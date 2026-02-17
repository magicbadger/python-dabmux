"""
Unit tests for FIG 0/2 DAB+ encoding.

These tests verify that FIG 0/2 correctly encodes the ASCTy (Audio Service
Component Type) field to distinguish between DAB (MPEG Layer II, ASCTy=0)
and DAB+ (HE-AAC, ASCTy=63) audio services.

Reference: ETSI EN 300 401 Section 6.3.3
"""
import pytest
from dabmux.fig.fig0 import FIG0_2
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabComponent, DabSubchannel,
    SubchannelType, DabProtection, ProtectionForm
)


def parse_fig0_2_services(buf: bytearray, num_bytes: int) -> dict:
    """
    Parse FIG 0/2 data and extract service information.

    Returns dict mapping SID -> {'tmid': int, 'ascty': int, 'components': list}
    """
    services = {}
    idx = 2  # Skip FIG header

    while idx < num_bytes:
        # Check if this looks like a programme service (2-byte SID)
        # Try to read as 16-bit SID first
        if idx + 3 <= num_bytes:
            sid = (buf[idx] << 8) | buf[idx + 1]
            # Lower 4 bits of byte idx+2 contain num_components
            local_caid_nsc = buf[idx + 2]
            num_components = local_caid_nsc & 0x0F

            if num_components > 0 and num_components < 16:
                # Valid programme service
                idx += 3

                # Parse components
                components = []
                for _ in range(num_components):
                    if idx + 2 <= num_bytes:
                        tmid = (buf[idx] >> 6) & 0x3
                        ascty = buf[idx] & 0x3F
                        subch_id = (buf[idx + 1] >> 2) & 0x3F
                        ps = (buf[idx + 1] >> 1) & 0x1
                        ca = buf[idx + 1] & 0x1

                        components.append({
                            'tmid': tmid,
                            'ascty': ascty,
                            'subch_id': subch_id,
                            'ps': ps,
                            'ca': ca
                        })
                        idx += 2
                    else:
                        break

                services[sid] = {
                    'tmid': components[0]['tmid'] if components else 0,
                    'ascty': components[0]['ascty'] if components else 0,
                    'components': components
                }
            else:
                # Invalid or end of data
                break
        else:
            break

    return services


