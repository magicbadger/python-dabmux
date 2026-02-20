"""
FIFO (Named Pipe) input for pre-encoded DAB+ streams.

Reads DAB+ audio data from named pipes for live streaming.
"""

import os
import fcntl
import select
import structlog
from pathlib import Path
from typing import Optional

from dabmux.input.dabplus_input import DABPlusInput

logger = structlog.get_logger(__name__)


class DABPlusFifoInput(DABPlusInput):
    """
    Read pre-encoded DAB+ data from named pipe (FIFO).

    Named pipes enable live streaming from ODR-AudioEnc to python-dabmux
    with minimal latency and no intermediate files.

    Usage:
        # Create FIFO
        mkfifo /tmp/audio.fifo

        # Start encoder (writes to FIFO)
        odr-audioenc -i input.wav -b 48 -o /tmp/audio.fifo &

        # Start multiplexer (reads from FIFO)
        python-dabmux -c config.yaml

    Example:
        >>> input_source = DABPlusFifoInput('/tmp/audio.fifo', bitrate=48)
        >>> if input_source.open():
        ...     frame_data = input_source.read_frame(144)
    """

    def __init__(self, fifo_path: str, bitrate: int, timeout: float = 1.0):
        """
        Initialize FIFO input.

        Args:
            fifo_path: Path to named pipe
            bitrate: Stream bitrate in kbps
            timeout: Read timeout in seconds (default: 1.0)
        """
        self.fifo_path = Path(fifo_path)
        self.bitrate = bitrate
        self.timeout = timeout

        # Calculate frame size
        self.frame_size = (bitrate // 8) * 120 // 5

        # State
        self.fifo: Optional[object] = None
        self.fd: Optional[int] = None
        self.frames_read: int = 0
        self.underruns: int = 0

        logger.debug(
            "DAB+ FIFO input initialized",
            path=str(self.fifo_path),
            bitrate=bitrate,
            frame_size=self.frame_size,
            timeout=timeout
        )

    def open(self) -> bool:
        """
        Open FIFO for reading.

        Opens in non-blocking mode initially, then switches to blocking mode.
        This prevents hanging if no writer is connected.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if FIFO exists
            if not self.fifo_path.exists():
                logger.error("FIFO does not exist", path=str(self.fifo_path))
                return False

            # Verify it's actually a FIFO
            if not self.fifo_path.is_fifo():
                logger.error("Path is not a FIFO", path=str(self.fifo_path))
                return False

            # Open in non-blocking mode to avoid hanging
            self.fd = os.open(str(self.fifo_path), os.O_RDONLY | os.O_NONBLOCK)

            # Switch to blocking mode for reads
            flags = fcntl.fcntl(self.fd, fcntl.F_GETFL)
            fcntl.fcntl(self.fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)

            # Wrap in file object for easier reading
            self.fifo = os.fdopen(self.fd, 'rb', buffering=0)  # No buffering for real-time

            logger.info(
                "DAB+ FIFO input opened",
                path=str(self.fifo_path),
                frame_size=self.frame_size
            )

            return True

        except Exception as e:
            logger.error("Failed to open FIFO", path=str(self.fifo_path), error=str(e))
            if self.fd is not None:
                try:
                    os.close(self.fd)
                except:
                    pass
                self.fd = None
            self.fifo = None
            return False

    def close(self) -> None:
        """Close FIFO."""
        if self.fifo:
            try:
                self.fifo.close()
                logger.debug("FIFO closed", path=str(self.fifo_path))
            except Exception as e:
                logger.error("Error closing FIFO", error=str(e))
            finally:
                self.fifo = None
                self.fd = None
                self.frames_read = 0

    def is_open(self) -> bool:
        """
        Check if FIFO is open.

        Returns:
            True if FIFO is open and ready
        """
        return self.fifo is not None

    def read_frame(self, frame_size: int) -> bytes:
        """
        Read one frame from FIFO with timeout.

        Uses select() to implement timeout. Returns zeros if timeout occurs
        or insufficient data is available.

        Args:
            frame_size: Expected frame size in bytes

        Returns:
            Frame data (exactly frame_size bytes)
        """
        if not self.fifo:
            logger.warning("Attempted to read from closed FIFO")
            return b'\x00' * frame_size

        try:
            # Use select for timeout
            readable, _, exceptional = select.select([self.fifo], [], [self.fifo], self.timeout)

            # Check for exceptional conditions
            if exceptional:
                logger.error("FIFO exceptional condition", path=str(self.fifo_path))
                return b'\x00' * frame_size

            # Check if data is available
            if not readable:
                logger.warning(
                    "FIFO read timeout",
                    path=str(self.fifo_path),
                    timeout=self.timeout
                )
                self.underruns += 1
                return b'\x00' * frame_size

            # Read data
            data = self.fifo.read(frame_size)

            if len(data) == 0:
                # EOF - encoder disconnected
                logger.warning("FIFO EOF - encoder disconnected", path=str(self.fifo_path))
                self.underruns += 1
                return b'\x00' * frame_size

            if len(data) < frame_size:
                # Underrun - not enough data
                logger.warning(
                    "FIFO underrun",
                    path=str(self.fifo_path),
                    expected=frame_size,
                    got=len(data)
                )
                self.underruns += 1
                # Pad with zeros
                data += b'\x00' * (frame_size - len(data))

            self.frames_read += 1
            return data

        except Exception as e:
            logger.error("Error reading from FIFO", path=str(self.fifo_path), error=str(e))
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
            Dictionary with frames_read and underruns
        """
        return {
            'frames_read': self.frames_read,
            'underruns': self.underruns,
            'underrun_rate': self.underruns / max(self.frames_read, 1)
        }
