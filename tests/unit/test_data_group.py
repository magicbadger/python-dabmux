"""Tests for PAD data group encoding."""

import pytest
from dabmux.pad.data_group import PADDataGroup


class TestPADDataGroup:
    """Test PAD data group encoding and structure."""

    def test_data_group_basic_encoding(self):
        """Test basic data group encoding."""
        dg = PADDataGroup(
            extension=False,
            crc_flag=True,
            segment=True,
            user_access=2,  # DLS
            data=b'Hello'
        )

        encoded = dg.encode()

        # Check header byte
        # Bit 7 = 0 (no extension)
        # Bit 6 = 1 (CRC present)
        # Bit 5 = 1 (segment flag)
        # Bits 4-0 = 2 (user access)
        expected_header = 0x60 | 0x02  # 01100010 = 0x62
        assert encoded[0] == expected_header

        # Check length (should be 5 for "Hello")
        assert encoded[1] == 5

        # Check data
        assert encoded[2:7] == b'Hello'

        # Check total length (header + length + data + CRC)
        assert len(encoded) == 1 + 1 + 5 + 2  # 9 bytes

    def test_data_group_no_crc(self):
        """Test data group without CRC."""
        dg = PADDataGroup(
            extension=False,
            crc_flag=False,
            segment=True,
            user_access=2,
            data=b'Test'
        )

        encoded = dg.encode()

        # Total length should be: header + length + data (no CRC)
        assert len(encoded) == 1 + 1 + 4  # 6 bytes

    def test_data_group_length_encoding_short(self):
        """Test short length encoding (< 128 bytes)."""
        # Data less than 128 bytes should use 1-byte length
        data = b'A' * 50
        dg = PADDataGroup(data=data, crc_flag=False)

        encoded = dg.encode()

        # Length should be in byte 1, single byte
        assert encoded[1] == 50
        assert encoded[1] < 128  # Bit 7 should be 0

    def test_data_group_length_encoding_long(self):
        """Test long length encoding (>= 128 bytes)."""
        # Data >= 128 bytes should use 2-byte length
        data = b'B' * 150
        dg = PADDataGroup(data=data, crc_flag=False)

        encoded = dg.encode()

        # Length should be in bytes 1-2, first byte has bit 7 set
        assert encoded[1] & 0x80 == 0x80  # Bit 7 set
        length = ((encoded[1] & 0x7F) << 8) | encoded[2]
        assert length == 150

    def test_data_group_crc_validity(self):
        """Test that CRC is correctly appended."""
        dg = PADDataGroup(
            extension=False,
            crc_flag=True,
            segment=True,
            user_access=2,
            data=b'TestData'
        )

        encoded = dg.encode()

        # CRC should be last 2 bytes
        crc_bytes = encoded[-2:]
        assert len(crc_bytes) == 2

        # CRC should be non-zero for non-zero data
        crc_value = (crc_bytes[0] << 8) | crc_bytes[1]
        assert crc_value != 0

    def test_data_group_empty_data(self):
        """Test data group with empty data."""
        dg = PADDataGroup(
            extension=False,
            crc_flag=True,
            segment=False,
            user_access=0,
            data=b''
        )

        encoded = dg.encode()

        # Should have header + length(0) + CRC
        assert len(encoded) == 1 + 1 + 2  # 4 bytes
        assert encoded[1] == 0  # Length = 0

    def test_data_group_user_access_field(self):
        """Test various user access field values."""
        for user_access in [0, 2, 12, 31]:  # 5-bit field, max 31
            dg = PADDataGroup(
                user_access=user_access,
                data=b'Test',
                crc_flag=False
            )

            encoded = dg.encode()

            # Extract user access from header
            extracted_ua = encoded[0] & 0x1F
            assert extracted_ua == user_access

    def test_data_group_all_flags_set(self):
        """Test data group with all flags enabled."""
        dg = PADDataGroup(
            extension=True,
            crc_flag=True,
            segment=True,
            user_access=31,
            data=b'X'
        )

        encoded = dg.encode()

        # Header should have all top 3 bits set
        assert encoded[0] & 0xE0 == 0xE0  # Bits 7, 6, 5 all set
        assert encoded[0] & 0x1F == 31    # User access = 31

    def test_data_group_decode_length(self):
        """Test length field decoding."""
        # Test short form
        data_short = bytes([0x60, 0x0A, 0x00])  # Length = 10
        length, consumed = PADDataGroup.decode_length(data_short, offset=1)
        assert length == 10
        assert consumed == 1

        # Test long form
        data_long = bytes([0x60, 0x80, 0x96, 0x00])  # Length = 150 (0x0096)
        length, consumed = PADDataGroup.decode_length(data_long, offset=1)
        assert length == 150
        assert consumed == 2

    def test_data_group_consistency(self):
        """Test encoding consistency - same input produces same output."""
        dg = PADDataGroup(data=b'Consistent')

        encoded1 = dg.encode()
        encoded2 = dg.encode()

        assert encoded1 == encoded2