class TestFIG0_2_ASCTy:
    """Test FIG 0/2 ASCTy encoding for DAB vs DAB+."""

    def test_ascty_dab_audio(self) -> None:
        """Test ASCTy=0 for DAB (MPEG Layer II) audio."""
        ensemble = DabEnsemble()

        # Create DAB service (MPEG Layer II)
        service = DabService(uid="radio1", id=0x5001)
        ensemble.services.append(service)

        # Create subchannel with DAB audio type
        subchannel = DabSubchannel(uid="audio1", id=0, bitrate=128)
        subchannel.type = SubchannelType.DABAudio  # MPEG Layer II
        subchannel.start_address = 0
        subchannel.protection.form = ProtectionForm.UEP
        subchannel.protection.level = 2
        ensemble.subchannels.append(subchannel)

        # Create component linking service to subchannel
        component = DabComponent(uid="comp1")
        component.service_id = 0x5001
        component.subchannel_id = 0
        component.is_primary = True
        ensemble.components.append(component)

        # Generate FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(64)
        status = fig.fill(buf, 64)

        assert status.num_bytes_written > 0
        assert status.complete_fig_transmitted is True

        # Parse FIG 0/2
        services = parse_fig0_2_services(buf, status.num_bytes_written)

        assert 0x5001 in services, "Service 0x5001 not found in FIG 0/2"

        # For DAB audio: TMId=0 (MSC stream audio), ASCTy=0 (MPEG Layer II)
        assert services[0x5001]['tmid'] == 0, "Expected TMId=0 for audio"
        assert services[0x5001]['ascty'] == 0, "Expected ASCTy=0 for DAB audio"

    def test_ascty_dabplus_audio(self) -> None:
        """Test ASCTy=63 for DAB+ (HE-AAC) audio."""
        ensemble = DabEnsemble()

        # Create DAB+ service (HE-AAC)
        service = DabService(uid="radio1", id=0x5001)
        ensemble.services.append(service)

        # Create subchannel with DAB+ audio type
        subchannel = DabSubchannel(uid="audio1", id=0, bitrate=48)
        subchannel.type = SubchannelType.DABPlusAudio  # HE-AAC
        subchannel.start_address = 0
        subchannel.protection.form = ProtectionForm.UEP
        subchannel.protection.level = 2
        ensemble.subchannels.append(subchannel)

        # Create component linking service to subchannel
        component = DabComponent(uid="comp1")
        component.service_id = 0x5001
        component.subchannel_id = 0
        component.is_primary = True
        ensemble.components.append(component)

        # Generate FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(64)
        status = fig.fill(buf, 64)

        assert status.num_bytes_written > 0
        assert status.complete_fig_transmitted is True

        # Parse FIG 0/2
        services = parse_fig0_2_services(buf, status.num_bytes_written)

        assert 0x5001 in services, "Service 0x5001 not found in FIG 0/2"

        # For DAB+ audio: TMId=0 (MSC stream audio), ASCTy=63 (HE-AAC)
        assert services[0x5001]['tmid'] == 0, "Expected TMId=0 for audio"
        assert services[0x5001]['ascty'] == 63, "Expected ASCTy=63 for DAB+ audio"

    def test_ascty_mixed_services(self) -> None:
        """Test mixed DAB and DAB+ services in same ensemble."""
        ensemble = DabEnsemble()

        # DAB service (MPEG)
        service1 = DabService(uid="radio1", id=0x5001)
        ensemble.services.append(service1)

        subchannel1 = DabSubchannel(uid="audio1", id=0, bitrate=128)
        subchannel1.type = SubchannelType.DABAudio
        subchannel1.start_address = 0
        subchannel1.protection.form = ProtectionForm.UEP
        subchannel1.protection.level = 2
        ensemble.subchannels.append(subchannel1)

        component1 = DabComponent(uid="comp1")
        component1.service_id = 0x5001
        component1.subchannel_id = 0
        component1.is_primary = True
        ensemble.components.append(component1)

        # DAB+ service (HE-AAC)
        service2 = DabService(uid="radio2", id=0x5002)
        ensemble.services.append(service2)

        subchannel2 = DabSubchannel(uid="audio2", id=1, bitrate=48)
        subchannel2.type = SubchannelType.DABPlusAudio
        subchannel2.start_address = 84  # After first subchannel
        subchannel2.protection.form = ProtectionForm.UEP
        subchannel2.protection.level = 2
        ensemble.subchannels.append(subchannel2)

        component2 = DabComponent(uid="comp2")
        component2.service_id = 0x5002
        component2.subchannel_id = 1
        component2.is_primary = True
        ensemble.components.append(component2)

        # Generate FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(128)
        status = fig.fill(buf, 128)

        assert status.num_bytes_written > 0
        assert status.complete_fig_transmitted is True

        # Parse and verify both services
        services = parse_fig0_2_services(buf, status.num_bytes_written)

        # Verify both services found
        assert 0x5001 in services, "DAB service not found"
        assert 0x5002 in services, "DAB+ service not found"

        # Verify ASCTy values
        assert services[0x5001]['ascty'] == 0, "DAB service should have ASCTy=0"
        assert services[0x5002]['ascty'] == 63, "DAB+ service should have ASCTy=63"

    def test_ascty_without_subchannel_link(self) -> None:
        """Test ASCTy defaults to 0 when subchannel not found."""
        ensemble = DabEnsemble()

        # Service without matching subchannel
        service = DabService(uid="radio1", id=0x5001)
        ensemble.services.append(service)

        # Component referencing non-existent subchannel
        component = DabComponent(uid="comp1")
        component.service_id = 0x5001
        component.subchannel_id = 99  # Doesn't exist
        component.is_primary = True
        ensemble.components.append(component)

        # Generate FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(64)
        status = fig.fill(buf, 64)

        assert status.num_bytes_written > 0

        # Parse FIG 0/2
        services = parse_fig0_2_services(buf, status.num_bytes_written)

        assert 0x5001 in services, "Service 0x5001 not found"

        # Should default to ASCTy=0 (DAB)
        assert services[0x5001]['ascty'] == 0, "Should default to ASCTy=0 when subchannel not found"

    def test_ascty_data_subchannel(self) -> None:
        """Test ASCTy for data subchannels (not audio)."""
        ensemble = DabEnsemble()

        # Data service
        service = DabService(uid="data1", id=0x5001)
        ensemble.services.append(service)

        # Data subchannel (packet mode)
        subchannel = DabSubchannel(uid="data1", id=0, bitrate=64)
        subchannel.type = SubchannelType.Packet
        subchannel.start_address = 0
        subchannel.protection.form = ProtectionForm.UEP
        subchannel.protection.level = 2
        ensemble.subchannels.append(subchannel)

        # Component for data service
        component = DabComponent(uid="comp1")
        component.service_id = 0x5001
        component.subchannel_id = 0
        component.is_primary = True
        ensemble.components.append(component)

        # Generate FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(64)
        status = fig.fill(buf, 64)

        assert status.num_bytes_written > 0

        # Data services should have TMId != 0 (not MSC stream audio)
        # ASCTy is not relevant for data services
        services = parse_fig0_2_services(buf, status.num_bytes_written)

        assert 0x5001 in services, "Data service should be present"
        # For data, ASCTy field is actually DSCTy (Data Service Component Type)
        # and defaults to 0

    def test_ascty_encoding_bitfield(self) -> None:
        """Test correct bitfield encoding of ASCTy in FIG 0/2."""
        ensemble = DabEnsemble()

        # DAB+ service
        service = DabService(uid="radio1", id=0x5001)
        ensemble.services.append(service)

        subchannel = DabSubchannel(uid="audio1", id=5, bitrate=48)
        subchannel.type = SubchannelType.DABPlusAudio
        subchannel.start_address = 0
        subchannel.protection.form = ProtectionForm.UEP
        subchannel.protection.level = 2
        ensemble.subchannels.append(subchannel)

        component = DabComponent(uid="comp1")
        component.service_id = 0x5001
        component.subchannel_id = 5
        component.is_primary = True
        ensemble.components.append(component)

        # Generate FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(64)
        status = fig.fill(buf, 64)

        # Locate service
        idx = 2
        while idx < status.num_bytes_written:
            sid = (buf[idx] << 8) | buf[idx + 1]
            if sid == 0x5001:
                # Component entry bytes:
                # Byte 0 (idx+3): TMId (bits 6-7) | ASCTy (bits 0-5)
                # Byte 1 (idx+4): SubChId (bits 2-7) | PS (bit 1) | CA (bit 0)

                byte0 = buf[idx + 3]
                byte1 = buf[idx + 4]

                tmid = (byte0 >> 6) & 0x3
                ascty = byte0 & 0x3F
                subch_id = (byte1 >> 2) & 0x3F
                ps = (byte1 >> 1) & 0x1
                ca = byte1 & 0x1

                # Verify encoding
                assert tmid == 0, "TMId should be 0 for audio"
                assert ascty == 63, "ASCTy should be 63 for DAB+"
                assert subch_id == 5, "SubChId should be 5"
                assert ps == 1, "PS (Primary/Secondary) should be 1 for primary"
                assert ca == 0, "CA (Conditional Access) should be 0"

                # Verify bitfield packing
                expected_byte0 = (0 << 6) | 63  # TMId=0, ASCTy=63
                assert byte0 == expected_byte0, f"Byte 0 encoding incorrect: {byte0:#04x} != {expected_byte0:#04x}"

                expected_byte1 = (5 << 2) | (1 << 1) | 0  # SubChId=5, PS=1, CA=0
                assert byte1 == expected_byte1, f"Byte 1 encoding incorrect: {byte1:#04x} != {expected_byte1:#04x}"
                break
            else:
                num_scs = (buf[idx + 2] >> 4) & 0x0F
                idx += 3 + (num_scs * 2)
        else:
            pytest.fail("Service 0x5001 not found in FIG 0/2")


