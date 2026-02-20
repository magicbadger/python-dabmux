"""
Unit tests for FIG 0/10 (Date and Time).
"""
import pytest
from datetime import datetime
from dabmux.core.mux_elements import DabEnsemble, DabLabel, DateTimeConfig
from dabmux.fig.fig0 import FIG0_10, calculate_mjd, calculate_lto_auto


class TestMJDCalculation:
    """Test Modified Julian Date calculation."""

    def test_mjd_epoch(self):
        """Test MJD for Unix epoch (1970-01-01)."""
        mjd = calculate_mjd(1970, 1, 1)
        assert mjd == 40587  # Known MJD for 1970-01-01

    def test_mjd_2000(self):
        """Test MJD for Y2K (2000-01-01)."""
        mjd = calculate_mjd(2000, 1, 1)
        assert mjd == 51544  # Known MJD for 2000-01-01

    def test_mjd_2026(self):
        """Test MJD for 2026-02-20."""
        mjd = calculate_mjd(2026, 2, 20)
        assert mjd == 61091  # Known MJD for 2026-02-20

    def test_mjd_17bit_mask(self):
        """Test that MJD is properly masked to 17 bits."""
        mjd = calculate_mjd(2050, 12, 31)
        assert mjd <= 0x1FFFF  # Must fit in 17 bits


class TestLTOCalculation:
    """Test Local Time Offset calculation."""

    def test_lto_auto_range(self):
        """Test that auto LTO is within valid range."""
        lto = calculate_lto_auto()
        assert -24 <= lto <= 24  # Valid range in half-hours


class TestFIG0_10:
    """Test FIG 0/10 (Date and Time) implementation."""

    def test_fig0_10_without_lto(self):
        """Test FIG 0/10 encoding without LTO (4 bytes data)."""
        # Create ensemble with datetime disabled for LTO
        dt_config = DateTimeConfig(
            enabled=True,
            source='manual',
            include_lto=False,
            utc_flag=True,
            manual_datetime=datetime(2026, 2, 20, 14, 30)
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            label=DabLabel(text="Test"),
            datetime=dt_config
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 6  # 2 header + 4 data

        # Verify header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[0] & 0x1F) == 5  # Length = 4 data + 1
        assert (buf[1] & 0x1F) == 10  # Extension 10

        # Verify MJD (2026-02-20 = MJD 61091 = 0xEEB3)
        mjd = ((buf[2] << 9) | (buf[3] << 1) | (buf[4] >> 7))
        assert mjd == 61091

        # Verify UTC flag
        utc_flag = (buf[4] >> 6) & 0x01
        assert utc_flag == 1

        # Verify hour (14)
        hour = buf[4] & 0x1F
        assert hour == 14

        # Verify minute (30)
        minute = (buf[5] >> 2) & 0x3F
        assert minute == 30

    def test_fig0_10_with_lto(self):
        """Test FIG 0/10 encoding with LTO (6 bytes data)."""
        dt_config = DateTimeConfig(
            enabled=True,
            source='manual',
            include_lto=True,
            utc_flag=True,
            confidence=True,
            manual_datetime=datetime(2026, 2, 20, 14, 30)
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            label=DabLabel(text="Test"),
            datetime=dt_config,
            lto_auto=False,
            lto=1  # +0.5 hours (UTC+0:30)
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 8  # 2 header + 6 data

        # Verify length
        assert (buf[0] & 0x1F) == 7  # Length = 6 data + 1

        # Verify LTO (byte 6)
        lto_sign = (buf[6] >> 5) & 0x01
        lto_value = buf[6] & 0x1F
        assert lto_sign == 0  # Positive
        assert lto_value == 1  # 1 half-hour

        # Verify confidence (byte 7)
        confidence = (buf[7] >> 7) & 0x01
        assert confidence == 1

    def test_fig0_10_negative_lto(self):
        """Test FIG 0/10 with negative LTO."""
        dt_config = DateTimeConfig(
            enabled=True,
            source='manual',
            include_lto=True,
            manual_datetime=datetime(2026, 2, 20, 14, 30)
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            datetime=dt_config,
            lto_auto=False,
            lto=-2  # -1 hour (UTC-1:00)
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify LTO sign is negative
        lto_sign = (buf[6] >> 5) & 0x01
        lto_value = buf[6] & 0x1F
        assert lto_sign == 1  # Negative
        assert lto_value == 2  # 2 half-hours

    def test_fig0_10_auto_lto(self):
        """Test FIG 0/10 with automatic LTO calculation."""
        dt_config = DateTimeConfig(
            enabled=True,
            source='system',
            include_lto=True
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            datetime=dt_config,
            lto_auto=True
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should successfully encode with auto-calculated LTO
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 8

        # LTO should be in valid range
        lto_sign = (buf[6] >> 5) & 0x01
        lto_value = buf[6] & 0x1F
        assert lto_value <= 24

    def test_fig0_10_system_time(self):
        """Test FIG 0/10 with system time source."""
        dt_config = DateTimeConfig(
            enabled=True,
            source='system',
            include_lto=False
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            datetime=dt_config
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should successfully encode with current system time
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 6

        # Verify MJD is reasonable (not zero)
        mjd = ((buf[2] << 9) | (buf[3] << 1) | (buf[4] >> 7))
        assert mjd > 50000  # Should be after year 1996

    def test_fig0_10_insufficient_space(self):
        """Test FIG 0/10 with insufficient buffer space."""
        dt_config = DateTimeConfig(
            enabled=True,
            include_lto=True
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            datetime=dt_config
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 5)  # Only 5 bytes, need 8

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_10_midnight(self):
        """Test FIG 0/10 at midnight."""
        dt_config = DateTimeConfig(
            enabled=True,
            source='manual',
            include_lto=False,
            manual_datetime=datetime(2026, 1, 1, 0, 0)
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            datetime=dt_config
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify hour is 0
        hour = buf[4] & 0x1F
        assert hour == 0

        # Verify minute is 0
        minute = (buf[5] >> 2) & 0x3F
        assert minute == 0

    def test_fig0_10_last_minute(self):
        """Test FIG 0/10 at 23:59."""
        dt_config = DateTimeConfig(
            enabled=True,
            source='manual',
            include_lto=False,
            manual_datetime=datetime(2026, 12, 31, 23, 59)
        )
        ensemble = DabEnsemble(
            id=0xCE15,
            datetime=dt_config
        )

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify hour is 23
        hour = buf[4] & 0x1F
        assert hour == 23

        # Verify minute is 59
        minute = (buf[5] >> 2) & 0x3F
        assert minute == 59

    def test_fig0_10_repetition_rate(self):
        """Test that FIG 0/10 has correct repetition rate."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_10(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.B

    def test_fig0_10_priority(self):
        """Test that FIG 0/10 has correct priority."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_10(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.NORMAL
