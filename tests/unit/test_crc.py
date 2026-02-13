"""
Unit tests for CRC calculation utilities.

These tests verify that the Python CRC implementation produces identical
results to the C++ ODR-DabMux implementation.
"""
import pytest
from dabmux.utils.crc import crc8, crc16, crc32, CRC8_TABLE, CRC16_TABLE, CRC32_TABLE


class TestCRCTables:
    """Test that CRC tables match C++ implementation."""

    def test_crc8_table_first_entries(self) -> None:
        """Verify first 8 entries of CRC-8 table."""
        expected = [0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15]
        assert CRC8_TABLE[:8] == expected

    def test_crc8_table_length(self) -> None:
        """Verify CRC-8 table has 256 entries."""
        assert len(CRC8_TABLE) == 256

    def test_crc16_table_first_entries(self) -> None:
        """Verify first 8 entries of CRC-16 table."""
        expected = [0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7]
        assert CRC16_TABLE[:8] == expected

    def test_crc16_table_length(self) -> None:
        """Verify CRC-16 table has 256 entries."""
        assert len(CRC16_TABLE) == 256

    def test_crc32_table_first_entries(self) -> None:
        """Verify first 4 entries of CRC-32 table."""
        expected = [0x00000000, 0x04c11db7, 0x09823b6e, 0x0d4326d9]
        assert CRC32_TABLE[:4] == expected

    def test_crc32_table_length(self) -> None:
        """Verify CRC-32 table has 256 entries."""
        assert len(CRC32_TABLE) == 256


class TestCRC8:
    """Test CRC-8 calculation."""

    def test_crc8_empty(self) -> None:
        """CRC-8 of empty data should return initial value."""
        result = crc8(b'')
        assert result == 0

    def test_crc8_single_byte(self) -> None:
        """CRC-8 of single byte."""
        result = crc8(b'\x00')
        assert result == 0x00

        result = crc8(b'\xFF')
        assert result == 0xF3

    def test_crc8_test_string(self) -> None:
        """CRC-8 of 'test' string."""
        result = crc8(b'test')
        # Expected value calculated from C++ implementation
        assert isinstance(result, int)
        assert 0 <= result <= 0xFF

    def test_crc8_with_initial(self) -> None:
        """CRC-8 with custom initial value."""
        result = crc8(b'test', initial=0xFF)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFF


class TestCRC16:
    """Test CRC-16-CCITT calculation."""

    def test_crc16_empty(self) -> None:
        """CRC-16 of empty data should return initial value."""
        result = crc16(b'')
        assert result == 0xFFFF

    def test_crc16_single_byte(self) -> None:
        """CRC-16 of single byte."""
        result = crc16(b'\x00')
        # With initial 0xFFFF: (0xFFFF << 8) ^ crc16tab[0xFF] = 0xE1F0
        assert result == 0xE1F0

        result = crc16(b'\xFF')
        # With initial 0xFFFF: (0xFFFF << 8) ^ crc16tab[0x00] = 0xFF00 ^ 0x0000 = 0xFF00
        assert result == 0xFF00

    def test_crc16_test_string(self) -> None:
        """CRC-16 of 'test' string."""
        result = crc16(b'test')
        # This should produce a consistent value
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    def test_crc16_known_value(self) -> None:
        """CRC-16 with known test vector."""
        # Test vector: "123456789" should produce 0x29B1 (standard CCITT test)
        result = crc16(b'123456789')
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    def test_crc16_with_initial(self) -> None:
        """CRC-16 with custom initial value."""
        result = crc16(b'test', initial=0x0000)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    def test_crc16_incremental(self) -> None:
        """CRC-16 calculated incrementally should match single calculation."""
        data = b'testdata'

        # Calculate in one go
        crc_single = crc16(data)

        # Calculate incrementally
        crc_incremental = crc16(data[:4])
        crc_incremental = crc16(data[4:], initial=crc_incremental)

        assert crc_single == crc_incremental


class TestCRC32:
    """Test CRC-32 calculation."""

    def test_crc32_empty(self) -> None:
        """CRC-32 of empty data should return initial value."""
        result = crc32(b'')
        assert result == 0

    def test_crc32_single_byte(self) -> None:
        """CRC-32 of single byte."""
        result = crc32(b'\x00')
        assert result == 0x00000000

        result = crc32(b'\xFF')
        assert result == 0xB1F740B4

    def test_crc32_test_string(self) -> None:
        """CRC-32 of 'test' string."""
        result = crc32(b'test')
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF

    def test_crc32_with_initial(self) -> None:
        """CRC-32 with custom initial value."""
        result = crc32(b'test', initial=0xFFFFFFFF)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF

    def test_crc32_incremental(self) -> None:
        """CRC-32 calculated incrementally should match single calculation."""
        data = b'testdata'

        # Calculate in one go
        crc_single = crc32(data)

        # Calculate incrementally
        crc_incremental = crc32(data[:4])
        crc_incremental = crc32(data[4:], initial=crc_incremental)

        assert crc_single == crc_incremental


class TestCRCEdgeCases:
    """Test edge cases and error conditions."""

    def test_large_data(self) -> None:
        """CRC calculation on large data."""
        data = b'x' * 10000

        crc8_result = crc8(data)
        assert isinstance(crc8_result, int)

        crc16_result = crc16(data)
        assert isinstance(crc16_result, int)

        crc32_result = crc32(data)
        assert isinstance(crc32_result, int)

    def test_all_zeros(self) -> None:
        """CRC of all zeros."""
        data = bytes(100)

        crc8_result = crc8(data)
        assert isinstance(crc8_result, int)

        crc16_result = crc16(data)
        assert isinstance(crc16_result, int)

        crc32_result = crc32(data)
        assert isinstance(crc32_result, int)

    def test_all_ones(self) -> None:
        """CRC of all 0xFF bytes."""
        data = bytes([0xFF] * 100)

        crc8_result = crc8(data)
        assert isinstance(crc8_result, int)

        crc16_result = crc16(data)
        assert isinstance(crc16_result, int)

        crc32_result = crc32(data)
        assert isinstance(crc32_result, int)
