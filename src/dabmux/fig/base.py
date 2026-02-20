"""
Base classes and structures for FIG generation.

This module defines the abstract base class for FIG implementations
and common structures.
"""
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import time


class FIGPriority(Enum):
    """
    FIG transmission priority for scheduling.

    Determines order of transmission, especially important for initial
    service announcements.
    """
    CRITICAL = 1   # Must be in every frame (FIG 0/0)
    HIGH = 2       # Should be in first frame (FIG 0/1, 0/2, 1/0)
    NORMAL = 3     # Should be in first 2-3 frames (FIG 1/1)
    LOW = 4        # Can be delayed (optional FIGs)


class FIGRate(Enum):
    """
    FIG repetition rates according to ETSI TR 101 496-2 Table 3.6.1.

    These rates determine how frequently each FIG should be transmitted.
    """
    FIG0_0 = "fig0_0"  # Special rate for FIG 0/0 (every 96ms)
    A = "a"            # At least 10 times per second (100ms)
    A_B = "a_b"        # Between 10 times and once per second (100-1000ms)
    B = "b"            # Once per second (1000ms)
    C = "c"            # Once every 10 seconds (10000ms)
    D = "d"            # Less than once every 10 seconds (>10000ms)
    E = "e"            # All in two minutes (120000ms)


def rate_increment_ms(rate: FIGRate) -> int:
    """
    Get the time increment in milliseconds for a FIG rate.

    Args:
        rate: FIG repetition rate

    Returns:
        Time increment in milliseconds
    """
    rate_map = {
        FIGRate.FIG0_0: 96,
        FIGRate.A: 100,
        FIGRate.A_B: 500,
        FIGRate.B: 1000,
        FIGRate.C: 10000,
        FIGRate.D: 30000,
        FIGRate.E: 120000,
    }
    return rate_map.get(rate, 1000)


@dataclass
class FillStatus:
    """
    Status of FIG filling operation.

    Reports how many bytes were written and whether the complete
    FIG was transmitted.
    """
    num_bytes_written: int = 0
    complete_fig_transmitted: bool = False


class FIGBase(ABC):
    """
    Abstract base class for all FIG implementations.

    Each FIG type implements this interface to provide configuration
    information to receivers.
    """

    def __init__(self) -> None:
        """Initialize the FIG."""
        self._last_transmission_ms: Optional[int] = None
        self._transmission_in_progress: bool = False
        self._completed_full_cycle: bool = False

    @abstractmethod
    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill the buffer with FIG data.

        Args:
            buf: Buffer to write FIG data into
            max_size: Maximum number of bytes available

        Returns:
            Fill status indicating bytes written and completion
        """
        pass

    @abstractmethod
    def repetition_rate(self) -> FIGRate:
        """
        Get the repetition rate for this FIG.

        Returns:
            FIG repetition rate
        """
        pass

    @abstractmethod
    def fig_type(self) -> int:
        """
        Get the FIG type number (0, 1, 2, etc.).

        Returns:
            FIG type number
        """
        pass

    @abstractmethod
    def fig_extension(self) -> int:
        """
        Get the FIG extension number.

        Returns:
            FIG extension number
        """
        pass

    def priority(self) -> FIGPriority:
        """
        Get the FIG priority for scheduling.

        Returns:
            FIG priority level (default: NORMAL)
        """
        return FIGPriority.NORMAL

    def name(self) -> str:
        """
        Get the FIG name (e.g., "0/0", "1/1").

        Returns:
            FIG name string
        """
        return f"{self.fig_type()}/{self.fig_extension()}"

    def should_transmit(self, current_time_ms: int) -> bool:
        """
        Check if this FIG should be transmitted now.

        Args:
            current_time_ms: Current time in milliseconds

        Returns:
            True if FIG should be transmitted
        """
        # Allow immediate retransmission if previous transmission was incomplete
        if self._transmission_in_progress:
            return True

        # If we've never transmitted or not completed a full cycle, transmit immediately
        if self._last_transmission_ms is None or not self._completed_full_cycle:
            return True

        # Otherwise check repetition rate
        increment = rate_increment_ms(self.repetition_rate())
        elapsed = current_time_ms - self._last_transmission_ms
        return elapsed >= increment

    def mark_transmitted(self, current_time_ms: int, complete: bool = False) -> None:
        """
        Mark this FIG as transmitted at the given time.

        Args:
            current_time_ms: Current time in milliseconds
            complete: True if complete FIG cycle finished (default: False for backwards compat)
        """
        if complete:
            self._last_transmission_ms = current_time_ms
            self._transmission_in_progress = False
            self._completed_full_cycle = True
        else:
            # Partial transmission - allow immediate retry in next FIB
            self._transmission_in_progress = True
            # Don't update _last_transmission_ms yet - allow immediate retry


def get_current_time_ms() -> int:
    """
    Get current time in milliseconds.

    Returns:
        Current time in milliseconds since epoch
    """
    return int(time.time() * 1000)
