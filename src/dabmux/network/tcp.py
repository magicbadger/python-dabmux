"""
TCP network input for DAB audio.

This module provides TCP-based audio input with client connection handling
and frame buffering.
"""
import socket
import threading
import struct
from typing import Optional, List
from urllib.parse import urlparse
import structlog

from dabmux.input.base import InputBase

logger = structlog.get_logger()


class TcpInput(InputBase):
    """
    TCP network input.

    Acts as a TCP server, accepting connections from audio encoders
    and receiving audio frame data.
    """

    # TCP receive block size
    TCP_BLOCKSIZE = 2048

    def __init__(self, prebuffer_frames: int = 5, max_buffer_bytes: int = 1024 * 1024) -> None:
        """
        Initialize TCP input.

        Args:
            prebuffer_frames: Number of frames to buffer before streaming
            max_buffer_bytes: Maximum buffer size in bytes
        """
        super().__init__()
        self._server_socket: Optional[socket.socket] = None
        self._client_socket: Optional[socket.socket] = None
        self._host: str = ""
        self._port: int = 0

        # Frame buffering
        self._accumulation_buffer = bytearray()
        self._prebuffer_frames = prebuffer_frames
        self._max_buffer_bytes = max_buffer_bytes
        self._is_prebuffering = True

        # Receive thread
        self._receive_thread: Optional[threading.Thread] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._running = False

        # Statistics
        self._bytes_received = 0
        self._connections_accepted = 0
        self._client_addr: Optional[tuple] = None

    def open(self, name: str) -> None:
        """
        Open TCP input (start server).

        Args:
            name: TCP URL in format tcp://host:port or tcp://:port

        Raises:
            ValueError: If URL format is invalid
            RuntimeError: If server cannot be started
        """
        if not name:
            raise ValueError("TCP URL cannot be empty")

        # Parse URL
        if not name.startswith("tcp://"):
            raise ValueError(f"Invalid TCP URL: {name}")

        url = urlparse(name)
        netloc = url.netloc

        if ':' in netloc:
            if netloc.startswith(':'):
                # Bind all interfaces
                self._host = ''
                port_str = netloc[1:]
            else:
                # Specific host
                host_port = netloc.rsplit(':', 1)
                self._host = host_port[0]
                port_str = host_port[1]
        else:
            raise ValueError(f"Invalid TCP URL format: {name}")

        try:
            self._port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port number: {port_str}")

        # Create TCP server socket
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self._host, self._port))
            self._server_socket.listen(1)  # Single client

            self._is_open = True
            self._running = True

            # Start accept thread
            self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._accept_thread.start()

            logger.info(
                "TCP server started",
                host=self._host or "0.0.0.0",
                port=self._port
            )

        except OSError as e:
            raise RuntimeError(f"Failed to start TCP server: {e}")

    def set_bitrate(self, bitrate: int) -> int:
        """
        Set the input bitrate.

        For TCP inputs, bitrate is informational only and doesn't
        affect the actual data reception.

        Args:
            bitrate: Bitrate in kbps

        Returns:
            The bitrate value (unchanged)
        """
        return bitrate

    def close(self) -> None:
        """Close TCP input."""
        self._running = False

        # Close client connection
        if self._client_socket:
            try:
                self._client_socket.close()
            except:
                pass
            self._client_socket = None

        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass
            self._server_socket = None

        # Wait for threads
        if self._accept_thread:
            self._accept_thread.join(timeout=2.0)
            self._accept_thread = None

        if self._receive_thread:
            self._receive_thread.join(timeout=2.0)
            self._receive_thread = None

        self._is_open = False

        logger.info(
            "TCP server stopped",
            bytes=self._bytes_received,
            connections=self._connections_accepted
        )

    def _accept_loop(self) -> None:
        """Background thread for accepting client connections."""
        if not self._server_socket:
            return

        # Set timeout for clean shutdown
        self._server_socket.settimeout(1.0)

        while self._running:
            try:
                # Accept connection
                client_sock, client_addr = self._server_socket.accept()

                # Close previous client if exists
                if self._client_socket:
                    logger.info("Closing previous client", addr=self._client_addr)
                    self._client_socket.close()

                # Set new client
                self._client_socket = client_sock
                self._client_addr = client_addr
                self._connections_accepted += 1

                logger.info(
                    "TCP client connected",
                    addr=client_addr,
                    total_connections=self._connections_accepted
                )

                # Start receive thread for this client
                if self._receive_thread and self._receive_thread.is_alive():
                    # Wait for previous thread to finish
                    self._receive_thread.join(timeout=1.0)

                self._receive_thread = threading.Thread(
                    target=self._receive_loop,
                    daemon=True
                )
                self._receive_thread.start()

                # Reset prebuffering
                self._is_prebuffering = True
                self._accumulation_buffer.clear()

            except socket.timeout:
                # Normal timeout, continue
                continue
            except Exception as e:
                if self._running:
                    logger.error("TCP accept error", error=str(e))

    def _receive_loop(self) -> None:
        """Background thread for receiving data from client."""
        if not self._client_socket:
            return

        # Set socket timeout
        self._client_socket.settimeout(5.0)

        try:
            while self._running and self._client_socket:
                # Receive data
                data = self._client_socket.recv(self.TCP_BLOCKSIZE)

                if not data:
                    # Client disconnected
                    logger.info("TCP client disconnected", addr=self._client_addr)
                    break

                self._bytes_received += len(data)

                # Check buffer size limit
                if len(self._accumulation_buffer) + len(data) > self._max_buffer_bytes:
                    # Buffer overflow - drop oldest data
                    overflow = len(self._accumulation_buffer) + len(data) - self._max_buffer_bytes
                    logger.warning(
                        "TCP buffer overflow, dropping data",
                        overflow_bytes=overflow
                    )
                    self._accumulation_buffer = self._accumulation_buffer[overflow:]

                # Add to buffer
                self._accumulation_buffer.extend(data)

        except socket.timeout:
            logger.warning("TCP receive timeout", addr=self._client_addr)
        except Exception as e:
            if self._running:
                logger.error("TCP receive error", error=str(e))
        finally:
            # Close client socket
            if self._client_socket:
                try:
                    self._client_socket.close()
                except:
                    pass
                self._client_socket = None

    def read_frame(self, size: int) -> bytes:
        """
        Read frame from TCP input.

        Args:
            size: Frame size in bytes

        Returns:
            Frame data (or silence if unavailable)
        """
        # Check if we have enough data
        if len(self._accumulation_buffer) >= size:
            # Extract frame
            frame_data = bytes(self._accumulation_buffer[:size])
            self._accumulation_buffer = self._accumulation_buffer[size:]

            # Prebuffering logic
            if self._is_prebuffering:
                # Wait for sufficient buffer
                if len(self._accumulation_buffer) >= size * self._prebuffer_frames:
                    self._is_prebuffering = False
                    logger.info(
                        "TCP prebuffering complete",
                        buffer_frames=len(self._accumulation_buffer) // size
                    )
                else:
                    # Still prebuffering, return silence
                    return bytes(size)

            return frame_data
        else:
            # Insufficient data - underrun
            if not self._is_prebuffering:
                logger.warning(
                    "TCP input underrun",
                    available=len(self._accumulation_buffer),
                    needed=size
                )
                self._is_prebuffering = True

            return bytes(size)

    def get_info(self) -> str:
        """
        Get input information string.

        Returns:
            Information string
        """
        client_info = f" (client: {self._client_addr})" if self._client_socket else ""
        return f"tcp://{self._host or '0.0.0.0'}:{self._port}{client_info}"

    def get_buffer_level(self) -> int:
        """
        Get current buffer level in bytes.

        Returns:
            Buffer level
        """
        return len(self._accumulation_buffer)

    def is_connected(self) -> bool:
        """
        Check if client is connected.

        Returns:
            True if client connected
        """
        return self._client_socket is not None

    def get_statistics(self) -> dict:
        """
        Get input statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'bytes_received': self._bytes_received,
            'buffer_bytes': len(self._accumulation_buffer),
            'connections_accepted': self._connections_accepted,
            'client_connected': self.is_connected(),
            'client_addr': str(self._client_addr) if self._client_addr else None,
            'is_prebuffering': self._is_prebuffering,
        }
