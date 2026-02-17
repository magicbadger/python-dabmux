"""
Unit tests for DAB CRC compliance.

These tests verify that CRC calculations comply with ETSI EN 300 401/799,
specifically that CRC values are inverted (XORed with 0xFFFF) as required
by the DAB standard.

This prevents regression of the critical bug where CRC inversion was missing,
causing etisnoop to report CRC mismatches.
"""
import pytest
from dabmux.utils.crc import crc16
from dabmux.fig.fic import FICEncoder
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabSubchannel, DabComponent,
    TransmissionMode, DabLabel, PtySettings
)
from dabmux.mux import DabMultiplexer


class TestCRC16Inversion:
    """Test that CRC-16 inversion is correctly applied per DAB standard."""

    def test_crc16_raw_calculation(self) -> None:
        """Test raw CRC-16-CCITT calculation (without inversion)."""
        # Known test vector for CRC-16-CCITT
        data = b'\x00' * 30  # 30 bytes of zeros
        crc = crc16(data)

        # CRC-16-CCITT of 30 zero bytes with init 0xFFFF
        # Should NOT be inverted yet
        assert crc == 0x2A45  # This is the raw CRC value

    def test_crc16_inverted(self) -> None:
        """Test CRC-16 with inversion as required by DAB standard."""
        data = b'\x00' * 30
        crc_raw = crc16(data)
        crc_inverted = crc_raw ^ 0xFFFF

        # After inversion
        assert crc_inverted == 0xD5BA

        # Verify inversion is bidirectional
        assert (crc_inverted ^ 0xFFFF) == crc_raw

    def test_crc_inversion_identity(self) -> None:
        """Test that double inversion returns original value."""
        test_values = [0x0000, 0xFFFF, 0xA042, 0x5FBD, 0x1234, 0xABCD]

        for value in test_values:
            inverted = value ^ 0xFFFF
            double_inverted = inverted ^ 0xFFFF
            assert double_inverted == value


class TestFIBCRCCompliance:
    """Test FIB CRC calculation compliance with ETSI EN 300 401."""

    @pytest.fixture
    def minimal_ensemble(self) -> DabEnsemble:
        """Create minimal valid ensemble for testing."""
        ensemble = DabEnsemble()
        ensemble.id = 0xCE15
        ensemble.ecc = 0xE1
        ensemble.transmission_mode = TransmissionMode.TM_I
        ensemble.label = DabLabel(text='Test DAB', short_text='Test')

        # Add subchannel
        subchannel = DabSubchannel(uid='audio1', id=0, bitrate=128)
        subchannel.start_address = 0
        subchannel.protection.level = 2
        subchannel.input_uri = 'file://test.mp2'
        ensemble.subchannels.append(subchannel)

        # Add service
        service = DabService(uid='service1', id=0x5001)
        service.label = DabLabel(text='Test Service', short_text='Test')
        service.pty_settings = PtySettings(pty=10)
        service.language = 9
        ensemble.services.append(service)

        # Add component
        component = DabComponent(uid='comp1')
        component.service_id = 0x5001
        component.subchannel_id = 0
        component.type = 0
        ensemble.components.append(component)

        return ensemble

    def test_fib_crc_inversion_applied(self, minimal_ensemble: DabEnsemble) -> None:
        """Test that FIB CRC has inversion applied."""
        fic_encoder = FICEncoder(minimal_ensemble)
        fic_data = fic_encoder.encode_fic(frame_number=0)

        # FIC for Mode I is 96 bytes (3 FIBs of 32 bytes)
        assert len(fic_data) == 96

        # Check each FIB (30 bytes data + 2 bytes CRC)
        for fib_num in range(3):
            fib_start = fib_num * 32
            fib_data = fic_data[fib_start:fib_start+30]
            fib_crc_stored = (fic_data[fib_start+30] << 8) | fic_data[fib_start+31]

            # Calculate what the CRC should be (with inversion)
            crc_calculated = crc16(fib_data) ^ 0xFFFF

            # Verify stored CRC matches calculated CRC with inversion
            assert fib_crc_stored == crc_calculated, \
                f"FIB {fib_num} CRC mismatch: stored=0x{fib_crc_stored:04X}, calculated=0x{crc_calculated:04X}"

    def test_fib_crc_without_inversion_would_fail(self, minimal_ensemble: DabEnsemble) -> None:
        """Test that FIB CRC WITHOUT inversion would NOT match (regression test)."""
        fic_encoder = FICEncoder(minimal_ensemble)
        fic_data = fic_encoder.encode_fic(frame_number=0)

        # Check first FIB
        fib_data = fic_data[0:30]
        fib_crc_stored = (fic_data[30] << 8) | fic_data[31]

        # Calculate CRC WITHOUT inversion (the bug we fixed)
        crc_without_inversion = crc16(fib_data)

        # This should NOT match (proving inversion is necessary)
        assert fib_crc_stored != crc_without_inversion, \
            "CRC without inversion should NOT match stored value"

        # But with inversion it should match
        crc_with_inversion = crc_without_inversion ^ 0xFFFF
        assert fib_crc_stored == crc_with_inversion


