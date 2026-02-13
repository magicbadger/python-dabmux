"""
Unit tests for MPEG frame parsing.

These tests verify MPEG audio frame header parsing and validation.
"""
import pytest
from dabmux.audio.mpeg import MpegFrameParser, MpegHeader, MpegLayer, MpegSamplingRate


class TestMpegHeader:
    """Test MPEG header parsing and validation."""

    def test_create_header(self) -> None:
        """Test creating MPEG header."""
        header = MpegHeader()
        assert header.sync == 0
        assert header.layer == MpegLayer.LAYER_II

    def test_valid_header(self) -> None:
        """Test valid MPEG header."""
        header = MpegHeader()
        header.sync = 0x7FF
        header.version = 3  # MPEG-1
        header.layer = MpegLayer.LAYER_II
        header.bitrate_index = 8  # 128 kbps
        header.sampling_rate_index = 1  # 48000 Hz

        assert header.is_valid() is True

    def test_invalid_sync(self) -> None:
        """Test invalid sync word."""
        header = MpegHeader()
        header.sync = 0x123
        assert header.is_valid() is False

    def test_invalid_version(self) -> None:
        """Test invalid MPEG version."""
        header = MpegHeader()
        header.sync = 0x7FF
        header.version = 0  # MPEG-2.5 not supported for DAB
        assert header.is_valid() is False

    def test_invalid_layer(self) -> None:
        """Test invalid layer."""
        header = MpegHeader()
        header.sync = 0x7FF
        header.version = 3
        header.layer = MpegLayer.RESERVED
        assert header.is_valid() is False

    def test_invalid_bitrate(self) -> None:
        """Test invalid bitrate index."""
        header = MpegHeader()
        header.sync = 0x7FF
        header.version = 3
        header.layer = MpegLayer.LAYER_II
        header.bitrate_index = 0  # Free bitrate not supported
        assert header.is_valid() is False

    def test_get_bitrate_mpeg1(self) -> None:
        """Test bitrate calculation for MPEG-1."""
        header = MpegHeader()
        header.version = 3  # MPEG-1
        header.layer = MpegLayer.LAYER_II
        header.bitrate_index = 8  # 128 kbps

        assert header.get_bitrate() == 128

    def test_get_bitrate_mpeg2(self) -> None:
        """Test bitrate calculation for MPEG-2."""
        header = MpegHeader()
        header.version = 2  # MPEG-2
        header.layer = MpegLayer.LAYER_II
        header.bitrate_index = 8  # 64 kbps for MPEG-2

        assert header.get_bitrate() == 64

    def test_get_sampling_rate_mpeg1(self) -> None:
        """Test sampling rate for MPEG-1."""
        header = MpegHeader()
        header.version = 3  # MPEG-1
        header.sampling_rate_index = 1  # 48000 Hz

        assert header.get_sampling_rate() == 48000

    def test_get_sampling_rate_mpeg2(self) -> None:
        """Test sampling rate for MPEG-2."""
        header = MpegHeader()
        header.version = 2  # MPEG-2
        header.sampling_rate_index = 1  # 24000 Hz

        assert header.get_sampling_rate() == 24000

    def test_get_frame_length(self) -> None:
        """Test frame length calculation."""
        header = MpegHeader()
        header.version = 3  # MPEG-1
        header.layer = MpegLayer.LAYER_II
        header.bitrate_index = 8  # 128 kbps
        header.sampling_rate_index = 1  # 48000 Hz
        header.padding = 0

        # Frame length = 144 * 128000 / 48000 = 384 bytes
        assert header.get_frame_length() == 384

    def test_get_frame_length_with_padding(self) -> None:
        """Test frame length with padding."""
        header = MpegHeader()
        header.version = 3
        header.layer = MpegLayer.LAYER_II
        header.bitrate_index = 8  # 128 kbps
        header.sampling_rate_index = 1  # 48000 Hz
        header.padding = 1

        # Frame length = 384 + 1 = 385 bytes
        assert header.get_frame_length() == 385


