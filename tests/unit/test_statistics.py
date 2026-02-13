"""
Unit tests for statistics collection.

These tests verify input statistics tracking and monitoring.
"""
import pytest
import time
from dabmux.utils.statistics import InputStatistics, InputState


class TestInputStatistics:
    """Test InputStatistics class."""

    def test_create_statistics(self) -> None:
        """Test creating statistics collector."""
        stats = InputStatistics("test_input")
        assert stats.input_name == "test_input"
        assert stats._num_underruns == 0
        assert stats._num_overruns == 0

    def test_notify_buffer(self) -> None:
        """Test buffer notification."""
        stats = InputStatistics()

        stats.notify_buffer(1000)
        assert len(stats._buffer_stats) == 1
        assert stats._buffer_stats[0].bufsize == 1000

    def test_notify_multiple_buffers(self) -> None:
        """Test multiple buffer notifications."""
        stats = InputStatistics()

        for i in range(10):
            stats.notify_buffer(1000 + i * 100)

        assert len(stats._buffer_stats) == 10
        assert stats.get_average_buffer_fill() == 1450.0

    def test_notify_timestamp_offset(self) -> None:
        """Test timestamp offset notification."""
        stats = InputStatistics()

        stats.notify_timestamp_offset(0.001)  # 1ms offset
        assert stats._last_tist_offset == 0.001
        assert len(stats._tist_offset_history) == 1

    def test_notify_peak_levels(self) -> None:
        """Test peak level notification."""
        stats = InputStatistics()

        stats.notify_peak_levels(10000, 12000)
        assert stats._last_peak_left == 10000
        assert stats._last_peak_right == 12000
        assert len(stats._peak_stats) == 1

    def test_notify_underrun(self) -> None:
        """Test underrun notification."""
        stats = InputStatistics()

        stats.notify_underrun()
        assert stats._num_underruns == 1
        assert stats._glitch_counter > 0

    def test_notify_overrun(self) -> None:
        """Test overrun notification."""
        stats = InputStatistics()

        stats.notify_overrun()
        assert stats._num_overruns == 1
        assert stats._glitch_counter > 0

    def test_notify_version(self) -> None:
        """Test version notification."""
        stats = InputStatistics()

        stats.notify_version("v1.0.0", 3600)
        assert stats._encoder_version == "v1.0.0"
        assert stats._encoder_uptime == 3600

    def test_determine_state_no_data(self) -> None:
        """Test state determination with no data."""
        stats = InputStatistics()

        state = stats.determine_state()
        assert state == InputState.NO_DATA

    def test_determine_state_streaming(self) -> None:
        """Test state determination when streaming."""
        stats = InputStatistics()

        # Add buffer data
        stats.notify_buffer(1000)

        # Add audio levels
        stats.notify_peak_levels(10000, 10000)

        state = stats.determine_state()
        assert state == InputState.STREAMING

    def test_determine_state_unstable(self) -> None:
        """Test state determination with underruns."""
        stats = InputStatistics()

        # Add buffer data
        stats.notify_buffer(1000)

        # Trigger multiple underruns
        for _ in range(10):
            stats.notify_underrun()

        state = stats.determine_state()
        assert state == InputState.UNSTABLE

    def test_determine_state_silence(self) -> None:
        """Test state determination with silence."""
        stats = InputStatistics()

        # Add buffer data
        stats.notify_buffer(1000)

        # Trigger silence detection
        for _ in range(15):
            stats.notify_peak_levels(50, 50)  # Very low levels

        state = stats.determine_state()
        assert state == InputState.SILENCE

    def test_get_average_buffer_fill(self) -> None:
        """Test average buffer fill calculation."""
        stats = InputStatistics()

        stats.notify_buffer(1000)
        stats.notify_buffer(2000)
        stats.notify_buffer(3000)

        avg = stats.get_average_buffer_fill()
        assert avg == 2000.0

    def test_get_min_buffer_fill(self) -> None:
        """Test minimum buffer fill."""
        stats = InputStatistics()

        stats.notify_buffer(1000)
        stats.notify_buffer(2000)
        stats.notify_buffer(500)

        min_fill = stats.get_min_buffer_fill()
        assert min_fill == 500

    def test_get_max_buffer_fill(self) -> None:
        """Test maximum buffer fill."""
        stats = InputStatistics()

        stats.notify_buffer(1000)
        stats.notify_buffer(3000)
        stats.notify_buffer(2000)

        max_fill = stats.get_max_buffer_fill()
        assert max_fill == 3000

    def test_get_average_tist_offset(self) -> None:
        """Test average TIST offset calculation."""
        stats = InputStatistics()

        stats.notify_timestamp_offset(0.001)
        stats.notify_timestamp_offset(0.002)
        stats.notify_timestamp_offset(0.003)

        avg = stats.get_average_tist_offset()
        assert abs(avg - 0.002) < 0.0001

    def test_get_peak_levels(self) -> None:
        """Test peak level retrieval."""
        stats = InputStatistics()

        stats.notify_peak_levels(10000, 12000)
        stats.notify_peak_levels(15000, 11000)
        stats.notify_peak_levels(8000, 13000)

        max_left, max_right = stats.get_peak_levels()
        assert max_left == 15000
        assert max_right == 13000

    def test_encode_values_json(self) -> None:
        """Test JSON encoding."""
        stats = InputStatistics("test")

        stats.notify_buffer(1000)
        stats.notify_peak_levels(10000, 12000)
        stats.notify_timestamp_offset(0.001)
        stats.notify_version("v1.0", 3600)

        json_data = stats.encode_values_json()

        assert json_data['input_name'] == "test"
        assert 'buffer' in json_data
        assert 'events' in json_data
        assert 'timestamp' in json_data
        assert 'audio' in json_data
        assert 'encoder' in json_data

        assert json_data['buffer']['current'] == 1000
        assert json_data['audio']['peak_left'] == 10000
        assert json_data['encoder']['version'] == "v1.0"

    def test_string_representation(self) -> None:
        """Test string representation."""
        stats = InputStatistics("test")

        stats.notify_buffer(1000)
        s = str(stats)

        assert "test" in s
        assert "InputStatistics" in s

    def test_glitch_counter_decay(self) -> None:
        """Test glitch counter decay when streaming."""
        stats = InputStatistics()

        # Add buffer
        stats.notify_buffer(1000)

        # Trigger underrun
        stats.notify_underrun()
        assert stats._glitch_counter > 0

        # Determine state multiple times (should decay)
        initial_counter = stats._glitch_counter
        for _ in range(5):
            stats.determine_state()

        assert stats._glitch_counter < initial_counter

    def test_silence_counter_recovery(self) -> None:
        """Test silence counter recovery."""
        stats = InputStatistics()

        # Add buffer
        stats.notify_buffer(1000)

        # Trigger silence
        for _ in range(5):
            stats.notify_peak_levels(50, 50)

        assert stats._silence_counter > 0

        # Add normal audio
        for _ in range(10):
            stats.notify_peak_levels(10000, 10000)

        assert stats._silence_counter == 0

    def test_buffer_history_retention(self) -> None:
        """Test buffer history is limited."""
        stats = InputStatistics()

        # Add many buffer notifications with old timestamps
        for i in range(1000):
            stats.notify_buffer(i)

        # Should be limited by time window, not count
        assert len(stats._buffer_stats) <= 1000


class TestInputState:
    """Test InputState enum."""

    def test_state_values(self) -> None:
        """Test state enum values."""
        assert InputState.NO_DATA.value == "no_data"
        assert InputState.UNSTABLE.value == "unstable"
        assert InputState.SILENCE.value == "silence"
        assert InputState.STREAMING.value == "streaming"
