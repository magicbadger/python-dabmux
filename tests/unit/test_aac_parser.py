"""
Unit tests for AAC/ADTS frame parsing.

These tests verify AAC audio frame header parsing and validation
for DAB+ transmission (HE-AAC v2).
"""
import pytest
from dabmux.audio.aac_parser import AACFrameParser, AACHeader


def create_adts_header(sample_rate: int, channels: int, frame_length: int,
                       profile: int = 1, protection: bool = False) -> bytes:
    """
    Create a valid ADTS header.

    Args:
        sample_rate: Sample rate in Hz (48000, 32000, etc.)
        channels: Number of channels (1=mono, 2=stereo)
        frame_length: Total frame size in bytes (including header)
        profile: AAC profile (0=Main, 1=LC, 2=SSR)
        protection: Whether CRC protection is present

    Returns:
        7-byte ADTS header
    """
    # Sample rate index lookup
    SAMPLE_RATES = [96000, 88200, 64000, 48000, 44100, 32000, 24000,
                    22050, 16000, 12000, 11025, 8000, 7350]
    sr_idx = SAMPLE_RATES.index(sample_rate)

    # Build header
    header = bytearray(7)

    # Byte 0: Sync word high (0xFF)
    header[0] = 0xFF

    # Byte 1: Sync low (4 bits) + MPEG-4 + Layer + Protection
    header[1] = 0xF0 | (0 << 3) | (0 << 2) | (0 if protection else 1)

    # Byte 2: Profile + SR index + Private + Channel high
    header[2] = (profile << 6) | (sr_idx << 2) | 0 | ((channels >> 2) & 0x01)

    # Byte 3: Channel low + Frame length high
    header[3] = ((channels & 0x03) << 6) | ((frame_length >> 11) & 0x03)

    # Byte 4: Frame length middle
    header[4] = (frame_length >> 3) & 0xFF

    # Byte 5: Frame length low + Buffer fullness high
    header[5] = ((frame_length & 0x07) << 5) | 0x1F

    # Byte 6: Buffer fullness low + Number of frames
    header[6] = 0xFC

    return bytes(header)


class TestAACHeader:
    """Test AAC header parsing and validation."""

    def test_create_header(self) -> None:
        """Test creating AAC header."""
        header = AACHeader(
            profile=1,  # AAC-LC
            sample_rate=48000,
            channels=2,
            frame_length=256,
            protection=False
        )
        assert header.profile == 1
        assert header.sample_rate == 48000
        assert header.channels == 2
        assert header.frame_length == 256
        assert header.protection is False

    def test_is_he_aac_v2(self) -> None:
        """Test HE-AAC v2 detection (AAC-LC + stereo)."""
        # HE-AAC v2: AAC-LC profile with stereo
        header = AACHeader(
            profile=1,  # AAC-LC
            sample_rate=48000,
            channels=2,  # Stereo
            frame_length=256,
            protection=False
        )
        assert header.is_he_aac_v2() is True

    def test_is_he_aac_v2_mono(self) -> None:
        """Test HE-AAC v2 detection with mono (should be False)."""
        # Mono is HE-AAC v1, not v2
        header = AACHeader(
            profile=1,
            sample_rate=48000,
            channels=1,  # Mono
            frame_length=256,
            protection=False
        )
        assert header.is_he_aac_v2() is False

    def test_is_he_aac_v2_wrong_profile(self) -> None:
        """Test HE-AAC v2 detection with wrong profile."""
        # AAC-Main (profile 0) is not HE-AAC
        header = AACHeader(
            profile=0,  # AAC-Main
            sample_rate=48000,
            channels=2,
            frame_length=256,
            protection=False
        )
        assert header.is_he_aac_v2() is False

    def test_is_dab_compatible_48khz(self) -> None:
        """Test DAB+ compatibility with 48 kHz."""
        header = AACHeader(
            profile=1,  # AAC-LC
            sample_rate=48000,
            channels=2,
            frame_length=256,
            protection=False
        )
        assert header.is_dab_compatible() is True

    def test_is_dab_compatible_32khz(self) -> None:
        """Test DAB+ compatibility with 32 kHz."""
        header = AACHeader(
            profile=1,
            sample_rate=32000,
            channels=2,
            frame_length=256,
            protection=False
        )
        assert header.is_dab_compatible() is True

    def test_is_dab_compatible_24khz(self) -> None:
        """Test DAB+ compatibility with 24 kHz."""
        header = AACHeader(
            profile=1,
            sample_rate=24000,
            channels=1,
            frame_length=128,
            protection=False
        )
        assert header.is_dab_compatible() is True

    def test_is_dab_compatible_16khz(self) -> None:
        """Test DAB+ compatibility with 16 kHz."""
        header = AACHeader(
            profile=1,
            sample_rate=16000,
            channels=1,
            frame_length=128,
            protection=False
        )
        assert header.is_dab_compatible() is True

    def test_is_not_dab_compatible_wrong_rate(self) -> None:
        """Test DAB+ incompatibility with wrong sample rate."""
        # 44.1 kHz is not valid for DAB+
        header = AACHeader(
            profile=1,
            sample_rate=44100,
            channels=2,
            frame_length=256,
            protection=False
        )
        assert header.is_dab_compatible() is False

    def test_is_not_dab_compatible_wrong_profile(self) -> None:
        """Test DAB+ incompatibility with wrong profile."""
        # AAC-SSR (profile 2) is not used for DAB+
        header = AACHeader(
            profile=2,  # SSR
            sample_rate=48000,
            channels=2,
            frame_length=256,
            protection=False
        )
        assert header.is_dab_compatible() is False


