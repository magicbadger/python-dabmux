"""
Statistics collection and monitoring for DAB inputs.

This module provides input statistics tracking for monitoring buffer levels,
underruns, overruns, and overall input health.
"""
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from collections import deque
import structlog

logger = structlog.get_logger()


class InputState(Enum):
    """Input state for monitoring."""
    NO_DATA = "no_data"          # Waiting for data, buffers empty
    UNSTABLE = "unstable"        # Running but many underruns/overruns
    SILENCE = "silence"          # Audio too quiet
    STREAMING = "streaming"      # Running stably


@dataclass
class BufferStat:
    """Buffer fill statistic at a point in time."""
    timestamp: float
    bufsize: int


@dataclass
class PeakStat:
    """Audio peak level statistic."""
    timestamp: float
    peak_left: int
    peak_right: int


class InputStatistics:
    """
    Input statistics collector.

    Tracks buffer levels, underruns, overruns, timestamp offsets,
    and audio levels for input monitoring.
    """

    # History retention (seconds)
    BUFFER_HISTORY_SECONDS = 60
    PEAK_HISTORY_SECONDS = 5

    # State thresholds
    GLITCH_THRESHOLD = 5        # Underruns/overruns before UNSTABLE
    SILENCE_THRESHOLD = 10      # Frames with low audio before SILENCE
    SILENCE_LEVEL = 100         # Peak level threshold for silence detection

    def __init__(self, input_name: str = "unknown") -> None:
        """
        Initialize statistics collector.

        Args:
            input_name: Name of the input
        """
        self.input_name = input_name

        # Buffer fill history
        self._buffer_stats: deque = deque()

        # Event counters
        self._num_underruns = 0
        self._num_overruns = 0

        # Timestamp quality
        self._last_tist_offset = 0.0
        self._tist_offset_history: List[float] = []

        # Audio quality
        self._peak_stats: deque = deque()
        self._last_peak_left = 0
        self._last_peak_right = 0

        # State tracking
        self._glitch_counter = 0     # For UNSTABLE detection
        self._silence_counter = 0    # For SILENCE detection
        self._current_state = InputState.NO_DATA

        # Metadata
        self._encoder_version: Optional[str] = None
        self._encoder_uptime: Optional[int] = None

    def notify_buffer(self, bufsize: int) -> None:
        """
        Notify buffer fill level.

        Args:
            bufsize: Current buffer size in bytes
        """
        now = time.time()

        # Add to history
        self._buffer_stats.append(BufferStat(timestamp=now, bufsize=bufsize))

        # Trim old entries
        cutoff = now - self.BUFFER_HISTORY_SECONDS
        while self._buffer_stats and self._buffer_stats[0].timestamp < cutoff:
            self._buffer_stats.popleft()

    def notify_timestamp_offset(self, offset: float) -> None:
        """
        Notify timestamp offset.

        Args:
            offset: Offset in seconds (positive = frame is early)
        """
        self._last_tist_offset = offset
        self._tist_offset_history.append(offset)

        # Keep last 100 samples
        if len(self._tist_offset_history) > 100:
            self._tist_offset_history.pop(0)

    def notify_peak_levels(self, peak_left: int, peak_right: int) -> None:
        """
        Notify audio peak levels.

        Args:
            peak_left: Left channel peak (0-32767)
            peak_right: Right channel peak (0-32767)
        """
        now = time.time()

        self._last_peak_left = peak_left
        self._last_peak_right = peak_right

        # Add to history
        self._peak_stats.append(PeakStat(
            timestamp=now,
            peak_left=peak_left,
            peak_right=peak_right
        ))

        # Trim old entries
        cutoff = now - self.PEAK_HISTORY_SECONDS
        while self._peak_stats and self._peak_stats[0].timestamp < cutoff:
            self._peak_stats.popleft()

        # Check for silence
        if peak_left < self.SILENCE_LEVEL and peak_right < self.SILENCE_LEVEL:
            self._silence_counter = min(self._silence_counter + 1, self.SILENCE_THRESHOLD + 1)
        else:
            self._silence_counter = max(self._silence_counter - 1, 0)

    def notify_underrun(self) -> None:
        """Notify input underrun (frame not available)."""
        self._num_underruns += 1
        self._glitch_counter = min(self._glitch_counter + 1, self.GLITCH_THRESHOLD + 1)

        logger.warning(
            "Input underrun",
            input=self.input_name,
            total_underruns=self._num_underruns
        )

    def notify_overrun(self) -> None:
        """Notify input overrun (buffer overflow)."""
        self._num_overruns += 1
        self._glitch_counter = min(self._glitch_counter + 1, self.GLITCH_THRESHOLD + 1)

        logger.warning(
            "Input overrun",
            input=self.input_name,
            total_overruns=self._num_overruns
        )

    def notify_version(self, version: str, uptime_s: int) -> None:
        """
        Notify encoder version information.

        Args:
            version: Encoder version string
            uptime_s: Encoder uptime in seconds
        """
        self._encoder_version = version
        self._encoder_uptime = uptime_s

    def determine_state(self) -> InputState:
        """
        Determine current input state based on statistics.

        Returns:
            Current input state
        """
        # Check if we have buffer data
        if not self._buffer_stats:
            self._current_state = InputState.NO_DATA
            return self._current_state

        # Check for glitches (underruns/overruns)
        if self._glitch_counter >= self.GLITCH_THRESHOLD:
            self._current_state = InputState.UNSTABLE
            return self._current_state

        # Check for silence
        if self._silence_counter >= self.SILENCE_THRESHOLD:
            self._current_state = InputState.SILENCE
            return self._current_state

        # Healthy streaming
        self._current_state = InputState.STREAMING

        # Decay glitch counter slowly when streaming well
        if self._glitch_counter > 0:
            self._glitch_counter -= 1

        return self._current_state

    def get_average_buffer_fill(self) -> float:
        """
        Get average buffer fill level.

        Returns:
            Average buffer size in bytes
        """
        if not self._buffer_stats:
            return 0.0

        return sum(s.bufsize for s in self._buffer_stats) / len(self._buffer_stats)

    def get_min_buffer_fill(self) -> int:
        """
        Get minimum buffer fill level.

        Returns:
            Minimum buffer size in bytes
        """
        if not self._buffer_stats:
            return 0

        return min(s.bufsize for s in self._buffer_stats)

    def get_max_buffer_fill(self) -> int:
        """
        Get maximum buffer fill level.

        Returns:
            Maximum buffer size in bytes
        """
        if not self._buffer_stats:
            return 0

        return max(s.bufsize for s in self._buffer_stats)

    def get_average_tist_offset(self) -> float:
        """
        Get average timestamp offset.

        Returns:
            Average offset in seconds
        """
        if not self._tist_offset_history:
            return 0.0

        return sum(self._tist_offset_history) / len(self._tist_offset_history)

    def get_peak_levels(self) -> tuple[int, int]:
        """
        Get recent maximum peak levels.

        Returns:
            Tuple of (left_peak, right_peak)
        """
        if not self._peak_stats:
            return (0, 0)

        max_left = max(s.peak_left for s in self._peak_stats)
        max_right = max(s.peak_right for s in self._peak_stats)

        return (max_left, max_right)

    def encode_values_json(self) -> Dict[str, Any]:
        """
        Encode statistics as JSON-serializable dictionary.

        Returns:
            Dictionary with all statistics
        """
        state = self.determine_state()

        return {
            'input_name': self.input_name,
            'state': state.value,
            'buffer': {
                'current': self._buffer_stats[-1].bufsize if self._buffer_stats else 0,
                'average': self.get_average_buffer_fill(),
                'min': self.get_min_buffer_fill(),
                'max': self.get_max_buffer_fill(),
            },
            'events': {
                'underruns': self._num_underruns,
                'overruns': self._num_overruns,
                'glitch_counter': self._glitch_counter,
            },
            'timestamp': {
                'last_offset': self._last_tist_offset,
                'average_offset': self.get_average_tist_offset(),
            },
            'audio': {
                'peak_left': self._last_peak_left,
                'peak_right': self._last_peak_right,
                'max_peak_left': self.get_peak_levels()[0],
                'max_peak_right': self.get_peak_levels()[1],
                'silence_counter': self._silence_counter,
            },
            'encoder': {
                'version': self._encoder_version,
                'uptime_s': self._encoder_uptime,
            },
        }

    def __str__(self) -> str:
        """String representation."""
        state = self.determine_state()
        buffer_avg = self.get_average_buffer_fill()

        return (
            f"InputStatistics(name={self.input_name}, "
            f"state={state.value}, "
            f"buffer_avg={buffer_avg:.0f} bytes, "
            f"underruns={self._num_underruns}, "
            f"overruns={self._num_overruns})"
        )
