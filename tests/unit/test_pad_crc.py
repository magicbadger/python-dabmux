"""Tests for PAD CRC calculation."""

import pytest
from dabmux.pad.crc import crc16_ccitt_pad


class TestPADCRC:
    """Test CRC-16-CCITT calculation for PAD data groups."""

    def test_crc_empty_data(self):
        """Test CRC of empty data."""
        crc = crc16_ccitt_pad(b'')
        assert crc == 0xFFFF

    def test_crc_zero_bytes(self):
        """Test CRC of zero bytes."""
        crc = crc16_ccitt_pad(b'\x00\x00')
        assert crc == 0x1D0F

    def test_crc_all_ones(self):
        """Test CRC of all ones."""
        crc = crc16_ccitt_pad(b'\xFF\xFF')
        assert crc == 0x0000  # CRC-16-CCITT of all ones

    def test_crc_known_values(self):
        """Test CRC against known values (from actual CRC-16-CCITT calculation)."""
        test_vectors = [
            (b'\x00', 0xE1F0),
            (b'\x01', 0xF1D1),
            (b'\xFF', 0xFF00),
            (b'\x12\x34', 0x0EC9),
            (b'\xAB\xCD\xEF', 0xED38),
        ]

        for data, expected_crc in test_vectors:
            crc = crc16_ccitt_pad(data)
            assert crc == expected_crc, f"CRC mismatch for {data.hex()}: got {crc:04X}, expected {expected_crc:04X}"

    def test_crc_typical_dls(self):
        """Test CRC with typical DLS data."""
        # Simulate a DLS segment header + text
        dls_data = b'\x60\x0BHello World'  # Header + "Hello World"
        crc = crc16_ccitt_pad(dls_data)

        # CRC should be a 16-bit value
        assert 0 <= crc <= 0xFFFF
        assert isinstance(crc, int)

    def test_crc_consistency(self):
        """Test CRC consistency - same input produces same output."""
        data = b'Test data for CRC'
        crc1 = crc16_ccitt_pad(data)
        crc2 = crc16_ccitt_pad(data)
        assert crc1 == crc2

    def test_crc_different_data(self):
        """Test that different data produces different CRCs."""
        crc1 = crc16_ccitt_pad(b'Data A')
        crc2 = crc16_ccitt_pad(b'Data B')
        assert crc1 != crc2

    def test_crc_length_sensitivity(self):
        """Test CRC is sensitive to data length."""
        crc1 = crc16_ccitt_pad(b'Test')
        crc2 = crc16_ccitt_pad(b'Test\x00')  # Extra null byte
        assert crc1 != crc2