class TestAACFrameParser:
    """Test AAC frame parser."""

    def test_create_parser(self) -> None:
        """Test creating parser."""
        parser = AACFrameParser()
        assert parser.SAMPLE_RATES is not None
        assert len(parser.SAMPLE_RATES) == 13

    def test_sample_rates_table(self) -> None:
        """Test sample rates table completeness."""
        parser = AACFrameParser()
        # Verify common DAB+ rates are present
        assert 48000 in parser.SAMPLE_RATES
        assert 32000 in parser.SAMPLE_RATES
        assert 24000 in parser.SAMPLE_RATES
        assert 16000 in parser.SAMPLE_RATES

    def test_find_sync(self) -> None:
        """Test finding ADTS sync word (0xFFF)."""
        parser = AACFrameParser()

        # Data with sync at position 0
        header = create_adts_header(48000, 2, 256)
        data = header + b'\x00' * 100
        offset = parser.find_sync(data)

        assert offset == 0

    def test_find_sync_with_offset(self) -> None:
        """Test finding sync word with offset."""
        parser = AACFrameParser()

        # Data with sync at position 10
        header = create_adts_header(48000, 2, 256)
        data = b'\x00' * 10 + header + b'\x00' * 100
        offset = parser.find_sync(data)

        assert offset == 10

    def test_find_sync_not_found(self) -> None:
        """Test sync not found."""
        parser = AACFrameParser()

        data = b'\x00' * 100
        offset = parser.find_sync(data)

        assert offset is None

    def test_find_sync_false_positive(self) -> None:
        """Test rejecting false sync (0xFF but not 0xFFF)."""
        parser = AACFrameParser()

        # 0xFF followed by 0x0X (not 0xFX)
        data = b'\xff\x01\x02\x03' + b'\x00' * 100
        offset = parser.find_sync(data)

        assert offset is None

    def test_parse_header_48khz_stereo(self) -> None:
        """Test parsing valid ADTS header (48 kHz stereo)."""
        parser = AACFrameParser()

        header_bytes = create_adts_header(48000, 2, 256)

        header = parser.parse_header(header_bytes)

        assert header is not None
        assert header.profile == 1  # AAC-LC
        assert header.sample_rate == 48000
        assert header.channels == 2
        assert header.frame_length == 256
        assert header.protection is False

    def test_parse_header_32khz_mono(self) -> None:
        """Test parsing ADTS header (32 kHz mono)."""
        parser = AACFrameParser()

        header_bytes = create_adts_header(32000, 1, 128)

        header = parser.parse_header(header_bytes)

        assert header is not None
        assert header.profile == 1
        assert header.sample_rate == 32000
        assert header.channels == 1
        assert header.frame_length == 128

    def test_parse_header_with_crc(self) -> None:
        """Test parsing ADTS header with CRC protection."""
        parser = AACFrameParser()

        header_bytes = create_adts_header(48000, 2, 256, protection=True)

        header = parser.parse_header(header_bytes)

        assert header is not None
        assert header.protection is True

    def test_parse_header_short_data(self) -> None:
        """Test parsing with insufficient data."""
        parser = AACFrameParser()

        # Only 5 bytes (need 7)
        header_bytes = b'\xff\xf1\x50\x80\x01'

        header = parser.parse_header(header_bytes)

        assert header is None

    def test_parse_header_invalid_sync(self) -> None:
        """Test parsing with invalid sync word."""
        parser = AACFrameParser()

        # Wrong sync (0xFEF instead of 0xFFF)
        header_bytes = b'\xfe\xf1\x50\x80\x01\x3f\xfc'

        header = parser.parse_header(header_bytes)

        assert header is None

    def test_parse_header_invalid_sample_rate_index(self) -> None:
        """Test parsing with invalid sample rate index."""
        parser = AACFrameParser()

        # Sample rate index 15 is invalid (manually encoded)
        # Create invalid header with sr_idx = 15 (0xF)
        header_bytes = bytearray(7)
        header_bytes[0] = 0xFF  # Sync
        header_bytes[1] = 0xF1  # Sync + MPEG-4 + no CRC
        header_bytes[2] = (1 << 6) | (15 << 2) | 0  # Profile=1, SR_idx=15 (invalid)
        header_bytes[3] = 0x80  # Channels=2, length high
        header_bytes[4] = 0x20  # Length middle
        header_bytes[5] = 0x1F  # Length low + buffer
        header_bytes[6] = 0xFC  # Buffer + frames

        header = parser.parse_header(bytes(header_bytes))

        assert header is None

    def test_read_frame_complete(self) -> None:
        """Test reading complete AAC frame."""
        parser = AACFrameParser()

        # Create valid AAC frame (256 bytes total)
        header_bytes = create_adts_header(48000, 2, 256)
        frame_data = header_bytes + b'\x00' * (256 - 7)  # Total 256 bytes

        result = parser.read_frame(frame_data + b'\xff\xf0')  # Add start of next sync

        assert result is not None
        header, data = result
        assert len(data) == 256
        assert header.sample_rate == 48000
        assert header.channels == 2

    def test_read_frame_incomplete(self) -> None:
        """Test reading with incomplete frame."""
        parser = AACFrameParser()

        # Header says 256 bytes but only provide 100
        header_bytes = create_adts_header(48000, 2, 256)
        data = header_bytes + b'\x00' * (100 - 7)  # Total 100 bytes

        result = parser.read_frame(data)

        assert result is None

    def test_read_frame_no_sync(self) -> None:
        """Test reading with no sync word."""
        parser = AACFrameParser()

        data = b'\x00' * 1000

        result = parser.read_frame(data)

        assert result is None

    def test_read_frame_multiple(self) -> None:
        """Test reading multiple frames from buffer."""
        parser = AACFrameParser()

        # Create two complete frames
        header_bytes = create_adts_header(48000, 2, 256)
        frame1 = header_bytes + b'\xaa' * (256 - 7)
        frame2 = header_bytes + b'\xbb' * (256 - 7)

        data = frame1 + frame2

        # Read first frame
        result1 = parser.read_frame(data)
        assert result1 is not None
        header1, data1 = result1
        assert len(data1) == 256
        assert data1[7] == 0xaa

        # Read second frame
        result2 = parser.read_frame(data[256:])
        assert result2 is not None
        header2, data2 = result2
        assert len(data2) == 256
        assert data2[7] == 0xbb

    def test_validate_for_dab_plus_valid_48kbps(self) -> None:
        """Test validation for valid 48 kbps DAB+ file."""
        parser = AACFrameParser()

        # Create valid frame: 48 kHz, stereo, ~48 kbps
        # Frame rate = 48000 / 1024 = 46.875 fps
        # Frame size = 48000 / 8 / 46.875 = ~128 bytes
        frame_size = 128
        header_bytes = create_adts_header(48000, 2, frame_size)
        frame_data = header_bytes + b'\x00' * (frame_size - 7)

        valid, error = parser.validate_for_dab_plus(frame_data, 48)

        assert valid is True
        assert error == ""

    def test_validate_for_dab_plus_valid_32kbps(self) -> None:
        """Test validation for valid 32 kbps DAB+ file."""
        parser = AACFrameParser()

        # 32 kbps at 48 kHz: ~85 bytes per frame
        frame_size = 85
        header_bytes = create_adts_header(48000, 2, frame_size)
        frame_data = header_bytes + b'\x00' * (frame_size - 7)

        valid, error = parser.validate_for_dab_plus(frame_data, 32)

        assert valid is True

    def test_validate_for_dab_plus_no_frame(self) -> None:
        """Test validation with no valid frame."""
        parser = AACFrameParser()

        data = b'\x00' * 1000

        valid, error = parser.validate_for_dab_plus(data, 48)

        assert valid is False
        assert "No valid AAC frame found" in error

    def test_validate_for_dab_plus_wrong_sample_rate(self) -> None:
        """Test validation with incompatible sample rate."""
        parser = AACFrameParser()

        # 44.1 kHz is not valid for DAB+
        frame_size = 128
        header_bytes = create_adts_header(44100, 2, frame_size)
        frame_data = header_bytes + b'\x00' * (frame_size - 7)

        valid, error = parser.validate_for_dab_plus(frame_data, 48)

        assert valid is False
        assert "Incompatible format" in error
        assert "44100" in error

    def test_validate_for_dab_plus_wrong_profile(self) -> None:
        """Test validation with incompatible profile."""
        parser = AACFrameParser()

        # Profile 0 (AAC-Main) instead of 1 (AAC-LC)
        frame_size = 256
        header_bytes = create_adts_header(48000, 2, frame_size, profile=0)
        frame_data = header_bytes + b'\x00' * (frame_size - 7)

        valid, error = parser.validate_for_dab_plus(frame_data, 48)

        assert valid is False
        assert "Incompatible format" in error
        assert "profile 0" in error

    def test_validate_for_dab_plus_bitrate_mismatch(self) -> None:
        """Test validation with mismatched bitrate."""
        parser = AACFrameParser()

        # Create 48 kbps frame but claim it's 96 kbps
        frame_size = 128  # ~48 kbps at 48 kHz
        header_bytes = create_adts_header(48000, 2, frame_size)
        frame_data = header_bytes + b'\x00' * (frame_size - 7)

        valid, error = parser.validate_for_dab_plus(frame_data, 96)

        assert valid is False
        assert "Bitrate mismatch" in error
        assert "96" in error

    def test_validate_for_dab_plus_bitrate_tolerance(self) -> None:
        """Test validation with bitrate within 10% tolerance."""
        parser = AACFrameParser()

        # Create ~50 kbps frame, claim 48 kbps (within 10%)
        # 50 kbps at 48 kHz ≈ 133 bytes per frame
        frame_size = 133
        header_bytes = create_adts_header(48000, 2, frame_size)
        frame_data = header_bytes + b'\x00' * (frame_size - 7)

        valid, error = parser.validate_for_dab_plus(frame_data, 48)

        # Should be valid (within tolerance)
        assert valid is True