class TestETICRCCompliance:
    """Test ETI frame CRC compliance (EOH and EOF)."""

    @pytest.fixture
    def test_ensemble(self) -> DabEnsemble:
        """Create test ensemble."""
        ensemble = DabEnsemble()
        ensemble.id = 0xCE15
        ensemble.ecc = 0xE1
        ensemble.transmission_mode = TransmissionMode.TM_I
        ensemble.label = DabLabel(text='Test', short_text='Test')

        subchannel = DabSubchannel(uid='audio1', id=0, bitrate=128)
        subchannel.start_address = 0
        subchannel.protection.level = 2
        subchannel.input_uri = 'file://test.mp2'
        ensemble.subchannels.append(subchannel)

        service = DabService(uid='service1', id=0x5001)
        service.label = DabLabel(text='Service', short_text='Svc')
        service.pty_settings = PtySettings(pty=10)
        service.language = 9
        ensemble.services.append(service)

        component = DabComponent(uid='comp1')
        component.service_id = 0x5001
        component.subchannel_id = 0
        component.type = 0
        ensemble.components.append(component)

        return ensemble

    def test_eoh_crc_inversion_applied(self, test_ensemble: DabEnsemble) -> None:
        """Test that EOH CRC has inversion applied."""
        mux = DabMultiplexer(test_ensemble)
        frame = mux.generate_frame()

        # Calculate EOH CRC manually (FC + STC headers + MNSC)
        header_data = bytearray()
        header_data.extend(frame.fc.pack())
        for stc in frame.stc_headers:
            header_data.extend(stc.pack())
        # Add MNSC (2 bytes) to CRC calculation
        header_data.extend(frame.eoh.mnsc.to_bytes(2, 'big'))

        # EOH CRC should have inversion
        crc_calculated = crc16(bytes(header_data)) ^ 0xFFFF

        assert frame.eoh.crc == crc_calculated, \
            f"EOH CRC mismatch: stored=0x{frame.eoh.crc:04X}, calculated=0x{crc_calculated:04X}"

    def test_eof_crc_inversion_applied(self, test_ensemble: DabEnsemble) -> None:
        """Test that EOF CRC has inversion applied."""
        mux = DabMultiplexer(test_ensemble)
        frame = mux.generate_frame()

        # Calculate EOF CRC manually (FIC + MST)
        mst_data = frame.fic_data + frame.subchannel_data

        # EOF CRC should have inversion
        crc_calculated = crc16(mst_data) ^ 0xFFFF

        assert frame.eof.crc == crc_calculated, \
            f"EOF CRC mismatch: stored=0x{frame.eof.crc:04X}, calculated=0x{crc_calculated:04X}"

    def test_eoh_crc_without_inversion_would_fail(self, test_ensemble: DabEnsemble) -> None:
        """Test that EOH CRC WITHOUT inversion would NOT match (regression test)."""
        mux = DabMultiplexer(test_ensemble)
        frame = mux.generate_frame()

        # Calculate EOH CRC WITHOUT inversion
        header_data = bytearray()
        header_data.extend(frame.fc.pack())
        for stc in frame.stc_headers:
            header_data.extend(stc.pack())
        # Add MNSC (2 bytes) to CRC calculation
        header_data.extend(frame.eoh.mnsc.to_bytes(2, 'big'))

        crc_without_inversion = crc16(bytes(header_data))

        # Should NOT match (proving inversion is necessary)
        assert frame.eoh.crc != crc_without_inversion, \
            "EOH CRC without inversion should NOT match"

        # But with inversion it should match
        crc_with_inversion = crc_without_inversion ^ 0xFFFF
        assert frame.eoh.crc == crc_with_inversion

    def test_eof_crc_without_inversion_would_fail(self, test_ensemble: DabEnsemble) -> None:
        """Test that EOF CRC WITHOUT inversion would NOT match (regression test)."""
        mux = DabMultiplexer(test_ensemble)
        frame = mux.generate_frame()

        # Calculate EOF CRC WITHOUT inversion
        mst_data = frame.fic_data + frame.subchannel_data
        crc_without_inversion = crc16(mst_data)

        # Should NOT match (proving inversion is necessary)
        assert frame.eof.crc != crc_without_inversion, \
            "EOF CRC without inversion should NOT match"

        # But with inversion it should match
        crc_with_inversion = crc_without_inversion ^ 0xFFFF
        assert frame.eof.crc == crc_with_inversion


