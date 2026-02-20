"""
FIG Carousel.

The carousel manages multiple FIGs and rotates through them according
to their repetition rates, filling available FIC space.
"""
from typing import List
import structlog
from dabmux.fig.base import FIGBase, get_current_time_ms

logger = structlog.get_logger()


class FIGCarousel:
    """
    FIG Carousel.

    Manages a collection of FIGs and rotates through them, respecting
    their individual repetition rates and space constraints.
    """

    def __init__(self) -> None:
        """Initialize the carousel."""
        self.figs: List[FIGBase] = []
        self._start_time_ms: int = 0
        self._initial_phase_duration_ms: int = 5000  # 5 seconds

    def add_fig(self, fig: FIGBase) -> None:
        """
        Add a FIG to the carousel.

        Args:
            fig: FIG to add
        """
        self.figs.append(fig)
        logger.debug("Added FIG to carousel", fig=fig.name())

    def clear(self) -> None:
        """Clear all FIGs from the carousel."""
        self.figs.clear()

    def fill_fib(self, fib_data: bytearray, max_size: int = 30) -> int:
        """
        Fill a FIB (Fast Information Block) with FIGs.

        A FIB is typically 30 bytes (in Mode I) and can contain multiple FIGs.
        This method fills the FIB with as many FIGs as possible, respecting
        their repetition rates.

        Args:
            fib_data: Buffer to fill (should be at least max_size bytes)
            max_size: Maximum size of FIB (default 30 bytes for Mode I)

        Returns:
            Number of bytes written
        """
        pos = 0
        current_time_ms = get_current_time_ms()

        # Initialize start time on first call
        if self._start_time_ms == 0:
            self._start_time_ms = current_time_ms

        # Check if we're in the initial announcement phase
        in_initial_phase = (current_time_ms - self._start_time_ms) < self._initial_phase_duration_ms

        # Sort FIGs by priority during initial phase for faster service announcement
        figs_to_process = self.figs
        if in_initial_phase:
            figs_to_process = sorted(self.figs, key=lambda fig: fig.priority().value)

        # Try to fill the FIB with FIGs
        for fig in figs_to_process:
            # Check if this FIG should be transmitted now
            if not fig.should_transmit(current_time_ms):
                continue

            # Try to fill this FIG
            remaining = max_size - pos
            if remaining < 2:
                # No space for even a minimal FIG
                break

            # Create a temporary buffer for this FIG
            temp_buf = bytearray(remaining)
            status = fig.fill(temp_buf, remaining)

            if status.num_bytes_written > 0:
                # Copy data to FIB
                fib_data[pos:pos + status.num_bytes_written] = temp_buf[:status.num_bytes_written]
                pos += status.num_bytes_written

                # Mark FIG as transmitted with completion status
                fig.mark_transmitted(current_time_ms, status.complete_fig_transmitted)

                logger.debug(
                    "Wrote FIG",
                    fig=fig.name(),
                    priority=fig.priority().name,
                    bytes=status.num_bytes_written,
                    complete=status.complete_fig_transmitted,
                    in_progress=not status.complete_fig_transmitted,
                    priority_mode=in_initial_phase
                )

                # If FIB is full, stop
                if pos >= max_size - 1:
                    break

        # Pad remaining bytes with 0xFF (no information)
        if pos < max_size:
            for i in range(pos, max_size):
                fib_data[i] = 0xFF

        return pos

    def get_fig_count(self) -> int:
        """
        Get number of FIGs in carousel.

        Returns:
            Number of FIGs
        """
        return len(self.figs)
