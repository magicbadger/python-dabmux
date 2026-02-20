"""
Unit tests for FIG 0/6 (Service Linking).
"""
import pytest
import struct
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabLabel,
    ServiceLink, ServiceLinkage
)
from dabmux.fig.fig0 import FIG0_6


class TestFIG0_6:
    """Test FIG 0/6 (Service Linking) implementation."""

    def test_fig0_6_dab_link(self):
        """Test FIG 0/6 encoding with DAB link (IdLQ=0)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)

        link = ServiceLink(
            idlq=0,  # DAB
            lsn=100,
            hard_link=True,
            ils=False,
            target_ecc=0xE1,
            target_ensemble_id=0x4FFF,
            target_service_id=0x6001
        )
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 11  # 2 header + 9 data

        # Verify header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[0] & 0x1F) == 10  # Length = 9 data + 1
        assert (buf[1] & 0x1F) == 6  # Extension 6

        # Verify data
        # Bytes 2-3: Service ID
        svc_id = struct.unpack('>H', buf[2:4])[0]
        assert svc_id == 0x5001

        # Byte 4: IdLQ (2 bits) + LSN high (6 bits)
        idlq = (buf[4] >> 6) & 0x03
        lsn_high = buf[4] & 0x3F
        assert idlq == 0

        # Byte 5: LSN low (6 bits) + Hard/Soft + ILS
        lsn_low = (buf[5] >> 2) & 0x3F
        hard = (buf[5] >> 1) & 0x01
        ils = buf[5] & 0x01

        # Reconstruct LSN
        lsn = (lsn_high << 6) | lsn_low
        assert lsn == 100
        assert hard == 0  # 0 = hard link
        assert ils == 0

        # DAB target IDs
        # Byte 6: ECC
        assert buf[6] == 0xE1

        # Bytes 7-8: Ensemble ID
        target_ens = struct.unpack('>H', buf[7:9])[0]
        assert target_ens == 0x4FFF

        # Bytes 9-10: Service ID (16-bit)
        target_svc = struct.unpack('>H', buf[9:11])[0]
        assert target_svc == 0x6001

    def test_fig0_6_rds_link(self):
        """Test FIG 0/6 encoding with RDS link (IdLQ=1)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)

        link = ServiceLink(
            idlq=1,  # RDS
            lsn=100,
            hard_link=False,
            ils=False,
            rds_pi_code=0xC454
        )
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.complete_fig_transmitted is True
        assert status.num_bytes_written == 9  # 2 header + 7 data

        # Verify IdLQ
        idlq = (buf[4] >> 6) & 0x03
        assert idlq == 1

        # Verify hard/soft (should be 1 for soft)
        hard = (buf[5] >> 1) & 0x01
        assert hard == 1  # 1 = soft link

        # Verify RDS target
        # Byte 6: Type (0 = RDS)
        assert buf[6] == 0x00

        # Bytes 7-8: PI code
        pi_code = struct.unpack('>H', buf[7:9])[0]
        assert pi_code == 0xC454

    def test_fig0_6_fm_link(self):
        """Test FIG 0/6 encoding with FM link (IdLQ=1)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)

        link = ServiceLink(
            idlq=1,  # FM
            lsn=100,
            hard_link=False,
            ils=False,
            fm_frequency_mhz=101.5
        )
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify FM target
        # Byte 6: Type (1 = FM)
        assert buf[6] == 0x01

        # Bytes 7-8: Frequency encoding: (MHz - 87.5) * 200
        fm_freq = struct.unpack('>H', buf[7:9])[0]
        expected = int((101.5 - 87.5) * 200)
        assert fm_freq == expected

    def test_fig0_6_drm_link(self):
        """Test FIG 0/6 encoding with DRM link (IdLQ=2)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)

        link = ServiceLink(
            idlq=2,  # DRM
            lsn=100,
            hard_link=False,
            ils=False,
            drm_service_id=0x12345678
        )
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify status
        assert status.num_bytes_written == 10  # 2 header + 8 data

        # Verify IdLQ
        idlq = (buf[4] >> 6) & 0x03
        assert idlq == 2

        # Verify DRM target (32-bit SId)
        drm_sid = struct.unpack('>I', buf[6:10])[0]
        assert drm_sid == 0x12345678

    def test_fig0_6_amss_link(self):
        """Test FIG 0/6 encoding with AMSS link (IdLQ=3)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)

        link = ServiceLink(
            idlq=3,  # AMSS
            lsn=100,
            hard_link=False,
            ils=False,
            drm_service_id=0x87654321  # Reuse field
        )
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Verify IdLQ
        idlq = (buf[4] >> 6) & 0x03
        assert idlq == 3

        # Verify AMSS target (32-bit SId)
        amss_sid = struct.unpack('>I', buf[6:10])[0]
        assert amss_sid == 0x87654321

    def test_fig0_6_lsn_field(self):
        """Test FIG 0/6 LSN field (12 bits)."""
        # Test various LSN values
        for lsn in [0, 100, 2048, 4095]:
            ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
            service = DabService(uid='test_svc', id=0x5001)

            linkage = ServiceLinkage(enabled=True)
            link = ServiceLink(
                idlq=0,
                lsn=lsn,
                target_ecc=0xE1,
                target_ensemble_id=0x1000,
                target_service_id=0x5001
            )
            linkage.links.append(link)
            service.linkage = linkage
            ensemble.services.append(service)

            fig = FIG0_6(ensemble)
            buf = bytearray(32)
            fig.fill(buf, 32)

            # Verify LSN (12 bits split across bytes 4 and 5)
            lsn_high = buf[4] & 0x3F
            lsn_low = (buf[5] >> 2) & 0x3F
            decoded_lsn = (lsn_high << 6) | lsn_low
            assert decoded_lsn == lsn

    def test_fig0_6_hard_vs_soft_link(self):
        """Test FIG 0/6 hard vs soft linking flag."""
        # Test hard link
        ensemble1 = DabEnsemble(id=0xCE15, ecc=0xE1)
        service1 = DabService(uid='test_svc', id=0x5001)

        linkage1 = ServiceLinkage(enabled=True)
        link1 = ServiceLink(
            idlq=0,
            lsn=100,
            hard_link=True,  # Hard link
            target_ecc=0xE1,
            target_ensemble_id=0x1000,
            target_service_id=0x5001
        )
        linkage1.links.append(link1)
        service1.linkage = linkage1
        ensemble1.services.append(service1)

        fig1 = FIG0_6(ensemble1)
        buf1 = bytearray(32)
        fig1.fill(buf1, 32)

        hard1 = (buf1[5] >> 1) & 0x01
        assert hard1 == 0  # 0 = hard link

        # Test soft link
        ensemble2 = DabEnsemble(id=0xCE15, ecc=0xE1)
        service2 = DabService(uid='test_svc', id=0x5001)

        linkage2 = ServiceLinkage(enabled=True)
        link2 = ServiceLink(
            idlq=0,
            lsn=100,
            hard_link=False,  # Soft link
            target_ecc=0xE1,
            target_ensemble_id=0x1000,
            target_service_id=0x5001
        )
        linkage2.links.append(link2)
        service2.linkage = linkage2
        ensemble2.services.append(service2)

        fig2 = FIG0_6(ensemble2)
        buf2 = bytearray(32)
        fig2.fill(buf2, 32)

        hard2 = (buf2[5] >> 1) & 0x01
        assert hard2 == 1  # 1 = soft link

    def test_fig0_6_ils_flag(self):
        """Test FIG 0/6 ILS (International Linkage Set) flag."""
        # Test ILS flag values
        for ils_value in [False, True]:
            ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
            service = DabService(uid='test_svc', id=0x5001)

            linkage = ServiceLinkage(enabled=True)
            link = ServiceLink(
                idlq=0,
                lsn=100,
                ils=ils_value,
                target_ecc=0xE1,
                target_ensemble_id=0x1000,
                target_service_id=0x5001
            )
            linkage.links.append(link)
            service.linkage = linkage
            ensemble.services.append(service)

            fig = FIG0_6(ensemble)
            buf = bytearray(32)
            fig.fill(buf, 32)

            ils = buf[5] & 0x01
            assert ils == (1 if ils_value else 0)

    def test_fig0_6_32bit_service_id(self):
        """Test FIG 0/6 with 32-bit service ID in DAB link."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)

        link = ServiceLink(
            idlq=0,
            lsn=100,
            target_ecc=0xE1,
            target_ensemble_id=0x4FFF,
            target_service_id=0x12345678  # 32-bit
        )
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should write more bytes (4 for SId instead of 2)
        assert status.num_bytes_written == 13  # 2 header + 11 data

        # Verify 32-bit service ID
        target_svc = struct.unpack('>I', buf[9:13])[0]
        assert target_svc == 0x12345678

    def test_fig0_6_multiple_links(self):
        """Test FIG 0/6 with multiple links per service."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)

        # Add two links
        for lsn in [100, 200]:
            link = ServiceLink(
                idlq=0,
                lsn=lsn,
                target_ecc=0xE1,
                target_ensemble_id=0x1000,
                target_service_id=0x6001
            )
            linkage.links.append(link)

        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)

        # First call - should transmit first link (limit buffer to force split)
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 13)  # Small buffer, only fits one link
        assert status1.num_bytes_written > 0
        assert status1.complete_fig_transmitted is False

        lsn1_high = buf1[4] & 0x3F
        lsn1_low = (buf1[5] >> 2) & 0x3F
        lsn1 = (lsn1_high << 6) | lsn1_low

        # Second call - should transmit second link
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)
        assert status2.num_bytes_written > 0
        assert status2.complete_fig_transmitted is True

        lsn2_high = buf2[4] & 0x3F
        lsn2_low = (buf2[5] >> 2) & 0x3F
        lsn2 = (lsn2_high << 6) | lsn2_low

        # Verify different LSNs
        assert {lsn1, lsn2} == {100, 200}

    def test_fig0_6_iterative_transmission_services(self):
        """Test FIG 0/6 iterative transmission across services."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        # Add multiple services with linkage
        for svc_id in [0x5001, 0x5002]:
            service = DabService(uid=f'svc_{svc_id}', id=svc_id)
            linkage = ServiceLinkage(enabled=True)
            link = ServiceLink(
                idlq=0,
                lsn=100,
                target_ecc=0xE1,
                target_ensemble_id=0x1000,
                target_service_id=0x6001
            )
            linkage.links.append(link)
            service.linkage = linkage
            ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        transmitted_services = []

        # Transmit iteratively (limit buffer to force one service per call)
        for _ in range(2):
            buf = bytearray(32)
            status = fig.fill(buf, 13)  # Small buffer, only one service at a time
            if status.num_bytes_written > 0:
                # Extract service ID
                svc_id = struct.unpack('>H', buf[2:4])[0]
                transmitted_services.append(svc_id)

        # Should have transmitted both services
        assert set(transmitted_services) == {0x5001, 0x5002}

    def test_fig0_6_insufficient_space(self):
        """Test FIG 0/6 with insufficient buffer space."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=True)
        link = ServiceLink(
            idlq=0,
            lsn=100,
            target_ecc=0xE1,
            target_ensemble_id=0x1000,
            target_service_id=0x6001
        )
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 5)  # Only 5 bytes, need 11

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_6_no_linkage(self):
        """Test FIG 0/6 with no linkage (skip behavior)."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)
        service = DabService(uid='test_svc', id=0x5001)
        # No linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should not write anything
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_fig0_6_linkage_disabled(self):
        """Test FIG 0/6 with linkage disabled."""
        ensemble = DabEnsemble(id=0xCE15, ecc=0xE1)

        service = DabService(uid='test_svc', id=0x5001)
        linkage = ServiceLinkage(enabled=False)  # Disabled
        link = ServiceLink(idlq=0, lsn=100)
        linkage.links.append(link)
        service.linkage = linkage
        ensemble.services.append(service)

        fig = FIG0_6(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should not write anything (linkage disabled)
        assert status.num_bytes_written == 0

    def test_fig0_6_repetition_rate(self):
        """Test that FIG 0/6 has correct repetition rate."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_6(ensemble)

        from dabmux.fig.base import FIGRate
        assert fig.repetition_rate() == FIGRate.C

    def test_fig0_6_priority(self):
        """Test that FIG 0/6 has correct priority."""
        ensemble = DabEnsemble(id=0xCE15)
        fig = FIG0_6(ensemble)

        from dabmux.fig.base import FIGPriority
        assert fig.priority() == FIGPriority.HIGH
