"""
UDP input for pre-encoded DAB+ streams.

Receives DAB+ audio data via UDP for distributed/networked streaming.
"""

import socket
import queue
import threading
import structlog
from typing import Optional

from dabmux.input.dabplus_input import DABPlusInput

logger = structlog.get_logger(__name__)


class DABPlusUdpInput(DABPlusInput):
    """
    Read pre-encoded DAB+ data from UDP socket.

    UDP input enables distributed encoding where ODR-AudioEnc runs on a
    different machine than the multiplexer. Each UDP packet should contain
    exactly one DAB+ frame.

    Usage:
        # On encoder machine:
        odr-audioenc -i input.wav -b 48 -o udp://mux-server:9000

        # On multiplexer machine:
        python-dabmux -c config.yaml

    Example:
        >>> input_source = DABPlusUdpInput('0.0.0.0', 9000, bitrate=48)
        >>> if input_source.open():
        ...     frame_data = input_source.read_frame(144)
    """

    def __init__(self, host: str, port: int, bitrate: int, buffer_frames: int = 10):
        """
        Initialize UDP input.

        Args:
            host: Bind address (0.0.0.0 for all interfaces, 127.0.0.1 for localhost)
            port: UDP port to listen on
            bitrate: Stream bitrate in kbps
            buffer_frames: Number of frames to buffer (default: 10)
        """
        self.host = host
        self.port = port
        self.bitrate = bitrate
        self.buffer_frames = buffer_frames

        # Calculate frame size
        self.frame_size = (bitrate // 8) * 120 // 5

        # State
        self.socket: Optional[socket.socket] = None
        self.buffer: Optional[queue.Queue] = None
        self.receiver_thread: Optional[threading.Thread] = None
        self.running = False

        # Statistics
        self.frames_received = 0
        self.frames_dropped = 0
        self.underruns = 0
        self.size_errors = 0

        logger.debug(
            "DAB+ UDP input initialized",
            host=host,
            port=port,
            bitrate=bitrate,
            frame_size=self.frame_size,
            buffer_frames=buffer_frames
        )

    def open(self) -> bool:
        """
        Open UDP socket and start receiver thread.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Set receive buffer size (larger buffer helps prevent drops)
            # 64KB should be enough for ~400 frames at 144 bytes
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

            # Bind to address
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(0.1)  # 100ms timeout for clean shutdown

            # Create frame buffer
            self.buffer = queue.Queue(maxsize=self.buffer_frames)

            # Start receiver thread
            self.running = True
            self.receiver_thread = threading.Thread(
                target=self._receiver_loop,
                name=f"UDP-Receiver-{self.port}",
                daemon=True
            )
            self.receiver_thread.start()

            logger.info(
                "DAB+ UDP input opened",
                host=self.host,
                port=self.port,
                frame_size=self.frame_size
            )

            return True

        except Exception as e:
            logger.error("Failed to open UDP socket", error=str(e))
            self._cleanup()
            return False

    def close(self) -> None:
        """Close UDP socket and stop receiver thread."""
        if self.running:
            self.running = False

            # Wait for receiver thread to stop
            if self.receiver_thread and self.receiver_thread.is_alive():
                self.receiver_thread.join(timeout=1.0)

            self._cleanup()

            logger.debug(
                "UDP input closed",
                host=self.host,
                port=self.port,
                frames_received=self.frames_received,
                frames_dropped=self.frames_dropped
            )

    def _cleanup(self):
        """Clean up resources."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        self.buffer = None
        self.receiver_thread = None

    def is_open(self) -> bool:
        """
        Check if UDP socket is open.

        Returns:
            True if socket is open and receiving
        """
        return self.running and self.socket is not None

    def _receiver_loop(self):
        """
        Background thread to receive UDP packets.

        Runs continuously while self.running is True, receiving packets
        and adding them to the buffer queue.
        """
        logger.debug("UDP receiver thread started", port=self.port)

        while self.running:
            try:
                # Receive packet with timeout
                data, addr = self.socket.recvfrom(self.frame_size + 100)

                # Validate packet size
                if len(data) != self.frame_size:
                    logger.warning(
                        "Incorrect UDP packet size",
                        expected=self.frame_size,
                        got=len(data),
                        addr=addr
                    )
                    self.size_errors += 1
                    continue

                # Add to buffer
                try:
                    self.buffer.put_nowait(data)
                    self.frames_received += 1
                except queue.Full:
                    # Buffer overflow - drop frame
                    logger.warning("UDP buffer overflow, dropping frame", addr=addr)
                    self.frames_dropped += 1

            except socket.timeout:
                # Normal timeout, continue loop
                continue

            except Exception as e:
                if self.running:
                    logger.error("UDP receive error", error=str(e))

        logger.debug("UDP receiver thread stopped", port=self.port)

    def read_frame(self, frame_size: int) -> bytes:
        """
        Read one frame from UDP buffer.

        Returns buffered frame or zeros if buffer is empty.

        Args:
            frame_size: Expected frame size in bytes

        Returns:
            Frame data (exactly frame_size bytes)
        """
        if not self.buffer:
            logger.warning("Attempted to read from closed UDP input")
            return b'\x00' * frame_size

        try:
            # Try to get frame from buffer with short timeout
            return self.buffer.get(timeout=0.1)

        except queue.Empty:
            # Buffer underrun
            logger.warning("UDP buffer underrun", port=self.port)
            self.underruns += 1
            return b'\x00' * frame_size

    def get_bitrate(self) -> int:
        """
        Get bitrate.

        Returns:
            Bitrate in kbps
        """
        return self.bitrate

    def get_stats(self) -> dict:
        """
        Get statistics.

        Returns:
            Dictionary with receive statistics
        """
        buffer_level = self.buffer.qsize() if self.buffer else 0

        return {
            'frames_received': self.frames_received,
            'frames_dropped': self.frames_dropped,
            'underruns': self.underruns,
            'size_errors': self.size_errors,
            'buffer_level': buffer_level,
            'buffer_max': self.buffer_frames,
            'drop_rate': self.frames_dropped / max(self.frames_received, 1) if self.frames_received > 0 else 0
        }

    def get_buffer_level(self) -> tuple[int, int]:
        """
        Get current buffer fill level.

        Returns:
            Tuple of (current_level, max_level)
        """
        if self.buffer:
            return (self.buffer.qsize(), self.buffer_frames)
        return (0, 0)
