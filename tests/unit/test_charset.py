"""
Unit tests for character set handling.
"""
import pytest
from dabmux.utils.charset import (
    utf8_to_ebu_latin,
    ebu_latin_to_utf8,
    calculate_label_short_mask,
    validate_label,
    EBU_LATIN_TO_UNICODE,
    UNICODE_TO_EBU_LATIN
)


class TestUTF8ToEBULatin:
    """Test UTF-8 to EBU Latin conversion."""

    def test_convert_ascii(self) -> None:
        """Test converting ASCII text."""
        text = "Hello"
        result = utf8_to_ebu_latin(text, max_length=16, pad=False)
        assert result == b"Hello"

    def test_convert_with_padding(self) -> None:
        """Test conversion with padding."""
        text = "Hello"
        result = utf8_to_ebu_latin(text, max_length=16, pad=True)
        assert len(result) == 16
        assert result[:5] == b"Hello"
        assert result[5:] == b" " * 11

    def test_convert_special_chars(self) -> None:
        """Test converting special characters."""
        text = "Café"  # Contains é (U+00E9)
        result = utf8_to_ebu_latin(text, max_length=16, pad=False)
        assert len(result) == 4
        assert result[0:3] == b"Caf"
        assert result[3] == 0xE9  # é in EBU Latin

    def test_convert_german_chars(self) -> None:
        """Test converting German characters."""
        text = "Köln"  # Contains ö (U+00F6)
        result = utf8_to_ebu_latin(text, max_length=16, pad=False)
        assert b"K" in result
        assert 0xF6 in result  # ö in EBU Latin

    def test_truncate_long_text(self) -> None:
        """Test truncating text that's too long."""
        text = "This is a very long text that exceeds the maximum"
        result = utf8_to_ebu_latin(text, max_length=16, pad=False)
        assert len(result) == 16
        assert result == b"This is a very l"

    def test_unsupported_char_replacement(self) -> None:
        """Test that unsupported characters are replaced."""
        text = "Test 中文"  # Contains Chinese characters
        result = utf8_to_ebu_latin(text, max_length=16, pad=False)
        # Chinese characters should be replaced with spaces
        assert b"Test" in result


class TestEBULatinToUTF8:
    """Test EBU Latin to UTF-8 conversion."""

    def test_convert_ascii(self) -> None:
        """Test converting ASCII bytes."""
        data = b"Hello"
        result = ebu_latin_to_utf8(data)
        assert result == "Hello"

    def test_convert_special_chars(self) -> None:
        """Test converting special characters."""
        data = b"Caf\xe9"  # Café with é (0xE9)
        result = ebu_latin_to_utf8(data)
        assert result == "Café"

    def test_convert_with_trailing_spaces(self) -> None:
        """Test that trailing spaces are stripped."""
        data = b"Hello     "
        result = ebu_latin_to_utf8(data)
        assert result == "Hello"

    def test_roundtrip(self) -> None:
        """Test roundtrip conversion."""
        original = "Radio Station"
        ebu = utf8_to_ebu_latin(original, max_length=16, pad=True)
        back = ebu_latin_to_utf8(ebu)
        assert back == original


class TestCalculateLabelShortMask:
    """Test short label mask calculation."""

    def test_simple_mask(self) -> None:
        """Test simple short label mask."""
        label = "Radio One"
        short_label = "Radio"
        mask = calculate_label_short_mask(label, short_label)

        # "Radio" is first 5 characters
        # Mask should be: 11111000 00000000 = 0xF800
        assert mask == 0xF800

    def test_non_contiguous_mask(self) -> None:
        """Test non-contiguous short label."""
        label = "BBC Radio 1"
        short_label = "BBC1"

        # B(0) B(1) C(2) R(4) 1(10)
        # Mask bits: 15,14,13,11,5 set
        mask = calculate_label_short_mask(label, short_label)
        assert mask != 0

    def test_empty_short_label(self) -> None:
        """Test with empty short label."""
        mask = calculate_label_short_mask("Radio", "")
        assert mask == 0

    def test_invalid_short_label(self) -> None:
        """Test with invalid short label (chars not in order)."""
        with pytest.raises(ValueError):
            calculate_label_short_mask("Radio One", "OneRadio")


class TestValidateLabel:
    """Test label validation."""

    def test_valid_label(self) -> None:
        """Test valid label."""
        assert validate_label("Radio One", "Radio") is True

    def test_label_too_long(self) -> None:
        """Test label that's too long."""
        with pytest.raises(ValueError, match="Label too long"):
            validate_label("A" * 17, "")

    def test_short_label_too_long(self) -> None:
        """Test short label that's too long."""
        with pytest.raises(ValueError, match="Short label too long"):
            validate_label("Radio", "A" * 9)

    def test_invalid_short_label_order(self) -> None:
        """Test invalid short label character order."""
        with pytest.raises(ValueError, match="Invalid short label"):
            validate_label("Radio One", "OneRadio")

    def test_valid_special_chars(self) -> None:
        """Test label with valid special characters."""
        assert validate_label("Café Music", "Café") is True


class TestCharsetMappings:
    """Test character set mapping tables."""

    def test_ebu_latin_table_completeness(self) -> None:
        """Test that EBU Latin table has all entries."""
        assert len(EBU_LATIN_TO_UNICODE) == 256

    def test_ascii_identity_mapping(self) -> None:
        """Test that 0x00-0x7F maps to ASCII."""
        for i in range(0x80):
            assert EBU_LATIN_TO_UNICODE[i] == chr(i)

    def test_reverse_mapping(self) -> None:
        """Test that reverse mapping excludes unused characters."""
        # Unused characters (0x0000) should not be in reverse map
        assert '\u0000' not in UNICODE_TO_EBU_LATIN.values()

    def test_specific_mappings(self) -> None:
        """Test specific character mappings."""
        # Test common European characters
        assert EBU_LATIN_TO_UNICODE[0xE9] == '\u00E9'  # é
        assert EBU_LATIN_TO_UNICODE[0xF6] == '\u00F6'  # ö
        assert EBU_LATIN_TO_UNICODE[0xFC] == '\u00FC'  # ü
        assert EBU_LATIN_TO_UNICODE[0xC4] == '\u00C4'  # Ä
        assert EBU_LATIN_TO_UNICODE[0xD6] == '\u00D6'  # Ö
        assert EBU_LATIN_TO_UNICODE[0xDC] == '\u00DC'  # Ü
        assert EBU_LATIN_TO_UNICODE[0xDF] == '\u00DF'  # ß

    def test_arrow_characters(self) -> None:
        """Test arrow character mappings."""
        assert EBU_LATIN_TO_UNICODE[0xAC] == '\u2190'  # ←
        assert EBU_LATIN_TO_UNICODE[0xAD] == '\u2191'  # ↑
        assert EBU_LATIN_TO_UNICODE[0xAE] == '\u2192'  # →
        assert EBU_LATIN_TO_UNICODE[0xAF] == '\u2193'  # ↓

    def test_quotation_marks(self) -> None:
        """Test quotation mark mappings."""
        assert EBU_LATIN_TO_UNICODE[0xA9] == '\u2018'  # '
        assert EBU_LATIN_TO_UNICODE[0xAA] == '\u201C'  # "
        assert EBU_LATIN_TO_UNICODE[0xB9] == '\u2019'  # '
        assert EBU_LATIN_TO_UNICODE[0xBA] == '\u201D'  # "