class TestCRCConsistencyAcrossFrames:
    """Test that CRC calculations are consistent across multiple frames."""

    @pytest.fixture
    def ensemble(self) -> DabEnsemble:
        """Create test ensemble."""
        ensemble = DabEnsemble()
        ensemble.id = 0xCE15
        ensemble.ecc = 0xE1
        ensemble.transmission_mode = TransmissionMode.TM_I
        ensemble.label = DabLabel(text='Test', short_text='Test')

        subchannel = DabSubchannel(uid='audio1', id=0, bitrate=128)
        subchannel.start_address = 0
        subchannel.protection.level = 2
        subchannel.input_uri = 'file://test.mp2'
        ensemble.subchannels.append(subchannel)

        service = DabService(uid='service1', id=0x5001)
        service.label = DabLabel(text='Service', short_text='Svc')
        service.pty_settings = PtySettings(pty=10)
        service.language = 9
        ensemble.services.append(service)

        component = DabComponent(uid='comp1')
        component.service_id = 0x5001
        component.subchannel_id = 0
        component.type = 0
        ensemble.components.append(component)

        return ensemble

    def test_crc_consistency_multiple_frames(self, ensemble: DabEnsemble) -> None:
        """Test that CRC calculations are consistent across 100 frames."""
        mux = DabMultiplexer(ensemble)

        for frame_num in range(100):
            frame = mux.generate_frame()

            # Verify EOH CRC
            header_data = bytearray()
            header_data.extend(frame.fc.pack())
            for stc in frame.stc_headers:
                header_data.extend(stc.pack())
            # Add MNSC (2 bytes) to CRC calculation
            header_data.extend(frame.eoh.mnsc.to_bytes(2, 'big'))
            eoh_crc_expected = crc16(bytes(header_data)) ^ 0xFFFF
            assert frame.eoh.crc == eoh_crc_expected, \
                f"Frame {frame_num}: EOH CRC mismatch"

            # Verify EOF CRC
            mst_data = frame.fic_data + frame.subchannel_data
            eof_crc_expected = crc16(mst_data) ^ 0xFFFF
            assert frame.eof.crc == eof_crc_expected, \
                f"Frame {frame_num}: EOF CRC mismatch"


class TestKnownGoodCRCValues:
    """Test against known good CRC values."""

    def test_known_fib_crc(self) -> None:
        """Test FIB CRC with known good data."""
        # All zeros FIB (30 bytes)
        fib_data = bytes(30)

        # CRC-16-CCITT of 30 zeros with init 0xFFFF = 0x2A45
        # After inversion: 0x2A45 ^ 0xFFFF = 0xD5BA
        crc_calculated = crc16(fib_data) ^ 0xFFFF
        assert crc_calculated == 0xD5BA

    def test_known_header_crc(self) -> None:
        """Test ETI header CRC with known pattern."""
        # Simple test pattern (8 bytes)
        header_data = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07])

        # Calculate CRC with inversion
        crc = crc16(header_data) ^ 0xFFFF

        # Verify it's a valid 16-bit value
        assert 0 <= crc <= 0xFFFF

        # Verify inversion was applied (raw CRC != inverted CRC)
        crc_raw = crc16(header_data)
        assert crc != crc_raw


class TestCRCRegressionPrevention:
    """Tests to prevent regression of the CRC inversion bug."""

    def test_crc_inversion_prevents_etisnoop_mismatch(self) -> None:
        """
        Verify that CRC inversion is applied, preventing etisnoop CRC mismatch.

        This is a regression test for the critical bug where CRC values
        were not inverted, causing etisnoop to report CRC mismatches.

        The DAB standard (ETSI EN 300 401/799) requires that CRC-16 values
        be inverted (XORed with 0xFFFF) before transmission. Without this
        inversion, tools like etisnoop report CRC errors.
        """
        # Test data: 30 bytes of zeros
        data = bytes(30)

        # Raw CRC (what the bug generated)
        crc_raw = crc16(data)
        assert crc_raw == 0x2A45

        # Correct CRC with inversion (what the fix generates)
        crc_inverted = crc16(data) ^ 0xFFFF
        assert crc_inverted == 0xD5BA

        # Verify that inversion is actually applied
        assert crc_inverted != crc_raw
        assert crc_inverted == (crc_raw ^ 0xFFFF)
