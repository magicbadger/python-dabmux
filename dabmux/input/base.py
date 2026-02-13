"""
Abstract base classes for input sources.

This module defines the InputBase abstract class that all input implementations
must inherit from.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
import time


class BufferManagement(Enum):
    """
    Buffer management strategy for inputs.

    Prebuffering: Use a simple buffer without timestamps
    Timestamped: Buffer data until a timestamp is reached
    """
    Prebuffering = "prebuffering"
    Timestamped = "timestamped"


class InputBase(ABC):
    """
    Abstract base class for all input sources.

    Inputs provide audio or data frames to the multiplexer. They can read from
    files, network streams, or other sources.
    """

    def __init__(self) -> None:
        """Initialize the input."""
        self._buffer_management = BufferManagement.Prebuffering
        self._tist_delay_ms = 0
        self._is_open = False

    @abstractmethod
    def open(self, name: str) -> None:
        """
        Open the input source.

        Args:
            name: Source identifier (filename, URL, etc.)

        Raises:
            RuntimeError: If the source cannot be opened
            ValueError: If the name is invalid
        """
        pass

    @abstractmethod
    def read_frame(self, size: int) -> bytes:
        """
        Read a frame from the input (timestamp-agnostic).

        This method ignores timestamps and reads the next available data.
        All inputs must support this method.

        Args:
            size: Maximum number of bytes to read

        Returns:
            Data bytes (may be empty if no data available, or less than size)

        Raises:
            RuntimeError: On read error
        """
        pass

    def read_frame_timestamped(
        self,
        size: int,
        seconds: int,
        utco: int,
        tsta: int
    ) -> bytes:
        """
        Read a frame from the input, respecting timestamps.

        The timestamp of the returned data is not more recent than the
        specified timestamp. This is used for synchronization.

        Args:
            size: Maximum number of bytes to read
            seconds: UNIX epoch timestamp
            utco: TAI-UTC offset (leap seconds)
            tsta: ETI timestamp format

        Returns:
            Data bytes (empty if no data available)

        Note:
            Most file-based inputs don't support timestamps and return empty data.
            This allows buffer management to be changed at runtime safely.
        """
        # Default implementation: not supported, return empty
        return b''

    @abstractmethod
    def set_bitrate(self, bitrate: int) -> int:
        """
        Set the input bitrate.

        Args:
            bitrate: Bitrate in kbps

        Returns:
            Effective bitrate used (may differ from requested)

        Raises:
            ValueError: If bitrate is invalid
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the input source."""
        pass

    def set_tist_delay(self, delay_ms: int) -> None:
        """
        Set TIST (timestamp) delay in milliseconds.

        Args:
            delay_ms: Delay in milliseconds
        """
        self._tist_delay_ms = delay_ms

    def set_buffer_management(self, management: BufferManagement) -> None:
        """
        Set buffer management strategy.

        Args:
            management: Buffer management mode
        """
        self._buffer_management = management

    def get_buffer_management(self) -> BufferManagement:
        """
        Get current buffer management strategy.

        Returns:
            Current buffer management mode
        """
        return self._buffer_management

    @property
    def is_open(self) -> bool:
        """Check if input is open."""
        return self._is_open
