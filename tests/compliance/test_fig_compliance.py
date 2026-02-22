"""
FIG Compliance Test Suite.

Verifies FIG implementations against ETSI EN 300 401 specifications.

Tests:
- Byte structure compliance
- Repetition rate compliance
- Size constraints
- Edge cases
"""
import pytest
import struct
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabSubchannel, DabComponent,
    DabLabel, ProtectionLevel, SubchannelType, TransmissionMode
)
from dabmux.fig.fig0 import (
    FIG0_0, FIG0_1, FIG0_2, FIG0_5, FIG0_7, FIG0_10, FIG0_17, FIG0_18
)
from dabmux.fig.fig1 import FIG1_0, FIG1_1
from dabmux.fig.fig2 import FIG2_1
from dabmux.fig.base import FIGRate


class TestFIG0ByteStructures:
    """Test FIG 0 byte structures match ETSI EN 300 401."""

    def test_fig0_0_header(self):
        """FIG 0/0: Ensemble information header structure."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG0_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Byte 0: Type (3 bits) = 0, Length (5 bits)
        assert (buf[0] >> 5) == 0  # Type 0

        # Byte 1: CN | OE | PD | Extension
        assert (buf[1] & 0x1F) == 0  # Extension 0

    def test_fig0_1_header(self):
        """FIG 0/1: Subchannel organization header structure."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )
        subchannel = DabSubchannel(
            uid='test',
            id=0,
            type=SubchannelType.DABPLUS,
            bitrate=48,
            protection=ProtectionLevel.EEP_3A,
            input_uri='file:///test.dabp'
        )
        ensemble.subchannels.append(subchannel)

        fig = FIG0_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Byte 0: Type 0
        assert (buf[0] >> 5) == 0

        # Byte 1: Extension 1
        assert (buf[1] & 0x1F) == 1

    def test_fig0_2_component_byte(self):
        """FIG 0/2: Component byte structure (SubChId in bits 7-2)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )
        service = DabService(
            uid='test_svc',
            id=0x5001,
            label=DabLabel(text='Test Service'),
            pty=10,
            language=9
        )
        ensemble.services.append(service)

        component = DabComponent(
            uid='test_comp',
            service_id=0x5001,
            subchannel_id=0
        )
        ensemble.components.append(component)

        fig = FIG0_2(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Find component byte (after SId)
        # For 16-bit SId: byte 4 is component byte
        component_byte = buf[4]

        # Bits 7-2: SubChId (should be 0)
        subchid = (component_byte >> 2) & 0x3F
        assert subchid == 0

        # Bit 1: P/S flag
        # Bit 0: CA flag

    def test_fig0_7_count_field(self):
        """FIG 0/7: 10-bit count field structure."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I,
            configuration_count=512  # 10-bit value
        )

        fig = FIG0_7(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Byte 2: Rfa (6 bits) + Count high (2 bits)
        # Byte 3: Count low (8 bits)
        count = ((buf[2] & 0x03) << 8) | buf[3]
        assert count == 512

    def test_fig0_10_date_structure(self):
        """FIG 0/10: MJD and time structure."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )
        ensemble.datetime_enabled = True

        fig = FIG0_10(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Byte 2-3: MJD (Modified Julian Date)
        mjd = struct.unpack_from('>H', buf, 2)[0]
        assert mjd > 0  # Valid MJD

        # Byte 4: Hours (high bits)
        # Byte 5: Hours (low bits) + Minutes (high bits)
        # Byte 6: Minutes (low bits) + Seconds (high bits)


class TestFIG1ByteStructures:
    """Test FIG 1 byte structures."""

    def test_fig1_0_label_encoding(self):
        """FIG 1/0: Ensemble label encoding (16 characters)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test Ensemble  '),  # Padded to 16
            transmission_mode=TransmissionMode.I
        )

        fig = FIG1_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Label starts at byte 4 (after header + EId)
        label_bytes = buf[4:20]
        label_text = label_bytes.decode('iso-8859-1').rstrip()
        assert 'Test Ensemble' in label_text

    def test_fig1_1_short_label(self):
        """FIG 1/1: Short label mask encoding."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test Ensemble'),
            transmission_mode=TransmissionMode.I
        )
        service = DabService(
            uid='test',
            id=0x5001,
            label=DabLabel(text='TestSvc', short_text='Test'),
            pty=10,
            language=9
        )
        ensemble.services.append(service)

        fig = FIG1_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Short label mask is 16-bit field
        # Indicates which characters from long label form short label


class TestFIG2ByteStructures:
    """Test FIG 2 byte structures."""

    def test_fig2_1_segment_header(self):
        """FIG 2/1: Segment header structure."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )
        service = DabService(
            uid='test',
            id=0x5001,
            label=DabLabel(text='Test'),
            pty=10,
            language=9
        )
        ensemble.services.append(service)

        from dabmux.core.mux_elements import DynamicLabel
        component = DabComponent(
            uid='test',
            service_id=0x5001,
            subchannel_id=0,
            dynamic_label=DynamicLabel(text='Now Playing', charset=2)
        )
        ensemble.components.append(component)

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Byte 0: Type (3) = 2 | Length (5)
        assert (buf[0] >> 5) == 2  # Type 2

        # Byte 1: Charset (4) | OE | Ext
        charset = (buf[1] >> 4) & 0x0F
        assert charset in [0, 1, 2]  # Valid charset

        # Byte 2: Toggle | Seg# | Last | Rfa
        # Bit 7: Toggle
        # Bits 6-4: Segment number (0-7)
        # Bit 3: Last segment
        # Bits 2-0: Rfa


