"""
Timestamp utilities for DAB frame synchronization.

This module provides timestamp handling for frame-accurate multiplexing,
including EDI timestamps, TIST (Time Stamp) fields, and TAI-UTC offsets.
"""
import time
from dataclasses import dataclass
from typing import Optional
import structlog

logger = structlog.get_logger()


# EDI epoch: 2000-01-01T00:00:00Z
EDI_EPOCH_UNIX = 946684800

# TIST resolution: 1/16384000 seconds per LSB
TIST_RESOLUTION = 1.0 / 16384000.0


@dataclass
class FrameTimestamp:
    """
    DAB frame timestamp.

    Represents precise timing for frame synchronization, typically from
    EDI or other timestamp sources.
    """
    seconds: int = 0      # Seconds since EDI epoch (2000-01-01)
    utco: int = 0         # TAI-UTC offset (leap seconds)
    tsta: int = 0xFFFFFF  # Time stamp absolute (sub-second, 1/16384000 resolution)

    def is_valid(self) -> bool:
        """
        Check if timestamp is valid.

        Returns:
            True if timestamp has valid values
        """
        return self.tsta != 0xFFFFFF and self.seconds != 0

    def to_unix_epoch(self) -> float:
        """
        Convert to Unix epoch time.

        Returns:
            Unix timestamp in seconds (float)
        """
        if not self.is_valid():
            return 0.0

        # EDI epoch is 2000-01-01, Unix epoch is 1970-01-01
        # Subtract TAI-UTC offset to get UTC
        unix_seconds = EDI_EPOCH_UNIX + self.seconds - self.utco

        # Add sub-second component
        subsecond = self.tsta * TIST_RESOLUTION
        return unix_seconds + subsecond

    @classmethod
    def from_unix_epoch(cls, unix_time: float, utco: int = 0) -> 'FrameTimestamp':
        """
        Create timestamp from Unix epoch time.

        Args:
            unix_time: Unix timestamp in seconds
            utco: TAI-UTC offset (leap seconds)

        Returns:
            FrameTimestamp instance
        """
        # Convert Unix time to EDI time
        edi_time = unix_time - EDI_EPOCH_UNIX + utco

        # Split into seconds and subseconds
        seconds = int(edi_time)
        subsecond = edi_time - seconds

        # Convert subsecond to TIST units
        tsta = int(subsecond / TIST_RESOLUTION) & 0xFFFFFF

        return cls(seconds=seconds, utco=utco, tsta=tsta)

    def diff_s(self, other: 'FrameTimestamp') -> float:
        """
        Calculate time difference to another timestamp.

        Args:
            other: Other timestamp

        Returns:
            Time difference in seconds (self - other)
        """
        return self.to_unix_epoch() - other.to_unix_epoch()

    def __add__(self, milliseconds: float) -> 'FrameTimestamp':
        """
        Add milliseconds to timestamp.

        Args:
            milliseconds: Milliseconds to add

        Returns:
            New timestamp
        """
        unix_time = self.to_unix_epoch() + (milliseconds / 1000.0)
        return FrameTimestamp.from_unix_epoch(unix_time, self.utco)

    def __str__(self) -> str:
        """String representation."""
        if not self.is_valid():
            return "FrameTimestamp(invalid)"

        unix_time = self.to_unix_epoch()
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unix_time))
        subsec_ms = (self.tsta * TIST_RESOLUTION) * 1000
        return f"FrameTimestamp({time_str}.{subsec_ms:06.3f}Z)"


class TimestampManager:
    """
    Manages frame timestamps for multiplexer.

    Tracks current frame time and calculates TIST values for ETI frames.
    """

    def __init__(self, tist_offset_ms: float = 0.0) -> None:
        """
        Initialize timestamp manager.

        Args:
            tist_offset_ms: TIST offset in milliseconds
        """
        self.tist_offset_ms = tist_offset_ms
        self.frame_count = 0
        self.current_timestamp: Optional[FrameTimestamp] = None

    def set_current_time(self, timestamp: FrameTimestamp) -> None:
        """
        Set current time from external source.

        Args:
            timestamp: Current frame timestamp
        """
        self.current_timestamp = timestamp

    def get_current_timestamp(self) -> Optional[FrameTimestamp]:
        """
        Get current timestamp with offset applied.

        Returns:
            Current timestamp or None if not set
        """
        if self.current_timestamp is None:
            return None

        # Apply TIST offset
        return self.current_timestamp + self.tist_offset_ms

    def increment_frame(self, frame_duration_ms: float = 24.0) -> None:
        """
        Increment to next frame.

        Args:
            frame_duration_ms: Frame duration in milliseconds (default 24ms)
        """
        self.frame_count += 1

        if self.current_timestamp:
            self.current_timestamp = self.current_timestamp + frame_duration_ms

    def get_tist_for_frame(self, frame_number: int) -> int:
        """
        Calculate TIST value for frame.

        Args:
            frame_number: Frame number (0-249)

        Returns:
            TIST value (24-bit)
        """
        if self.current_timestamp is None:
            # Use frame count based timing (24ms per frame)
            ms_offset = (frame_number * 24) % 1000
            return int((ms_offset / 1000.0) / TIST_RESOLUTION) & 0xFFFFFF

        return self.current_timestamp.tsta

    def calculate_frame_offset(self, target: FrameTimestamp) -> float:
        """
        Calculate offset between current and target timestamp.

        Args:
            target: Target timestamp

        Returns:
            Offset in seconds (positive = target is in future)
        """
        if self.current_timestamp is None:
            return 0.0

        return target.diff_s(self.current_timestamp)