class TestMpegFrameParser:
    """Test MPEG frame parser."""

    def test_create_parser(self) -> None:
        """Test creating parser."""
        parser = MpegFrameParser()
        assert parser.last_header is None

    def test_parse_valid_header(self) -> None:
        """Test parsing valid MPEG header."""
        # Valid MPEG-1 Layer II header
        # Sync: 0x7FF (11 bits)
        # Version: 11 (MPEG-1)
        # Layer: 10 (Layer II)
        # Protection: 1 (no CRC)
        # Bitrate: 1000 (128 kbps = index 8)
        # Sampling: 01 (48000 Hz = index 1)
        # Padding: 0
        # Private: 0
        # Mode: 00 (stereo)
        # Mode ext: 00
        # Copyright: 0
        # Original: 0
        # Emphasis: 00
        # Binary: 11111111 11111101 10000100 00000000
        header_bytes = b'\xff\xfd\x84\x00'

        parser = MpegFrameParser()
        header = parser.parse_header(header_bytes)

        assert header is not None
        assert header.sync == 0x7FF
        assert header.version == 3
        assert header.layer == MpegLayer.LAYER_II
        assert header.bitrate_index == 8
        assert header.sampling_rate_index == 1

    def test_parse_short_data(self) -> None:
        """Test parsing with insufficient data."""
        parser = MpegFrameParser()
        header = parser.parse_header(b'\xff\xf5')

        assert header is None

    def test_find_sync(self) -> None:
        """Test finding sync word."""
        parser = MpegFrameParser()

        # Data with sync at position 0
        data = b'\xff\xfd\x84\x00' + b'\x00' * 100
        offset = parser.find_sync(data)

        assert offset == 0

    def test_find_sync_with_offset(self) -> None:
        """Test finding sync word with offset."""
        parser = MpegFrameParser()

        # Data with sync at position 10
        data = b'\x00' * 10 + b'\xff\xfd\x84\x00' + b'\x00' * 100
        offset = parser.find_sync(data)

        assert offset == 10

    def test_find_sync_not_found(self) -> None:
        """Test sync not found."""
        parser = MpegFrameParser()

        data = b'\x00' * 100
        offset = parser.find_sync(data)

        assert offset is None

    def test_read_frame(self) -> None:
        """Test reading complete MPEG frame."""
        parser = MpegFrameParser()

        # Create valid MPEG frame
        # Header: MPEG-1 Layer II, 128 kbps, 48000 Hz
        # Frame length should be 384 bytes
        header_bytes = b'\xff\xfd\x84\x00'
        frame_data = header_bytes + b'\x00' * 380  # Total 384 bytes

        result = parser.read_frame(frame_data + b'\xff\xfd\x84\x00')  # Add next sync

        assert result is not None
        header, data = result
        assert len(data) == 384
        assert header.get_bitrate() == 128
        assert header.get_sampling_rate() == 48000

    def test_read_frame_insufficient_data(self) -> None:
        """Test reading with insufficient data."""
        parser = MpegFrameParser()

        # Header says 384 bytes but only provide 100
        header_bytes = b'\xff\xfd\x84\x00'
        data = header_bytes + b'\x00' * 96

        result = parser.read_frame(data)

        assert result is None

    def test_validate_frame(self) -> None:
        """Test frame validation."""
        parser = MpegFrameParser()

        # Valid 384-byte frame
        header_bytes = b'\xff\xfd\x84\x00'
        frame_data = header_bytes + b'\x00' * 380

        assert parser.validate_frame(frame_data) is True

    def test_validate_frame_wrong_length(self) -> None:
        """Test validation with wrong length."""
        parser = MpegFrameParser()

        # Header says 384 bytes but only provide 100
        header_bytes = b'\xff\xfd\x84\x00'
        frame_data = header_bytes + b'\x00' * 96

        assert parser.validate_frame(frame_data) is False

    def test_get_frame_info(self) -> None:
        """Test getting frame info."""
        parser = MpegFrameParser()

        # Valid frame
        header_bytes = b'\xff\xfd\x84\x00'
        frame_data = header_bytes + b'\x00' * 380

        info = parser.get_frame_info(frame_data + b'\xff\xfd\x84\x00')

        assert info is not None
        assert info['bitrate'] == 128
        assert info['sampling_rate'] == 48000
        assert info['frame_length'] == 384
        assert info['layer'] == 'LAYER_II'
        assert info['version'] == 1
        assert info['protected'] is False
        assert info['padding'] is False