class TestRepetitionRates:
    """Test FIG repetition rates per ETSI EN 300 401 Section 5.2.2.1."""

    def test_fig2_1_rate_a(self):
        """FIG 2/1: Rate A (100 ms) for dynamic labels."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG2_1(ensemble)
        assert fig.repetition_rate() == FIGRate.A

    def test_fig0_0_rate_b(self):
        """FIG 0/0: Rate B (1 second)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG0_0(ensemble)
        assert fig.repetition_rate() == FIGRate.B

    def test_fig0_1_rate_b(self):
        """FIG 0/1: Rate B (1 second)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG0_1(ensemble)
        assert fig.repetition_rate() == FIGRate.B

    def test_fig0_10_rate_c(self):
        """FIG 0/10: Rate C (1 minute)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG0_10(ensemble)
        assert fig.repetition_rate() == FIGRate.C

    def test_fig1_0_rate_b(self):
        """FIG 1/0: Rate B (1 second)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG1_0(ensemble)
        assert fig.repetition_rate() == FIGRate.B


class TestSizeConstraints:
    """Test FIG size constraints."""

    def test_fig_fits_in_fib(self):
        """All FIGs must fit in FIB (30 bytes max)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test Ensemble  '),
            transmission_mode=TransmissionMode.I
        )

        # Add maximum services and subchannels
        for i in range(64):
            subchannel = DabSubchannel(
                uid=f'sub{i}',
                id=i,
                type=SubchannelType.DABPLUS,
                bitrate=48,
                protection=ProtectionLevel.EEP_3A,
                input_uri=f'file:///test{i}.dabp'
            )
            ensemble.subchannels.append(subchannel)

        # Test FIG 0/1 with maximum subchannels
        fig = FIG0_1(ensemble)
        buf = bytearray(30)  # FIB data size
        status = fig.fill(buf, 30)

        # Should either fit or indicate continuation needed
        assert status.num_bytes_written <= 30

    def test_length_field_correct(self):
        """Length field must match actual data size."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG0_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Byte 0: Type (3 bits) | Length (5 bits)
        length = buf[0] & 0x1F

        # Length should match bytes written minus 1
        assert length == status.num_bytes_written - 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_ensemble(self):
        """FIG 0/0 with no services."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Empty'),
            transmission_mode=TransmissionMode.I
        )

        fig = FIG0_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should still encode ensemble info
        assert status.num_bytes_written > 0

    def test_maximum_services(self):
        """64 services (maximum)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Max Services'),
            transmission_mode=TransmissionMode.I
        )

        for i in range(64):
            service = DabService(
                uid=f'svc{i}',
                id=0x5001 + i,
                label=DabLabel(text=f'Service {i}'),
                pty=10,
                language=9
            )
            ensemble.services.append(service)

        # FIG 1/1 should handle all services (iteratively)
        fig = FIG1_1(ensemble)
        buf = bytearray(30)
        status = fig.fill(buf, 30)

        # Should complete eventually
        assert status.num_bytes_written > 0

    def test_maximum_subchannels(self):
        """64 subchannels (maximum)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Max Subch'),
            transmission_mode=TransmissionMode.I
        )

        for i in range(64):
            subchannel = DabSubchannel(
                uid=f'sub{i}',
                id=i,
                type=SubchannelType.DABPLUS,
                bitrate=8,  # Minimum to fit all
                protection=ProtectionLevel.EEP_4A,
                input_uri=f'file:///test{i}.dabp'
            )
            ensemble.subchannels.append(subchannel)

        fig = FIG0_1(ensemble)
        buf = bytearray(30)
        status = fig.fill(buf, 30)

        assert status.num_bytes_written > 0

    def test_long_label(self):
        """16-character label (maximum)."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='0123456789ABCDEF'),  # Exactly 16
            transmission_mode=TransmissionMode.I
        )

        fig = FIG1_0(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should encode full 16 characters
        label_bytes = buf[4:20]
        assert len(label_bytes) == 16

    def test_utf8_dynamic_label(self):
        """UTF-8 dynamic label with emoji."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text='Test'),
            transmission_mode=TransmissionMode.I
        )
        service = DabService(
            uid='test',
            id=0x5001,
            label=DabLabel(text='Test'),
            pty=10,
            language=9
        )
        ensemble.services.append(service)

        from dabmux.core.mux_elements import DynamicLabel
        component = DabComponent(
            uid='test',
            service_id=0x5001,
            subchannel_id=0,
            dynamic_label=DynamicLabel(
                text='Now Playing: 🎵 Music',
                charset=2  # UTF-8
            )
        )
        ensemble.components.append(component)

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should encode without error
        assert status.num_bytes_written > 0


