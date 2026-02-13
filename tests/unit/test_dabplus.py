"""
Unit tests for DAB+ support.
"""
import pytest
from dabmux.audio.dabplus import (
    DabPlusProfile,
    DabPlusSuperframe,
    DabPlusConfig,
    calculate_dabplus_subchannel_size,
    create_dummy_superframe,
    parse_dabplus_bitrate,
    get_recommended_bitrate,
    DABPLUS_RECOMMENDED_BITRATES
)


class TestDabPlusSuperframe:
    """Test DAB+ superframe structure."""

    def test_create_superframe(self) -> None:
        """Test creating superframe."""
        sf = DabPlusSuperframe(num_aus=5, au_size=96, rs_enabled=True)
        assert sf.num_aus == 5
        assert sf.au_size == 96
        assert sf.rs_enabled is True

    def test_get_total_size_without_rs(self) -> None:
        """Test superframe size without RS."""
        sf = DabPlusSuperframe(num_aus=5, au_size=100, rs_enabled=False)
        assert sf.get_total_size() == 500  # 5 * 100

    def test_get_total_size_with_rs(self) -> None:
        """Test superframe size with RS."""
        sf = DabPlusSuperframe(num_aus=5, au_size=100, rs_enabled=True)
        size = sf.get_total_size()
        assert size > 500  # Larger due to RS parity


class TestDabPlusConfig:
    """Test DAB+ configuration."""

    def test_create_config(self) -> None:
        """Test creating config."""
        config = DabPlusConfig(
            bitrate=64,
            profile=DabPlusProfile.HE_AAC_V2
        )
        assert config.bitrate == 64
        assert config.profile == DabPlusProfile.HE_AAC_V2

    def test_get_au_size(self) -> None:
        """Test AU size calculation."""
        # For 32 kbps: AU = 32 * 3 = 96 bytes
        config = DabPlusConfig(bitrate=32, profile=DabPlusProfile.HE_AAC)
        assert config.get_au_size() == 96

        # For 64 kbps: AU = 64 * 3 = 192 bytes
        config = DabPlusConfig(bitrate=64, profile=DabPlusProfile.HE_AAC)
        assert config.get_au_size() == 192

    def test_get_superframe_size(self) -> None:
        """Test superframe size calculation."""
        config = DabPlusConfig(bitrate=48, profile=DabPlusProfile.HE_AAC)
        size = config.get_superframe_size()
        # Should be > 5 * 48 * 3 due to RS overhead
        assert size > 720

    def test_requires_enhanced_packet_mode(self) -> None:
        """Test enhanced packet mode requirement."""
        config = DabPlusConfig(bitrate=64, profile=DabPlusProfile.HE_AAC)
        assert config.requires_enhanced_packet_mode() is True

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = DabPlusConfig(bitrate=64, profile=DabPlusProfile.HE_AAC)
        assert config.sample_rate == 48000
        assert config.channels == 2
        assert config.sbr is True
        assert config.ps is False


class TestDabPlusProfile:
    """Test DAB+ profile enum."""

    def test_profile_values(self) -> None:
        """Test profile enum values."""
        assert DabPlusProfile.HE_AAC.value == "he-aac"
        assert DabPlusProfile.HE_AAC_V2.value == "he-aac-v2"


class TestCalculateDabplusSubchannelSize:
    """Test DAB+ subchannel size calculation."""

    def test_size_calculation(self) -> None:
        """Test size calculation for various bitrates."""
        # 32 kbps -> 32 CUs
        assert calculate_dabplus_subchannel_size(32) == 32

        # 64 kbps -> 64 CUs
        assert calculate_dabplus_subchannel_size(64) == 64

        # 96 kbps -> 96 CUs
        assert calculate_dabplus_subchannel_size(96) == 96


class TestCreateDummySuperframe:
    """Test dummy superframe creation."""

    def test_create_dummy(self) -> None:
        """Test creating dummy superframe."""
        config = DabPlusConfig(bitrate=64, profile=DabPlusProfile.HE_AAC)
        data = create_dummy_superframe(config)

        # Should have correct size
        assert len(data) == config.get_superframe_size()

        # Should be zero-filled (placeholder)
        assert all(b == 0 for b in data)


class TestParseDabplusBitrate:
    """Test DAB+ bitrate parsing."""

    def test_parse_numeric(self) -> None:
        """Test parsing numeric bitrate."""
        assert parse_dabplus_bitrate("32") == 32
        assert parse_dabplus_bitrate("64") == 64
        assert parse_dabplus_bitrate("96") == 96

    def test_parse_with_k_suffix(self) -> None:
        """Test parsing with 'k' suffix."""
        assert parse_dabplus_bitrate("32k") == 32
        assert parse_dabplus_bitrate("64K") == 64

    def test_parse_with_kbps_suffix(self) -> None:
        """Test parsing with 'kbps' suffix."""
        assert parse_dabplus_bitrate("32kbps") == 32
        assert parse_dabplus_bitrate("64KBPS") == 64

    def test_parse_with_spaces(self) -> None:
        """Test parsing with spaces."""
        assert parse_dabplus_bitrate(" 32 ") == 32
        assert parse_dabplus_bitrate(" 64 k ") == 64

    def test_parse_invalid_format(self) -> None:
        """Test parsing invalid format."""
        with pytest.raises(ValueError):
            parse_dabplus_bitrate("invalid")

        with pytest.raises(ValueError):
            parse_dabplus_bitrate("abc")

    def test_parse_invalid_bitrate(self) -> None:
        """Test parsing unsupported bitrate."""
        with pytest.raises(ValueError):
            parse_dabplus_bitrate("7")  # Too low

        with pytest.raises(ValueError):
            parse_dabplus_bitrate("200")  # Too high


class TestGetRecommendedBitrate:
    """Test recommended bitrate lookup."""

    def test_get_speech_mono(self) -> None:
        """Test speech mono recommendation."""
        bitrate = get_recommended_bitrate('speech_mono')
        assert bitrate == DABPLUS_RECOMMENDED_BITRATES['speech_mono']
        assert bitrate == 32

    def test_get_music_mono(self) -> None:
        """Test music mono recommendation."""
        bitrate = get_recommended_bitrate('music_mono')
        assert bitrate == 48

    def test_get_music_stereo(self) -> None:
        """Test music stereo recommendation."""
        bitrate = get_recommended_bitrate('music_stereo')
        assert bitrate == 80

    def test_get_music_stereo_hq(self) -> None:
        """Test music stereo HQ recommendation."""
        bitrate = get_recommended_bitrate('music_stereo_hq')
        assert bitrate == 96

    def test_get_unknown_type(self) -> None:
        """Test unknown content type (returns default)."""
        bitrate = get_recommended_bitrate('unknown')
        assert bitrate == 80  # Default


class TestDabPlusRecommendations:
    """Test DAB+ recommendation constants."""

    def test_recommendations_exist(self) -> None:
        """Test that all recommendations are defined."""
        assert 'speech_mono' in DABPLUS_RECOMMENDED_BITRATES
        assert 'music_mono' in DABPLUS_RECOMMENDED_BITRATES
        assert 'music_stereo' in DABPLUS_RECOMMENDED_BITRATES
        assert 'music_stereo_hq' in DABPLUS_RECOMMENDED_BITRATES

    def test_recommendations_valid(self) -> None:
        """Test that all recommendations are valid bitrates."""
        valid_bitrates = [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 112, 128, 144, 160, 192]

        for bitrate in DABPLUS_RECOMMENDED_BITRATES.values():
            assert bitrate in valid_bitrates
