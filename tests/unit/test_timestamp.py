"""
Unit tests for timestamp utilities.

These tests verify timestamp handling for frame synchronization.
"""
import pytest
import time
from dabmux.utils.timestamp import (
    FrameTimestamp, TimestampManager,
    EDI_EPOCH_UNIX, TIST_RESOLUTION
)


class TestFrameTimestamp:
    """Test FrameTimestamp class."""

    def test_create_timestamp(self) -> None:
        """Test creating timestamp."""
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0x100000)
        assert ts.seconds == 1000
        assert ts.utco == 37
        assert ts.tsta == 0x100000

    def test_invalid_timestamp(self) -> None:
        """Test invalid timestamp detection."""
        ts = FrameTimestamp()
        assert ts.is_valid() is False

        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0xFFFFFF)
        assert ts.is_valid() is False

    def test_valid_timestamp(self) -> None:
        """Test valid timestamp."""
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0x100000)
        assert ts.is_valid() is True

    def test_to_unix_epoch(self) -> None:
        """Test conversion to Unix epoch."""
        # EDI epoch (2000-01-01) + 1000 seconds - 37 leap seconds
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0)
        unix_time = ts.to_unix_epoch()

        expected = EDI_EPOCH_UNIX + 1000 - 37
        assert abs(unix_time - expected) < 0.001

    def test_to_unix_epoch_with_subsecond(self) -> None:
        """Test conversion with sub-second component."""
        # TIST value 0x800000 = 8388608 units
        # At 16384000 units/second = 0.512 seconds
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0x800000)
        unix_time = ts.to_unix_epoch()

        expected = EDI_EPOCH_UNIX + 1000 - 37 + (0x800000 * TIST_RESOLUTION)
        assert abs(unix_time - expected) < 0.001

    def test_from_unix_epoch(self) -> None:
        """Test creating from Unix epoch."""
        unix_time = EDI_EPOCH_UNIX + 1000
        ts = FrameTimestamp.from_unix_epoch(unix_time, utco=37)

        assert ts.is_valid()
        assert ts.seconds == 1000 + 37  # Add back TAI-UTC offset
        assert ts.utco == 37

    def test_diff_s(self) -> None:
        """Test time difference calculation."""
        ts1 = FrameTimestamp(seconds=1000, utco=37, tsta=0)
        ts2 = FrameTimestamp(seconds=1001, utco=37, tsta=0)

        diff = ts2.diff_s(ts1)
        assert abs(diff - 1.0) < 0.001

    def test_add_milliseconds(self) -> None:
        """Test adding milliseconds."""
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0)
        ts_new = ts + 24.0  # Add 24ms

        diff = ts_new.diff_s(ts)
        assert abs(diff - 0.024) < 0.0001

    def test_string_representation(self) -> None:
        """Test string representation."""
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0)
        s = str(ts)

        assert "FrameTimestamp" in s
        assert "2000" in s  # Year 2000

    def test_invalid_string(self) -> None:
        """Test string for invalid timestamp."""
        ts = FrameTimestamp()
        s = str(ts)

        assert "invalid" in s


class TestTimestampManager:
    """Test TimestampManager class."""

    def test_create_manager(self) -> None:
        """Test creating timestamp manager."""
        mgr = TimestampManager()
        assert mgr.frame_count == 0
        assert mgr.current_timestamp is None

    def test_create_with_offset(self) -> None:
        """Test creating with TIST offset."""
        mgr = TimestampManager(tist_offset_ms=100.0)
        assert mgr.tist_offset_ms == 100.0

    def test_set_current_time(self) -> None:
        """Test setting current time."""
        mgr = TimestampManager()
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0x100000)

        mgr.set_current_time(ts)
        assert mgr.current_timestamp == ts

    def test_get_current_timestamp_no_offset(self) -> None:
        """Test getting current timestamp without offset."""
        mgr = TimestampManager(tist_offset_ms=0.0)
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0)

        mgr.set_current_time(ts)
        current = mgr.get_current_timestamp()

        assert current is not None
        assert abs(current.diff_s(ts)) < 0.001

    def test_get_current_timestamp_with_offset(self) -> None:
        """Test getting current timestamp with offset."""
        mgr = TimestampManager(tist_offset_ms=24.0)
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0)

        mgr.set_current_time(ts)
        current = mgr.get_current_timestamp()

        assert current is not None
        diff = current.diff_s(ts)
        assert abs(diff - 0.024) < 0.001

    def test_increment_frame(self) -> None:
        """Test frame increment."""
        mgr = TimestampManager()
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0)

        mgr.set_current_time(ts)
        mgr.increment_frame(24.0)

        assert mgr.frame_count == 1

        current = mgr.get_current_timestamp()
        assert current is not None
        diff = current.diff_s(ts)
        assert abs(diff - 0.024) < 0.001

    def test_get_tist_for_frame_without_timestamp(self) -> None:
        """Test TIST calculation without timestamp."""
        mgr = TimestampManager()

        # Frame 0: 0ms
        tist0 = mgr.get_tist_for_frame(0)
        assert tist0 == 0

        # Frame 10: 240ms
        tist10 = mgr.get_tist_for_frame(10)
        expected = int((0.240 / TIST_RESOLUTION)) & 0xFFFFFF
        assert tist10 == expected

    def test_get_tist_for_frame_with_timestamp(self) -> None:
        """Test TIST calculation with timestamp."""
        mgr = TimestampManager()
        ts = FrameTimestamp(seconds=1000, utco=37, tsta=0x123456)

        mgr.set_current_time(ts)
        tist = mgr.get_tist_for_frame(0)

        assert tist == 0x123456

    def test_calculate_frame_offset(self) -> None:
        """Test frame offset calculation."""
        mgr = TimestampManager()
        ts_current = FrameTimestamp(seconds=1000, utco=37, tsta=0)
        ts_target = FrameTimestamp(seconds=1001, utco=37, tsta=0)

        mgr.set_current_time(ts_current)
        offset = mgr.calculate_frame_offset(ts_target)

        assert abs(offset - 1.0) < 0.001

    def test_calculate_frame_offset_no_current(self) -> None:
        """Test frame offset with no current timestamp."""
        mgr = TimestampManager()
        ts_target = FrameTimestamp(seconds=1000, utco=37, tsta=0)

        offset = mgr.calculate_frame_offset(ts_target)
        assert offset == 0.0


class TestTimestampConstants:
    """Test timestamp constants."""

    def test_edi_epoch(self) -> None:
        """Test EDI epoch value."""
        # EDI epoch is 2000-01-01T00:00:00Z
        # Unix epoch is 1970-01-01T00:00:00Z
        # Difference is 30 years + 7 leap years = 10957 days
        expected_days = 10957
        expected_seconds = expected_days * 86400

        assert EDI_EPOCH_UNIX == expected_seconds

    def test_tist_resolution(self) -> None:
        """Test TIST resolution."""
        # TIST resolution is 1/16384000 seconds
        assert abs(TIST_RESOLUTION - (1.0 / 16384000.0)) < 1e-12

        # 1 millisecond in TIST units
        ms_in_tist = int(0.001 / TIST_RESOLUTION)
        assert ms_in_tist == 16384

        # 24 milliseconds (one DAB frame) in TIST units
        frame_in_tist = int(0.024 / TIST_RESOLUTION)
        assert frame_in_tist == 393216
