"""
Unit tests for FIG 0/9 (Extended Country Code and LTO).
"""
import pytest
from dabmux.core.mux_elements import DabEnsemble, DabService, DabLabel
from dabmux.fig.fig0 import FIG0_9


class TestFIG0_9:
    """Test FIG 0/9 (Extended Country Code) implementation."""

    def test_fig0_9_single_service(self):
        """Test FIG 0/9 encoding for single service."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,  # UK
            label=DabLabel(text="Test"),
            international_table=1,
            lto_auto=False,
            lto=0  # UTC
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            label=DabLabel(text="Service 1")
        )
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 7  # 2 header + 5 data

        # Verify header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[0] & 0x1F) == 6  # Length = 5 data + 1
        assert (buf[1] & 0x1F) == 9  # Extension 9

        # Verify long form flag (bit 7 of byte 2)
        long_form = (buf[2] >> 7) & 0x01
        assert long_form == 1

        # Verify LTO (UTC = 0)
        lto_sign = (buf[2] >> 5) & 0x01
        lto_value = buf[2] & 0x1F
        assert lto_sign == 0
        assert lto_value == 0

        # Verify service ID (bytes 3-4)
        service_id = (buf[3] << 8) | buf[4]
        assert service_id == 0x5001

        # Verify ECC (byte 5)
        assert buf[5] == 0xE1

        # Verify international table (byte 6)
        assert buf[6] == 1

    def test_fig0_9_positive_lto(self):
        """Test FIG 0/9 with positive LTO."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE0,  # Germany
            lto_auto=False,
            lto=2  # UTC+1:00
        )
        service = DabService(uid='svc1', id=0x5001)
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify LTO encoding
        lto_sign = (buf[2] >> 5) & 0x01
        lto_value = buf[2] & 0x1F
        assert lto_sign == 0  # Positive
        assert lto_value == 2  # 2 half-hours

    def test_fig0_9_negative_lto(self):
        """Test FIG 0/9 with negative LTO."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xA2,  # USA (East Coast)
            lto_auto=False,
            lto=-10  # UTC-5:00
        )
        service = DabService(uid='svc1', id=0x5001)
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify LTO encoding
        lto_sign = (buf[2] >> 5) & 0x01
        lto_value = buf[2] & 0x1F
        assert lto_sign == 1  # Negative
        assert lto_value == 10  # 10 half-hours

    def test_fig0_9_auto_lto(self):
        """Test FIG 0/9 with automatic LTO calculation."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            lto_auto=True
        )
        service = DabService(uid='svc1', id=0x5001)
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should successfully encode with auto-calculated LTO
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 7

        # LTO value should be in valid range
        lto_value = buf[2] & 0x1F
        assert lto_value <= 24

    def test_fig0_9_service_specific_ecc(self):
        """Test FIG 0/9 with service-specific ECC."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,  # UK ensemble
            lto_auto=False,
            lto=0
        )
        service = DabService(
            uid='svc1',
            id=0x5001,
            ecc=0xE0  # German service on UK ensemble
        )
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify service-specific ECC is used
        assert buf[5] == 0xE0  # Not ensemble's 0xE1

    def test_fig0_9_multiple_services(self):
        """Test FIG 0/9 with multiple services (batched when space permits)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            lto_auto=False,
            lto=0
        )
        for i in range(3):
            service = DabService(
                uid=f'svc{i}',
                id=0x5000 + i
            )
            ensemble.services.append(service)

        fig = FIG0_9(ensemble)

        # With 32 bytes available, should encode all 3 services at once
        # 3 services * 5 bytes each = 15 bytes + 2 header bytes = 17 bytes
        buf = bytearray(32)
        status = fig.fill(buf, 32)
        assert status.num_bytes_written == 17
        assert status.complete_fig_transmitted is True

        # Verify all three service IDs are present
        service_id_1 = (buf[3] << 8) | buf[4]
        assert service_id_1 == 0x5000

        service_id_2 = (buf[8] << 8) | buf[9]
        assert service_id_2 == 0x5001

        service_id_3 = (buf[13] << 8) | buf[14]
        assert service_id_3 == 0x5002

    def test_fig0_9_iterative_limited_space(self):
        """Test FIG 0/9 with limited space forces iterative transmission."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            lto_auto=False,
            lto=0
        )
        for i in range(3):
            service = DabService(
                uid=f'svc{i}',
                id=0x5000 + i
            )
            ensemble.services.append(service)

        fig = FIG0_9(ensemble)

        # First call with limited space - should transmit only first service
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 8)  # Only 8 bytes: 2 header + 5 data + 1 spare
        assert status1.num_bytes_written == 7
        assert status1.complete_fig_transmitted is False
        service_id_1 = (buf1[3] << 8) | buf1[4]
        assert service_id_1 == 0x5000

        # Second call - should transmit second service
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 8)
        assert status2.num_bytes_written == 7
        assert status2.complete_fig_transmitted is False
        service_id_2 = (buf2[3] << 8) | buf2[4]
        assert service_id_2 == 0x5001

        # Third call - should transmit third service and complete
        buf3 = bytearray(32)
        status3 = fig.fill(buf3, 8)
        assert status3.num_bytes_written == 7
        assert status3.complete_fig_transmitted is True
        service_id_3 = (buf3[3] << 8) | buf3[4]
        assert service_id_3 == 0x5002

        # Fourth call - should restart from first service
        buf4 = bytearray(32)
        status4 = fig.fill(buf4, 8)
        assert status4.num_bytes_written == 7
        service_id_4 = (buf4[3] << 8) | buf4[4]
        assert service_id_4 == 0x5000

    def test_fig0_9_insufficient_space(self):
        """Test FIG 0/9 with insufficient buffer space."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='svc1', id=0x5001)
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 6)  # Only 6 bytes, need 7

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_9_no_services(self):
        """Test FIG 0/9 with no services."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_9_international_table_rds(self):
        """Test FIG 0/9 with RDS international table."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            international_table=1,  # RDS
            lto_auto=False,
            lto=0
        )
        service = DabService(uid='svc1', id=0x5001)
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify international table
        assert buf[6] == 1

    def test_fig0_9_international_table_rbds(self):
        """Test FIG 0/9 with RBDS (North America) international table."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xA2,
            international_table=2,  # RBDS (North America)
            lto_auto=False,
            lto=-10
        )
        service = DabService(uid='svc1', id=0x5001)
        ensemble.services.append(service)

        fig = FIG0_9(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify international table
        assert buf[6] == 2

    def test_fig0_9_repetition_rate(self):
        """Test that FIG 0/9 has correct repetition rate."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        fig = FIG0_9(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.B

    def test_fig0_9_priority(self):
        """Test that FIG 0/9 has correct priority."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        fig = FIG0_9(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.NORMAL
