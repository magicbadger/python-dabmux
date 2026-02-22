"""
Unit tests for FIG Type 6 (Conditional Access).

Tests FIG 6/0 (CA Organization) and FIG 6/1 (CA Service).
"""
import pytest
from dabmux.fig.fig6 import FIG6_0, FIG6_1
from dabmux.fig.base import FIGRate, FIGPriority
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, ConditionalAccessConfig, DabLabel
)


class TestFIG6_0_Header:
    """Tests for FIG 6/0 header encoding."""

    def test_header_type_and_extension(self):
        """Test FIG 6/0 header has correct type and extension."""
        ensemble = DabEnsemble()
        ensemble.conditional_access = ConditionalAccessConfig(
            enabled=True,
            systems=[0x5601]  # Nagravision
        )

        fig = FIG6_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        # Header byte 0: Type=6, Length=3 (1 byte header + 2 bytes data)
        assert (buf[0] >> 5) == 6, "FIG type should be 6"
        assert (buf[0] & 0x1F) == 3, "Length should be 3 (1 + 2 bytes)"

        # Header byte 1: CN=0, OE=0, PD=0, Extension=0
        assert (buf[1] >> 7) == 0, "CN should be 0"
        assert ((buf[1] >> 6) & 0x01) == 0, "OE should be 0"
        assert ((buf[1] >> 5) & 0x01) == 0, "PD should be 0"
        assert (buf[1] & 0x1F) == 0, "Extension should be 0"

    def test_single_ca_system(self):
        """Test FIG 6/0 with single CA system."""
        ensemble = DabEnsemble()
        ensemble.conditional_access = ConditionalAccessConfig(
            enabled=True,
            systems=[0x5601]  # Nagravision
        )

        fig = FIG6_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 4, "Should write 4 bytes (2 header + 2 CAId)"
        assert status.complete_fig_transmitted is True

        # CAId: 0x5601 at bytes 2-3 (big-endian)
        caid = (buf[2] << 8) | buf[3]
        assert caid == 0x5601, f"CAId should be 0x5601, got 0x{caid:04X}"

    def test_multiple_ca_systems(self):
        """Test FIG 6/0 with multiple CA systems."""
        ensemble = DabEnsemble()
        ensemble.conditional_access = ConditionalAccessConfig(
            enabled=True,
            systems=[0x5601, 0x4A10, 0x5901]  # Nagravision, DigitalRadio, VideoGuard
        )

        fig = FIG6_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 8, "Should write 8 bytes (2 header + 6 CAId)"
        assert status.complete_fig_transmitted is True

        # Extract CAIds
        caids = []
        for i in range(3):
            offset = 2 + (i * 2)
            caid = (buf[offset] << 8) | buf[offset + 1]
            caids.append(caid)

        assert caids == [0x5601, 0x4A10, 0x5901], f"CAIds mismatch: {caids}"


class TestFIG6_0_EdgeCases:
    """Tests for FIG 6/0 edge cases."""

    def test_ca_disabled(self):
        """Test FIG 6/0 when CA is disabled."""
        ensemble = DabEnsemble()
        ensemble.conditional_access = ConditionalAccessConfig(enabled=False)

        fig = FIG6_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 0, "Should not write anything"
        assert status.complete_fig_transmitted is True

    def test_no_ca_systems(self):
        """Test FIG 6/0 with empty CA systems list."""
        ensemble = DabEnsemble()
        ensemble.conditional_access = ConditionalAccessConfig(
            enabled=True,
            systems=[]
        )

        fig = FIG6_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 0, "Should not write anything"
        assert status.complete_fig_transmitted is True

    def test_ca_not_configured(self):
        """Test FIG 6/0 when CA is not configured at all."""
        ensemble = DabEnsemble()
        ensemble.conditional_access = None

        fig = FIG6_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 0, "Should not write anything"
        assert status.complete_fig_transmitted is True

    def test_insufficient_space(self):
        """Test FIG 6/0 with insufficient buffer space."""
        ensemble = DabEnsemble()
        ensemble.conditional_access = ConditionalAccessConfig(
            enabled=True,
            systems=[0x5601]
        )

        fig = FIG6_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 3)  # Need 4 bytes but only give 3

        assert status.num_bytes_written == 0, "Should not write partial data"
        assert status.complete_fig_transmitted is False


