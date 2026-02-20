"""
Unit tests for FIG 0/24 (Other Ensemble Services).
"""
import pytest
import struct
from dabmux.core.mux_elements import DabEnsemble, DabLabel, OtherEnsembleService
from dabmux.fig.fig0 import FIG0_24


class TestFIG0_24:
    """Test FIG 0/24 (Other Ensemble Services) implementation."""

    def test_fig0_24_single_service(self):
        """Test FIG 0/24 encoding with single OE service."""
        # Create ensemble with one other ensemble service
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test")
        )

        oe_svc = OtherEnsembleService(
            ecc=0xE2,
            ensemble_id=0x1000,
            service_id=0x5001,
            ca_id=0,
            is_32bit_sid=False
        )
        ensemble.other_ensemble_services.append(oe_svc)

        fig = FIG0_24(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 8  # 2 header + 6 data

        # Verify header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[0] & 0x1F) == 7  # Length = 6 data + 1
        assert (buf[1] & 0x1F) == 24  # Extension 24

        # Verify data
        # Byte 2: ECC
        assert buf[2] == 0xE2

        # Bytes 3-4: Ensemble ID
        ens_id = struct.unpack('>H', buf[3:5])[0]
        assert ens_id == 0x1000

        # Byte 5: Number of services (5 bits) + CAId flag + Rfa
        num_services = (buf[5] >> 3) & 0x1F
        assert num_services == 1

        # Bytes 6-7: Service ID (16-bit)
        svc_id = struct.unpack('>H', buf[6:8])[0]
        assert svc_id == 0x5001

    def test_fig0_24_multiple_services_same_ensemble(self):
        """Test FIG 0/24 with multiple services from same ensemble."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Add multiple services from same ensemble
        for svc_id in [0x5001, 0x5002, 0x5003]:
            oe_svc = OtherEnsembleService(
                ecc=0xE2,
                ensemble_id=0x1000,
                service_id=svc_id,
                is_32bit_sid=False
            )
            ensemble.other_ensemble_services.append(oe_svc)

        fig = FIG0_24(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should transmit all services in one go (same ensemble)
        assert status.complete_fig_transmitted is True

        # Verify number of services
        num_services = (buf[5] >> 3) & 0x1F
        assert num_services == 3

        # Verify all service IDs
        svc_ids = []
        for i in range(3):
            svc_id = struct.unpack('>H', buf[6 + i*2:8 + i*2])[0]
            svc_ids.append(svc_id)
        assert svc_ids == [0x5001, 0x5002, 0x5003]

    def test_fig0_24_multiple_ensembles(self):
        """Test FIG 0/24 with services from multiple ensembles."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Add services from different ensembles
        for ens_id in [0x1000, 0x2000]:
            oe_svc = OtherEnsembleService(
                ecc=0xE2,
                ensemble_id=ens_id,
                service_id=0x5001,
                is_32bit_sid=False
            )
            ensemble.other_ensemble_services.append(oe_svc)

        fig = FIG0_24(ensemble)
        buf = bytearray(64)

        # First call - should transmit first ensemble
        status1 = fig.fill(buf, 64)
        assert status1.num_bytes_written > 0
        assert status1.complete_fig_transmitted is False

        # Second call - should transmit second ensemble
        buf2 = bytearray(64)
        status2 = fig.fill(buf2, 64)
        assert status2.num_bytes_written > 0
        assert status2.complete_fig_transmitted is True

        # Verify different ensemble IDs
        ens_id1 = struct.unpack('>H', buf[3:5])[0]
        ens_id2 = struct.unpack('>H', buf2[3:5])[0]
        assert {ens_id1, ens_id2} == {0x1000, 0x2000}

    def test_fig0_24_32bit_service_id(self):
        """Test FIG 0/24 with 32-bit service ID."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        oe_svc = OtherEnsembleService(
            ecc=0xE2,
            ensemble_id=0x1000,
            service_id=0x12345678,  # 32-bit
            is_32bit_sid=True
        )
        ensemble.other_ensemble_services.append(oe_svc)

        fig = FIG0_24(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should write more bytes (4 for SId instead of 2)
        assert status.num_bytes_written == 10  # 2 header + 8 data

        # Verify 32-bit service ID
        svc_id = struct.unpack('>I', buf[6:10])[0]
        assert svc_id == 0x12345678

    def test_fig0_24_ecc_encoding(self):
        """Test FIG 0/24 ECC field encoding."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Test various ECC values
        for ecc in [0xE0, 0xE1, 0xE2, 0xF0]:
            ensemble.other_ensemble_services = []  # Reset
            oe_svc = OtherEnsembleService(
                ecc=ecc,
                ensemble_id=0x1000,
                service_id=0x5001,
                is_32bit_sid=False
            )
            ensemble.other_ensemble_services.append(oe_svc)

            fig = FIG0_24(ensemble)
            buf = bytearray(32)
            fig.fill(buf, 32)

            # Verify ECC
            assert buf[2] == ecc

    def test_fig0_24_insufficient_space(self):
        """Test FIG 0/24 with insufficient buffer space."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        oe_svc = OtherEnsembleService(
            ecc=0xE2,
            ensemble_id=0x1000,
            service_id=0x5001,
            is_32bit_sid=False
        )
        ensemble.other_ensemble_services.append(oe_svc)

        fig = FIG0_24(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 5)  # Only 5 bytes, need 8

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_24_no_oe_services(self):
        """Test FIG 0/24 with no OE services (skip behavior)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        # No OE services

        fig = FIG0_24(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_24_iterative_transmission(self):
        """Test FIG 0/24 iterative transmission across ensembles."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Add services from 3 different ensembles
        for ens_id in [0x1000, 0x2000, 0x3000]:
            oe_svc = OtherEnsembleService(
                ecc=0xE2,
                ensemble_id=ens_id,
                service_id=0x5001,
                is_32bit_sid=False
            )
            ensemble.other_ensemble_services.append(oe_svc)

        fig = FIG0_24(ensemble)
        transmitted_ensembles = []

        # Transmit iteratively
        for _ in range(3):
            buf = bytearray(32)
            status = fig.fill(buf, 32)
            assert status.num_bytes_written > 0

            # Extract ensemble ID
            ens_id = struct.unpack('>H', buf[3:5])[0]
            transmitted_ensembles.append(ens_id)

        # Should have transmitted all 3 ensembles
        assert set(transmitted_ensembles) == {0x1000, 0x2000, 0x3000}

    def test_fig0_24_grouping_by_ensemble(self):
        """Test FIG 0/24 groups services by ensemble correctly."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Add services: 2 from ens1, 1 from ens2, 2 from ens1 again
        services_config = [
            (0x1000, 0x5001),
            (0x1000, 0x5002),
            (0x2000, 0x6001),
            (0x1000, 0x5003),
        ]

        for ens_id, svc_id in services_config:
            oe_svc = OtherEnsembleService(
                ecc=0xE2,
                ensemble_id=ens_id,
                service_id=svc_id,
                is_32bit_sid=False
            )
            ensemble.other_ensemble_services.append(oe_svc)

        fig = FIG0_24(ensemble)

        # First transmission - should group all services from 0x1000
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)

        ens_id1 = struct.unpack('>H', buf1[3:5])[0]
        num_services1 = (buf1[5] >> 3) & 0x1F

        # Second transmission - should have services from 0x2000
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)

        ens_id2 = struct.unpack('>H', buf2[3:5])[0]
        num_services2 = (buf2[5] >> 3) & 0x1F

        # Verify grouping
        if ens_id1 == 0x1000:
            assert num_services1 == 3  # 3 services from 0x1000
            assert ens_id2 == 0x2000
            assert num_services2 == 1  # 1 service from 0x2000
        else:
            assert ens_id1 == 0x2000
            assert num_services1 == 1
            assert ens_id2 == 0x1000
            assert num_services2 == 3

    def test_fig0_24_repetition_rate(self):
        """Test that FIG 0/24 has correct repetition rate."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_24(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.C

    def test_fig0_24_priority(self):
        """Test that FIG 0/24 has correct priority."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_24(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.NORMAL
