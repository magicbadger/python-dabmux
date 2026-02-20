"""
Unit tests for FIG 0/18 (Announcement Support).
"""
import pytest
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabLabel, AnnouncementConfig
)
from dabmux.fig.fig0 import FIG0_18, ANNOUNCEMENT_TYPES


class TestFIG0_18:
    """Test FIG 0/18 (Announcement Support) implementation."""

    def test_fig0_18_single_service_single_type(self):
        """Test FIG 0/18 with single service and single announcement type."""
        ann_config = AnnouncementConfig(
            enabled=True,
            types=['alarm']
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            label=DabLabel(text="Service 1"),
            clusters=[1],
            announcements=ann_config
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 8  # 2 header + 6 data (SId+ASU+flags+1 cluster)

        # Verify header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[1] & 0x1F) == 18  # Extension 18

        # Verify service ID
        service_id = (buf[2] << 8) | buf[3]
        assert service_id == 0x5001

        # Verify ASU flags (alarm = bit 0)
        asu = (buf[4] << 8) | buf[5]
        assert asu & 0x0001 == 1  # Alarm bit set

        # Verify cluster count
        cluster_count = (buf[6] >> 3) & 0x1F
        assert cluster_count == 1

        # Verify cluster ID
        assert buf[7] == 1

    def test_fig0_18_multiple_types(self):
        """Test FIG 0/18 with multiple announcement types."""
        ann_config = AnnouncementConfig(
            enabled=True,
            types=['alarm', 'news', 'traffic']
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            announcements=ann_config,
            clusters=[]
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify ASU flags (alarm=0, traffic=1, news=4)
        asu = (buf[4] << 8) | buf[5]
        assert asu & (1 << 0) != 0  # Alarm
        assert asu & (1 << 1) != 0  # Traffic
        assert asu & (1 << 4) != 0  # News

    def test_fig0_18_all_announcement_types(self):
        """Test FIG 0/18 with all announcement types."""
        ann_types = list(ANNOUNCEMENT_TYPES.keys())
        ann_config = AnnouncementConfig(
            enabled=True,
            types=ann_types
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            announcements=ann_config
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify all bits are set
        asu = (buf[4] << 8) | buf[5]
        for bit_pos in ANNOUNCEMENT_TYPES.values():
            assert asu & (1 << bit_pos) != 0

    def test_fig0_18_multiple_clusters(self):
        """Test FIG 0/18 with multiple clusters."""
        ann_config = AnnouncementConfig(
            enabled=True,
            types=['alarm']
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            announcements=ann_config,
            clusters=[1, 2, 3]
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify cluster count
        cluster_count = (buf[6] >> 3) & 0x1F
        assert cluster_count == 3

        # Verify cluster IDs
        assert buf[7] == 1
        assert buf[8] == 2
        assert buf[9] == 3

    def test_fig0_18_new_flag(self):
        """Test FIG 0/18 with new flag set."""
        ann_config = AnnouncementConfig(
            enabled=True,
            types=['alarm'],
            new_flag=True
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            announcements=ann_config
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify new flag (bit 2)
        new_flag = (buf[6] >> 2) & 0x01
        assert new_flag == 1

    def test_fig0_18_region_flag(self):
        """Test FIG 0/18 with region flag set."""
        ann_config = AnnouncementConfig(
            enabled=True,
            types=['alarm'],
            region_flag=True
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            announcements=ann_config
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify region flag (bit 1)
        region_flag = (buf[6] >> 1) & 0x01
        assert region_flag == 1

    def test_fig0_18_combine_with_asu_field(self):
        """Test FIG 0/18 combines types list with pre-set asu field."""
        ann_config = AnnouncementConfig(
            enabled=True,
            types=['alarm']  # alarm = bit 0
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            asu=0x0010,  # Pre-set bit 4 (news)
            announcements=ann_config
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify both bits are set
        asu = (buf[4] << 8) | buf[5]
        assert asu & (1 << 0) != 0  # Alarm from types
        assert asu & (1 << 4) != 0  # News from pre-set asu

    def test_fig0_18_multiple_services(self):
        """Test FIG 0/18 with multiple services."""
        ensemble = DabEnsemble(id=0xCE15)

        for i in range(3):
            ann_config = AnnouncementConfig(
                enabled=True,
                types=['alarm']
            )
            service = DabService(
                uid=f'svc{i}',
                id=0x5000 + i,
                announcements=ann_config
            )
            ensemble.services.append(service)

        fig = FIG0_18(ensemble)

        # With enough space, should encode all services
        buf = bytearray(32)
        status = fig.fill(buf, 32)
        assert status.complete_fig_transmitted is True
        # 3 services * 5 bytes (no clusters) + 2 header = 17 bytes
        assert status.num_bytes_written == 17

    def test_fig0_18_no_announcements(self):
        """Test FIG 0/18 with no services having announcements."""
        service = DabService(
            uid='svc1',
            id=0x5001
            # announcements.enabled defaults to False
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_18_insufficient_space(self):
        """Test FIG 0/18 with insufficient buffer space."""
        ann_config = AnnouncementConfig(
            enabled=True,
            types=['alarm']
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            announcements=ann_config
        )
        ensemble = DabEnsemble(id=0xCE15)
        ensemble.services.append(service)

        fig = FIG0_18(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 6)  # Only 6 bytes, need 7 minimum

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_18_repetition_rate(self):
        """Test that FIG 0/18 has correct repetition rate."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_18(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.B

    def test_fig0_18_priority(self):
        """Test that FIG 0/18 has correct priority."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_18(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.NORMAL