class TestAACFrameIntegration:
    """Integration tests for AAC frame parsing."""

    def test_parse_continuous_frames(self) -> None:
        """Test parsing continuous AAC frames."""
        parser = AACFrameParser()

        # Create 10 continuous frames
        frame_size = 256
        header_bytes = create_adts_header(48000, 2, frame_size)
        single_frame = header_bytes + b'\x00' * (frame_size - 7)
        data = single_frame * 10

        frames_parsed = 0
        offset = 0

        while offset < len(data):
            result = parser.read_frame(data[offset:])
            if result is None:
                break

            header, frame_data = result
            assert len(frame_data) == frame_size
            assert header.sample_rate == 48000

            offset += len(frame_data)
            frames_parsed += 1

        assert frames_parsed == 10

    def test_parse_with_garbage_data(self) -> None:
        """Test parsing with garbage data before valid frame."""
        parser = AACFrameParser()

        # Garbage + valid frame
        garbage = b'\x12\x34\x56\x78\x9a\xbc\xde\xf0' * 10
        frame_size = 256
        header_bytes = create_adts_header(48000, 2, frame_size)
        valid_frame = header_bytes + b'\x00' * (frame_size - 7)

        data = garbage + valid_frame

        result = parser.read_frame(data)

        assert result is not None
        header, frame_data = result
        assert len(frame_data) == frame_size

    def test_frame_consistency(self) -> None:
        """Test that parsed frames maintain consistency."""
        parser = AACFrameParser()

        # Create frames with different patterns
        frame_size = 256
        header_bytes = create_adts_header(48000, 2, frame_size)

        for pattern in [0xaa, 0xbb, 0xcc]:
            frame = header_bytes + bytes([pattern] * (frame_size - 7))
            result = parser.read_frame(frame + b'\xff\xf0')

            assert result is not None
            header, data = result
            assert data[7] == pattern  # Check pattern is preserved

    def test_different_bitrates(self) -> None:
        """Test parsing frames with different bitrates."""
        parser = AACFrameParser()

        # Test common DAB+ bitrates: 32, 48, 64, 80 kbps
        # Frame sizes at 48 kHz (sample_rate / 1024 = 46.875 fps)
        bitrates_and_sizes = [
            (32, 85),   # 32 kbps ≈ 85 bytes
            (48, 128),  # 48 kbps ≈ 128 bytes
            (64, 170),  # 64 kbps ≈ 170 bytes
            (80, 213),  # 80 kbps ≈ 213 bytes
        ]

        for bitrate, frame_size in bitrates_and_sizes:
            # Encode frame length in ADTS header
            # Frame length is 13 bits in bytes 3-5
            fl_high = (frame_size >> 11) & 0x03
            fl_mid = (frame_size >> 3) & 0xFF
            fl_low = (frame_size & 0x07) << 5

            header = bytes([
                0xff, 0xf1, 0x50, 0x80 | fl_high, fl_mid, fl_low | 0x1f, 0xfc
            ])

            frame = header + b'\x00' * (frame_size - 7)
            result = parser.read_frame(frame + b'\xff\xf1')

            assert result is not None
            parsed_header, data = result
            assert len(data) == frame_size
            assert parsed_header.frame_length == frame_size