class TestFIG0_2_Regression:
    """Regression tests to ensure DAB support is preserved."""

    def test_backward_compatibility_dab(self) -> None:
        """Ensure existing DAB (MP2) configurations still work."""
        ensemble = DabEnsemble()

        # Traditional DAB configuration
        service = DabService(uid="radio1", id=0xD001)
        ensemble.services.append(service)

        subchannel = DabSubchannel(uid="audio1", id=0, bitrate=128)
        subchannel.type = SubchannelType.DABAudio
        subchannel.start_address = 0
        subchannel.protection.form = ProtectionForm.UEP
        subchannel.protection.level = 2
        ensemble.subchannels.append(subchannel)

        component = DabComponent(uid="comp1")
        component.service_id = 0xD001
        component.subchannel_id = 0
        component.is_primary = True
        ensemble.components.append(component)

        # Should generate valid FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(64)
        status = fig.fill(buf, 64)

        assert status.num_bytes_written > 0
        assert status.complete_fig_transmitted is True

        # Verify ASCTy=0
        idx = 2
        sid = (buf[idx] << 8) | buf[idx + 1]
        assert sid == 0xD001
        ascty = buf[idx + 3] & 0x3F
        assert ascty == 0

    def test_multiple_components_per_service(self) -> None:
        """Test service with multiple components (audio + data)."""
        ensemble = DabEnsemble()

        service = DabService(uid="radio1", id=0x5001)
        ensemble.services.append(service)

        # Audio component (DAB+)
        audio_sub = DabSubchannel(uid="audio1", id=0, bitrate=48)
        audio_sub.type = SubchannelType.DABPlusAudio
        audio_sub.start_address = 0
        audio_sub.protection.form = ProtectionForm.UEP
        audio_sub.protection.level = 2
        ensemble.subchannels.append(audio_sub)

        audio_comp = DabComponent(uid="comp1")
        audio_comp.service_id = 0x5001
        audio_comp.subchannel_id = 0
        audio_comp.is_primary = True
        ensemble.components.append(audio_comp)

        # Data component
        data_sub = DabSubchannel(uid="data1", id=1, bitrate=32)
        data_sub.type = SubchannelType.Packet
        data_sub.start_address = 32
        data_sub.protection.form = ProtectionForm.UEP
        data_sub.protection.level = 2
        ensemble.subchannels.append(data_sub)

        data_comp = DabComponent(uid="comp2")
        data_comp.service_id = 0x5001
        data_comp.subchannel_id = 1
        data_comp.is_primary = False
        ensemble.components.append(data_comp)

        # Generate FIG 0/2
        fig = FIG0_2(ensemble)
        buf = bytearray(128)
        status = fig.fill(buf, 128)

        assert status.num_bytes_written > 0

        # Parse and verify
        services = parse_fig0_2_services(buf, status.num_bytes_written)

        assert 0x5001 in services, "Service not found"
        assert len(services[0x5001]['components']) == 2, "Should have 2 components"

        # First component (audio, DAB+) should have ASCTy=63
        assert services[0x5001]['components'][0]['ascty'] == 63

        # Second component is data, ASCTy not applicable (field is DSCTy for data)
        # (TMId will be different)