class TestFIG6_0_Metadata:
    """Tests for FIG 6/0 metadata."""

    def test_repetition_rate(self):
        """Test FIG 6/0 repetition rate is C."""
        ensemble = DabEnsemble()
        fig = FIG6_0(ensemble)
        assert fig.repetition_rate() == FIGRate.C

    def test_priority(self):
        """Test FIG 6/0 priority is NORMAL."""
        ensemble = DabEnsemble()
        fig = FIG6_0(ensemble)
        assert fig.priority() == FIGPriority.NORMAL

    def test_fig_type(self):
        """Test FIG 6/0 fig_type returns 6."""
        ensemble = DabEnsemble()
        fig = FIG6_0(ensemble)
        assert fig.fig_type() == 6

    def test_fig_extension(self):
        """Test FIG 6/0 fig_extension returns 0."""
        ensemble = DabEnsemble()
        fig = FIG6_0(ensemble)
        assert fig.fig_extension() == 0


class TestFIG6_1_Header:
    """Tests for FIG 6/1 header encoding."""

    def test_header_type_and_extension(self):
        """Test FIG 6/1 header has correct type and extension."""
        ensemble = DabEnsemble()
        service = DabService(
            uid='s1',
            id=0x5001,
            ca_system=0x5601,
            label=DabLabel(text='Test')
        )
        ensemble.services = [service]

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        # Header byte 0: Type=6, Length=5 (1 byte header + 4 bytes data)
        assert (buf[0] >> 5) == 6, "FIG type should be 6"
        assert (buf[0] & 0x1F) == 5, "Length should be 5 (1 + 2 SId + 2 CAId)"

        # Header byte 1: Extension=1
        assert (buf[1] & 0x1F) == 1, "Extension should be 1"

    def test_pd_flag_programme_service(self):
        """Test PD flag is 0 for programme services (16-bit SId)."""
        ensemble = DabEnsemble()
        service = DabService(
            uid='s1',
            id=0x5001,  # 16-bit programme service
            ca_system=0x5601,
            label=DabLabel(text='Test')
        )
        ensemble.services = [service]

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        # PD flag should be 0 for programme service
        pd = (buf[1] >> 5) & 0x01
        assert pd == 0, "PD should be 0 for programme service"

    def test_pd_flag_data_service(self):
        """Test PD flag is 1 for data services (32-bit SId)."""
        ensemble = DabEnsemble()
        service = DabService(
            uid='s1',
            id=0x10001,  # 32-bit data service
            ca_system=0x5601,
            label=DabLabel(text='Test')
        )
        ensemble.services = [service]

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        # PD flag should be 1 for data service
        pd = (buf[1] >> 5) & 0x01
        assert pd == 1, "PD should be 1 for data service"


class TestFIG6_1_ServiceEncoding:
    """Tests for FIG 6/1 service entry encoding."""

    def test_single_service_16bit_sid(self):
        """Test FIG 6/1 with single service (16-bit SId)."""
        ensemble = DabEnsemble()
        service = DabService(
            uid='s1',
            id=0x5001,
            ca_system=0x5601,
            label=DabLabel(text='Test')
        )
        ensemble.services = [service]

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 6, "Should write 6 bytes (2 header + 2 SId + 2 CAId)"
        assert status.complete_fig_transmitted is True

        # SId: 0x5001 at bytes 2-3 (big-endian, 16-bit)
        sid = (buf[2] << 8) | buf[3]
        assert sid == 0x5001, f"SId should be 0x5001, got 0x{sid:04X}"

        # CAId: 0x5601 at bytes 4-5
        caid = (buf[4] << 8) | buf[5]
        assert caid == 0x5601, f"CAId should be 0x5601, got 0x{caid:04X}"

    def test_single_service_32bit_sid(self):
        """Test FIG 6/1 with single data service (32-bit SId)."""
        ensemble = DabEnsemble()
        service = DabService(
            uid='s1',
            id=0x12345678,  # 32-bit data service
            ca_system=0x4A10,
            label=DabLabel(text='Test')
        )
        ensemble.services = [service]

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 8, "Should write 8 bytes (2 header + 4 SId + 2 CAId)"

        # SId: 0x12345678 at bytes 2-5 (big-endian, 32-bit)
        sid = (buf[2] << 24) | (buf[3] << 16) | (buf[4] << 8) | buf[5]
        assert sid == 0x12345678, f"SId should be 0x12345678, got 0x{sid:08X}"

        # CAId: 0x4A10 at bytes 6-7
        caid = (buf[6] << 8) | buf[7]
        assert caid == 0x4A10, f"CAId should be 0x4A10, got 0x{caid:04X}"

    def test_multiple_services(self):
        """Test FIG 6/1 with multiple services."""
        ensemble = DabEnsemble()
        services = [
            DabService(uid='s1', id=0x5001, ca_system=0x5601, label=DabLabel(text='Test1')),
            DabService(uid='s2', id=0x5002, ca_system=0x5601, label=DabLabel(text='Test2')),
            DabService(uid='s3', id=0x5003, ca_system=0x4A10, label=DabLabel(text='Test3')),
        ]
        ensemble.services = services

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        # 3 services × 4 bytes (2 SId + 2 CAId) + 2 header = 14 bytes
        assert status.num_bytes_written == 14

        # Verify each service entry
        pos = 2
        for svc in services:
            sid = (buf[pos] << 8) | buf[pos + 1]
            caid = (buf[pos + 2] << 8) | buf[pos + 3]
            assert sid == svc.id
            assert caid == svc.ca_system
            pos += 4