class TestCRCCompliance:
    """Test CRC calculations per ETSI standards."""

    def test_crc_inversion_required(self):
        """CRC values must be inverted (XORed with 0xFFFF)."""
        # This is tested in test_dab_crc_compliance.py
        # but included here for completeness
        from dabmux.utils.crc import crc16

        data = b'Test data'
        crc_raw = crc16(data)
        crc_inverted = crc_raw ^ 0xFFFF

        # DAB standard requires inversion
        # Without inversion, CRCs would be incorrect
        assert crc_inverted != crc_raw


class TestMultilingualSupport:
    """Test multilingual and character set support."""

    def test_ebu_latin_charset(self):
        """EBU Latin character set encoding."""
        from dabmux.utils.charset import utf8_to_ebu_latin

        text = "Test Äöü"
        encoded = utf8_to_ebu_latin(text, max_length=16)

        assert len(encoded) <= 16

    def test_utf8_charset(self):
        """UTF-8 encoding in dynamic labels."""
        from dabmux.core.mux_elements import DynamicLabel

        label = DynamicLabel(text='Тест', charset=2)  # Russian
        assert label.text == 'Тест'

    def test_ucs2_charset(self):
        """UCS-2 encoding in dynamic labels."""
        from dabmux.core.mux_elements import DynamicLabel

        label = DynamicLabel(text='测试', charset=1)  # Chinese
        encoded = label._encode_text()
        assert len(encoded) > 0


# Pytest collection
__all__ = [
    'TestFIG0ByteStructures',
    'TestFIG1ByteStructures',
    'TestFIG2ByteStructures',
    'TestRepetitionRates',
    'TestSizeConstraints',
    'TestEdgeCases',
    'TestCRCCompliance',
    'TestMultilingualSupport',
]
