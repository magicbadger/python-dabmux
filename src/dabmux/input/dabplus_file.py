"""
File input for pre-encoded DAB+ streams (.dabp format).

Reads DAB+ audio data from files created by ODR-AudioEnc.
"""

import os
import structlog
from pathlib import Path
from typing import Optional

from dabmux.input.dabplus_input import DABPlusInput

logger = structlog.get_logger(__name__)


class DABPlusFileInput(DABPlusInput):
    """
    Read pre-encoded DAB+ data from .dabp file.

    Format: Raw RS-encoded DAB+ superframe data
    Created by: odr-audioenc -o file.dabp

    File structure:
    - Each frame is exactly (bitrate/8 * 120 / 5) bytes
    - No headers, just raw encoded data
    - Sequential reading with optional looping

    Example:
        >>> input_source = DABPlusFileInput('/path/to/audio.dabp', bitrate=48, loop=True)
        >>> if input_source.open():
        ...     frame_data = input_source.read_frame(144)  # 144 bytes for 48 kbps
    """

    def __init__(self, file_path: str, bitrate: int, loop: bool = True):
        """
        Initialize file input.

        Args:
            file_path: Path to .dabp file
            bitrate: Stream bitrate in kbps (24, 32, 48, 64, 80, 96, 112, 128, 160, 192)
            loop: Loop file when reaching EOF (default: True)
        """
        self.file_path = Path(file_path)
        self.bitrate = bitrate
        self.loop = loop

        # Calculate frame size from bitrate
        self.frame_size = (bitrate // 8) * 120 // 5

        # State
        self.file: Optional[object] = None
        self.file_size: int = 0
        self.bytes_read: int = 0
        self.loop_count: int = 0

        logger.debug(
            "DAB+ file input initialized",
            path=str(self.file_path),
            bitrate=bitrate,
            frame_size=self.frame_size,
            loop=loop
        )

    def open(self) -> bool:
        """
        Open .dabp file for reading.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.file_path.exists():
                logger.error("File not found", path=str(self.file_path))
                return False

            self.file = open(self.file_path, 'rb')

            # Get file size
            self.file.seek(0, 2)  # Seek to end
            self.file_size = self.file.tell()
            self.file.seek(0)  # Back to start

            # Validate file size
            if self.file_size == 0:
                logger.error("File is empty", path=str(self.file_path))
                self.close()
                return False

            if self.file_size % self.frame_size != 0:
                logger.warning(
                    "File size not multiple of frame size",
                    file_size=self.file_size,
                    frame_size=self.frame_size,
                    remainder=self.file_size % self.frame_size
                )

            num_frames = self.file_size // self.frame_size
            duration_seconds = num_frames * 24 / 1000  # 24ms per frame

            logger.info(
                "DAB+ file input opened",
                path=str(self.file_path),
                size_bytes=self.file_size,
                num_frames=num_frames,
                duration_seconds=f"{duration_seconds:.2f}"
            )

            return True

        except Exception as e:
            logger.error("Failed to open file", path=str(self.file_path), error=str(e))
            self.file = None
            return False

    def close(self) -> None:
        """Close file."""
        if self.file:
            try:
                self.file.close()
                logger.debug("File closed", path=str(self.file_path))
            except Exception as e:
                logger.error("Error closing file", error=str(e))
            finally:
                self.file = None
                self.bytes_read = 0

    def is_open(self) -> bool:
        """
        Check if file is open.

        Returns:
            True if file is open and ready
        """
        return self.file is not None

    def read_frame(self, frame_size: int) -> bytes:
        """
        Read one frame from .dabp file.

        Automatically loops to beginning if loop=True and EOF is reached.
        Returns zeros if file is not open or error occurs.

        Args:
            frame_size: Expected frame size in bytes

        Returns:
            Frame data (exactly frame_size bytes)
        """
        if not self.file:
            logger.warning("Attempted to read from closed file")
            return b'\x00' * frame_size

        try:
            data = self.file.read(frame_size)
            self.bytes_read += len(data)

            # Handle EOF
            if len(data) < frame_size:
                if self.loop and self.file_size > 0:
                    # Loop to beginning
                    self.file.seek(0)
                    self.loop_count += 1
                    self.bytes_read = 0

                    remaining = frame_size - len(data)
                    additional_data = self.file.read(remaining)
                    data += additional_data
                    self.bytes_read += len(additional_data)

                    logger.debug(
                        "File looped",
                        loop_count=self.loop_count,
                        path=str(self.file_path)
                    )
                else:
                    # Pad with zeros if not looping or empty file
                    logger.warning(
                        "End of file reached, padding with zeros",
                        path=str(self.file_path)
                    )
                    data += b'\x00' * (frame_size - len(data))

            return data

        except Exception as e:
            logger.error("Error reading from file", path=str(self.file_path), error=str(e))
            return b'\x00' * frame_size

    def get_bitrate(self) -> int:
        """
        Get bitrate.

        Returns:
            Bitrate in kbps
        """
        return self.bitrate

    def get_position(self) -> tuple[int, int]:
        """
        Get current position in file.

        Returns:
            Tuple of (bytes_read, file_size)
        """
        return (self.bytes_read, self.file_size)

    def get_loop_count(self) -> int:
        """
        Get number of times file has looped.

        Returns:
            Loop count
        """
        return self.loop_count
