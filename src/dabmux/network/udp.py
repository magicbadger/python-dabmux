"""
UDP network input for DAB audio.

This module provides UDP-based audio input with frame buffering and
optional timestamp synchronization.
"""
import socket
import threading
import queue
from typing import Optional, Tuple
from urllib.parse import urlparse
import structlog

from dabmux.input.base import InputBase, BufferManagement
from dabmux.utils.timestamp import FrameTimestamp

logger = structlog.get_logger()


class UdpInput(InputBase):
    """
    UDP network input.

    Receives audio data packets via UDP and assembles them into frames.
    Supports both simple concatenation mode and timestamp-based synchronization.
    """

    # Default receive buffer size
    DEFAULT_BUFFER_SIZE = 32768

    def __init__(self, prebuffer_frames: int = 5, max_queue_size: int = 100) -> None:
        """
        Initialize UDP input.

        Args:
            prebuffer_frames: Number of frames to buffer before streaming
            max_queue_size: Maximum frame queue size
        """
        super().__init__()
        self._socket: Optional[socket.socket] = None
        self._host: str = ""
        self._port: int = 0
        self._multicast: bool = False
        self._multicast_addr: str = ""

        # Frame buffering
        self._frame_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._prebuffer_frames = prebuffer_frames
        self._max_queue_size = max_queue_size
        self._is_prebuffering = True

        # Receive thread
        self._receive_thread: Optional[threading.Thread] = None
        self._running = False

        # Statistics
        self._packets_received = 0
        self._bytes_received = 0
        self._queue_overruns = 0

        # Accumulation buffer for partial frames
        self._accumulation_buffer = bytearray()

    def open(self, name: str) -> None:
        """
        Open UDP input.

        Args:
            name: UDP URL in format:
                  - udp://:port (bind all interfaces)
                  - udp://host:port (bind specific interface)
                  - udp://@multicast_addr:port (multicast)
                  - udp://local_addr@multicast_addr:port (multicast with bind)

        Raises:
            ValueError: If URL format is invalid
            RuntimeError: If socket cannot be opened
        """
        if not name:
            raise ValueError("UDP URL cannot be empty")

        # Parse URL
        if not name.startswith("udp://"):
            raise ValueError(f"Invalid UDP URL: {name}")

        url = urlparse(name)

        # Handle different URL patterns
        netloc = url.netloc
        if '@' in netloc:
            # Multicast with bind address
            bind_addr, mcast_port = netloc.split('@')
            if ':' in mcast_port:
                mcast_addr, port_str = mcast_port.rsplit(':', 1)
            else:
                raise ValueError(f"Invalid multicast URL: {name}")

            self._host = bind_addr or ''
            self._multicast_addr = mcast_addr
            self._multicast = True
        elif ':' in netloc:
            # Standard host:port
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
            raise ValueError(f"Invalid UDP URL format: {name}")

        try:
            self._port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port number: {port_str}")

        # Create UDP socket
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket
            self._socket.bind((self._host, self._port))

            # Join multicast group if needed
            if self._multicast:
                import struct as st
                mreq = st.pack('4sl', socket.inet_aton(self._multicast_addr),
                              socket.INADDR_ANY)
                self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            self._is_open = True

            # Start receive thread
            self._running = True
            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()

            logger.info(
                "UDP input opened",
                host=self._host or "0.0.0.0",
                port=self._port,
                multicast=self._multicast,
                mcast_addr=self._multicast_addr if self._multicast else None
            )

        except OSError as e:
            raise RuntimeError(f"Failed to open UDP socket: {e}")

    def set_bitrate(self, bitrate: int) -> int:
        """
        Set the input bitrate.

        For UDP inputs, bitrate is informational only and doesn't
        affect the actual data reception.

        Args:
            bitrate: Bitrate in kbps

        Returns:
            The bitrate value (unchanged)
        """
        return bitrate

    def close(self) -> None:
        """Close UDP input."""
        self._running = False

        if self._receive_thread:
            self._receive_thread.join(timeout=2.0)
            self._receive_thread = None

        if self._socket:
            self._socket.close()
            self._socket = None

        self._is_open = False

        logger.info(
            "UDP input closed",
            packets=self._packets_received,
            bytes=self._bytes_received,
            overruns=self._queue_overruns
        )

    def _receive_loop(self) -> None:
        """Background thread for receiving UDP packets."""
        if not self._socket:
            return

        # Set socket timeout for clean shutdown
        self._socket.settimeout(0.5)

        while self._running:
            try:
                # Receive packet
                data, addr = self._socket.recvfrom(self.DEFAULT_BUFFER_SIZE)
                self._packets_received += 1
                self._bytes_received += len(data)

                # Add to accumulation buffer
                self._accumulation_buffer.extend(data)

                # Log occasionally
                if self._packets_received % 100 == 0:
                    logger.debug(
                        "UDP packets received",
                        count=self._packets_received,
                        bytes=self._bytes_received,
                        queue_size=self._frame_queue.qsize()
                    )

            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                if self._running:
                    logger.error("UDP receive error", error=str(e))
                break

    def read_frame(self, size: int) -> bytes:
        """
        Read frame in prebuffering mode.

        Args:
            size: Frame size in bytes

        Returns:
            Frame data (or silence if unavailable)
        """
        # Check if we have enough data in accumulation buffer
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
                        "UDP prebuffering complete",
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
                    "UDP input underrun",
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
        if self._multicast:
            return f"udp://{self._host}@{self._multicast_addr}:{self._port}"
        else:
            return f"udp://{self._host or '0.0.0.0'}:{self._port}"

    def get_buffer_level(self) -> int:
        """
        Get current buffer level in bytes.

        Returns:
            Buffer level
        """
        return len(self._accumulation_buffer)

    def get_statistics(self) -> dict:
        """
        Get input statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'packets_received': self._packets_received,
            'bytes_received': self._bytes_received,
            'buffer_bytes': len(self._accumulation_buffer),
            'queue_overruns': self._queue_overruns,
            'is_prebuffering': self._is_prebuffering,
        }
