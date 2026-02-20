"""
Abstract interface for pre-encoded DAB+ audio sources.

This module defines the interface that all DAB+ input sources must implement.
python-dabmux accepts pre-encoded DAB+ streams from ODR-AudioEnc or compatible
encoders, focusing purely on multiplexing rather than encoding.
"""

from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)


class DABPlusInput(ABC):
    """
    Abstract interface for pre-encoded DAB+ audio sources.

    All implementations must provide exactly frame_size bytes per frame,
    where frame_size = (bitrate / 8) * 120 / 5 for the configured bitrate.

    This matches the ODR-AudioEnc output format:
    - 48 kbps: 144 bytes per frame (6 * 120 / 5)
    - 64 kbps: 192 bytes per frame (8 * 120 / 5)
    - 96 kbps: 288 bytes per frame (12 * 120 / 5)

    The data is RS-encoded DAB+ superframe data that will be inserted
    directly into the MST (Main Service Channel).
    """

    @abstractmethod
    def open(self) -> bool:
        """
        Open/connect to the input source.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close/disconnect from the input source."""
        pass

    @abstractmethod
    def is_open(self) -> bool:
        """
        Check if input is open and ready.

        Returns:
            True if open and ready to read
        """
        pass

    @abstractmethod
    def read_frame(self, frame_size: int) -> bytes:
        """
        Read one ETI frame worth of encoded DAB+ data.

        This method must return exactly frame_size bytes. If insufficient
        data is available, it should return zeros or cached data to maintain
        timing.

        Args:
            frame_size: Expected frame size in bytes

        Returns:
            Encoded DAB+ frame data (exactly frame_size bytes)
        """
        pass

    @abstractmethod
    def get_bitrate(self) -> int:
        """
        Get the bitrate of this stream.

        Returns:
            Bitrate in kbps
        """
        pass

    def get_frame_size(self) -> int:
        """
        Calculate frame size from bitrate.

        Uses ODR formula: (bitrate / 8) * 120 / 5

        Returns:
            Frame size in bytes
        """
        bitrate = self.get_bitrate()
        return (bitrate // 8) * 120 // 5
