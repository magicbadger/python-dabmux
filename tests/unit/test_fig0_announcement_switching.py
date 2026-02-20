"""
Unit tests for FIG 0/19 (Announcement Switching).
"""
import pytest
from dabmux.core.mux_elements import (
    DabEnsemble, DabLabel, ActiveAnnouncement
)
from dabmux.fig.fig0 import FIG0_19
from dabmux.mux import DabMultiplexer


class TestFIG0_19:
    """Test FIG 0/19 (Announcement Switching) implementation."""

    def test_fig0_19_no_announcements(self):
        """Test FIG 0/19 skips transmission when no active announcements."""
        ensemble = DabEnsemble(id=0xCE15)

        fig = FIG0_19(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_19_single_announcement(self):
        """Test FIG 0/19 with single active announcement."""
        ensemble = DabEnsemble(id=0xCE15)
        announcement = ActiveAnnouncement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2,
            new_flag=True,
            region_flag=False
        )
        ensemble.active_announcements.append(announcement)

        fig = FIG0_19(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 6  # 2 header + 4 data

        # Verify header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[1] & 0x1F) == 19  # Extension 19

        # Verify cluster ID
        assert buf[2] == 1

        # Verify ASU flags (alarm = bit 0)
        asu = (buf[3] << 8) | buf[4]
        assert asu & 0x0001 == 1

        # Verify subchannel ID (6 bits) + flags
        subchan_id = (buf[5] >> 2) & 0x3F
        assert subchan_id == 2

        # Verify new flag (bit 0)
        new_flag = buf[5] & 0x01
        assert new_flag == 1

        # Verify region flag (bit 1)
        region_flag = (buf[5] >> 1) & 0x01
        assert region_flag == 0

    def test_fig0_19_multiple_types(self):
        """Test FIG 0/19 with multiple announcement types."""
        ensemble = DabEnsemble(id=0xCE15)
        announcement = ActiveAnnouncement(
            cluster_id=1,
            types=['alarm', 'news', 'traffic'],
            subchannel_id=2
        )
        ensemble.active_announcements.append(announcement)

        fig = FIG0_19(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify ASU flags (alarm=0, traffic=1, news=4)
        asu = (buf[3] << 8) | buf[4]
        assert asu & (1 << 0) != 0  # Alarm
        assert asu & (1 << 1) != 0  # Traffic
        assert asu & (1 << 4) != 0  # News

    def test_fig0_19_with_region(self):
        """Test FIG 0/19 with region ID."""
        ensemble = DabEnsemble(id=0xCE15)
        announcement = ActiveAnnouncement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2,
            region_flag=True,
            region_id=42
        )
        ensemble.active_announcements.append(announcement)

        fig = FIG0_19(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # With region ID, should be 7 bytes (2 header + 5 data)
        assert status.num_bytes_written == 7

        # Verify region flag is set
        region_flag = (buf[5] >> 1) & 0x01
        assert region_flag == 1

        # Verify region ID
        assert buf[6] == 42

    def test_fig0_19_multiple_announcements(self):
        """Test FIG 0/19 with multiple active announcements."""
        ensemble = DabEnsemble(id=0xCE15)

        for i in range(3):
            announcement = ActiveAnnouncement(
                cluster_id=i + 1,
                types=['alarm'],
                subchannel_id=i + 2
            )
            ensemble.active_announcements.append(announcement)

        fig = FIG0_19(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # 3 announcements * 4 bytes + 2 header = 14 bytes
        assert status.num_bytes_written == 14

        # Verify first announcement
        assert buf[2] == 1  # Cluster 1
        subchan_1 = (buf[5] >> 2) & 0x3F
        assert subchan_1 == 2

        # Verify second announcement
        assert buf[6] == 2  # Cluster 2
        subchan_2 = (buf[9] >> 2) & 0x3F
        assert subchan_2 == 3

        # Verify third announcement
        assert buf[10] == 3  # Cluster 3
        subchan_3 = (buf[13] >> 2) & 0x3F
        assert subchan_3 == 4

    def test_fig0_19_dynamic_priority_active(self):
        """Test FIG 0/19 has HIGH priority when announcements active."""
        ensemble = DabEnsemble(id=0xCE15)
        announcement = ActiveAnnouncement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2
        )
        ensemble.active_announcements.append(announcement)

        fig = FIG0_19(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.HIGH

    def test_fig0_19_dynamic_priority_idle(self):
        """Test FIG 0/19 has NORMAL priority when no announcements."""
        ensemble = DabEnsemble(id=0xCE15)

        fig = FIG0_19(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.NORMAL

    def test_fig0_19_dynamic_rate_active(self):
        """Test FIG 0/19 uses Rate A when announcements active."""
        ensemble = DabEnsemble(id=0xCE15)
        announcement = ActiveAnnouncement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2
        )
        ensemble.active_announcements.append(announcement)

        fig = FIG0_19(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.A

    def test_fig0_19_dynamic_rate_idle(self):
        """Test FIG 0/19 uses Rate B when no announcements."""
        ensemble = DabEnsemble(id=0xCE15)

        fig = FIG0_19(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.B

    def test_fig0_19_insufficient_space(self):
        """Test FIG 0/19 with insufficient buffer space."""
        ensemble = DabEnsemble(id=0xCE15)
        announcement = ActiveAnnouncement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2
        )
        ensemble.active_announcements.append(announcement)

        fig = FIG0_19(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 5)  # Only 5 bytes, need 6

        # Should not write anything
        assert status.num_bytes_written == 0


class TestAnnouncementAPI:
    """Test announcement control API in DabMultiplexer."""

    def test_start_announcement(self):
        """Test starting an announcement."""
        ensemble = DabEnsemble(id=0xCE15, label=DabLabel(text="Test"))
        mux = DabMultiplexer(ensemble)

        mux.start_announcement(
            cluster_id=1,
            types=['alarm', 'news'],
            subchannel_id=2
        )

        # Verify announcement was added
        assert len(ensemble.active_announcements) == 1
        ann = ensemble.active_announcements[0]
        assert ann.cluster_id == 1
        assert ann.types == ['alarm', 'news']
        assert ann.subchannel_id == 2
        assert ann.new_flag is True
        assert ann.region_flag is False

    def test_start_announcement_with_region(self):
        """Test starting an announcement with region ID."""
        ensemble = DabEnsemble(id=0xCE15)
        mux = DabMultiplexer(ensemble)

        mux.start_announcement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2,
            region_id=42
        )

        ann = ensemble.active_announcements[0]
        assert ann.region_flag is True
        assert ann.region_id == 42

    def test_start_announcement_invalid_type(self):
        """Test starting announcement with invalid type raises error."""
        ensemble = DabEnsemble(id=0xCE15)
        mux = DabMultiplexer(ensemble)

        with pytest.raises(ValueError, match="Invalid announcement type"):
            mux.start_announcement(
                cluster_id=1,
                types=['invalid_type'],
                subchannel_id=2
            )

    def test_start_announcement_updates_existing(self):
        """Test starting announcement updates if cluster already active."""
        ensemble = DabEnsemble(id=0xCE15)
        mux = DabMultiplexer(ensemble)

        # Start first announcement
        mux.start_announcement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2
        )

        # Start same cluster again with different types
        mux.start_announcement(
            cluster_id=1,
            types=['news'],
            subchannel_id=3
        )

        # Should still have only one announcement (updated)
        assert len(ensemble.active_announcements) == 1
        ann = ensemble.active_announcements[0]
        assert ann.types == ['news']
        assert ann.subchannel_id == 3

    def test_stop_announcement(self):
        """Test stopping an announcement."""
        ensemble = DabEnsemble(id=0xCE15)
        mux = DabMultiplexer(ensemble)

        mux.start_announcement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2
        )

        # Stop the announcement
        result = mux.stop_announcement(cluster_id=1)

        assert result is True
        assert len(ensemble.active_announcements) == 0

    def test_stop_announcement_not_found(self):
        """Test stopping non-existent announcement returns False."""
        ensemble = DabEnsemble(id=0xCE15)
        mux = DabMultiplexer(ensemble)

        result = mux.stop_announcement(cluster_id=99)

        assert result is False

    def test_stop_announcement_multiple(self):
        """Test stopping one announcement leaves others active."""
        ensemble = DabEnsemble(id=0xCE15)
        mux = DabMultiplexer(ensemble)

        mux.start_announcement(cluster_id=1, types=['alarm'], subchannel_id=2)
        mux.start_announcement(cluster_id=2, types=['news'], subchannel_id=3)

        # Stop only cluster 1
        mux.stop_announcement(cluster_id=1)

        assert len(ensemble.active_announcements) == 1
        assert ensemble.active_announcements[0].cluster_id == 2

    def test_fig0_19_integration(self):
        """Test FIG 0/19 integration with multiplexer API."""
        ensemble = DabEnsemble(id=0xCE15)
        mux = DabMultiplexer(ensemble)

        # Start announcement
        mux.start_announcement(
            cluster_id=1,
            types=['alarm'],
            subchannel_id=2
        )

        # FIG 0/19 should now transmit data
        fig = FIG0_19(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written > 0

        # Stop announcement
        mux.stop_announcement(cluster_id=1)

        # FIG 0/19 should now skip transmission
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)

        assert status2.num_bytes_written == 0