class TestFIG6_1_EdgeCases:
    """Tests for FIG 6/1 edge cases."""

    def test_no_ca_services(self):
        """Test FIG 6/1 with no CA services."""
        ensemble = DabEnsemble()
        service = DabService(
            uid='s1',
            id=0x5001,
            ca_system=None,  # Free-to-air
            label=DabLabel(text='Test')
        )
        ensemble.services = [service]

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        assert status.num_bytes_written == 0, "Should not write anything"
        assert status.complete_fig_transmitted is True

    def test_mixed_ca_and_fta_services(self):
        """Test FIG 6/1 with mix of CA and free-to-air services."""
        ensemble = DabEnsemble()
        services = [
            DabService(uid='s1', id=0x5001, ca_system=0x5601, label=DabLabel(text='CA')),
            DabService(uid='s2', id=0x5002, ca_system=None, label=DabLabel(text='FTA')),
            DabService(uid='s3', id=0x5003, ca_system=0x4A10, label=DabLabel(text='CA2')),
        ]
        ensemble.services = services

        fig = FIG6_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, len(buf))

        # Should only encode CA services (2 services × 4 bytes + 2 header = 10 bytes)
        assert status.num_bytes_written == 10

    def test_iterative_transmission(self):
        """Test FIG 6/1 iterative transmission."""
        ensemble = DabEnsemble()
        services = [
            DabService(uid='s1', id=0x5001, ca_system=0x5601, label=DabLabel(text='Test1')),
            DabService(uid='s2', id=0x5002, ca_system=0x5601, label=DabLabel(text='Test2')),
        ]
        ensemble.services = services

        fig = FIG6_1(ensemble)
        buf = bytearray(32)

        # First call should transmit both services
        status = fig.fill(buf, len(buf))
        assert status.complete_fig_transmitted is True
        assert fig.service_index == 0, "Index should reset to 0"

        # Second call should also transmit both services (circular)
        status = fig.fill(buf, len(buf))
        assert status.complete_fig_transmitted is True

    def test_insufficient_space_iterative(self):
        """Test FIG 6/1 with insufficient space requires iteration."""
        ensemble = DabEnsemble()
        services = [
            DabService(uid='s1', id=0x5001, ca_system=0x5601, label=DabLabel(text='Test1')),
            DabService(uid='s2', id=0x5002, ca_system=0x5601, label=DabLabel(text='Test2')),
        ]
        ensemble.services = services

        fig = FIG6_1(ensemble)
        buf = bytearray(32)

        # First call with limited space (can fit 1 service only)
        status = fig.fill(buf, 6)  # 2 header + 4 service = 6 bytes for 1 service
        assert status.num_bytes_written == 6
        assert status.complete_fig_transmitted is False, "Should not be complete"

        # Second call should transmit the remaining service
        status = fig.fill(buf, 6)
        assert status.num_bytes_written == 6
        assert status.complete_fig_transmitted is True


class TestFIG6_1_Metadata:
    """Tests for FIG 6/1 metadata."""

    def test_repetition_rate(self):
        """Test FIG 6/1 repetition rate is C."""
        ensemble = DabEnsemble()
        fig = FIG6_1(ensemble)
        assert fig.repetition_rate() == FIGRate.C

    def test_priority(self):
        """Test FIG 6/1 priority is NORMAL."""
        ensemble = DabEnsemble()
        fig = FIG6_1(ensemble)
        assert fig.priority() == FIGPriority.NORMAL

    def test_fig_type(self):
        """Test FIG 6/1 fig_type returns 6."""
        ensemble = DabEnsemble()
        fig = FIG6_1(ensemble)
        assert fig.fig_type() == 6

    def test_fig_extension(self):
        """Test FIG 6/1 fig_extension returns 1."""
        ensemble = DabEnsemble()
        fig = FIG6_1(ensemble)
        assert fig.fig_extension() == 1
