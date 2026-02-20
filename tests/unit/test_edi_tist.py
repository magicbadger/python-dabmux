"""
Tests for EDI TIST (Timestamp) TAG.

Per ETSI TS 102 693 Section 5.1.5.2.
"""
import pytest
import struct
import time
from dabmux.edi.protocol import TagTIST, EDI_EPOCH_UNIX


class TestTagTIST_Encoding:
    """Test TIST TAG encoding."""

    def test_tag_name(self):
        """Test TIST TAG name is 'tist'."""
        tist = TagTIST(seconds=0, ticks=0)
        assert tist.get_name() == b"tist"

    def test_value_length(self):
        """Test TIST value is 7 bytes (56 bits)."""
        tist = TagTIST(seconds=0, ticks=0)
        value = tist.get_value()
        assert len(value) == 7

    def test_zero_timestamp(self):
        """Test encoding of zero timestamp."""
        tist = TagTIST(seconds=0, ticks=0)
        value = tist.get_value()

        # Should be 7 bytes of zeros
        assert value == b'\x00\x00\x00\x00\x00\x00\x00'

    def test_seconds_encoding(self):
        """Test encoding of seconds field."""
        # 1000 seconds = 0x3E8
        tist = TagTIST(seconds=1000, ticks=0)
        value = tist.get_value()

        # Full value: (1000 << 24) = 0x3E8000000
        # As 64-bit big-endian: 00 00 00 03 E8 00 00 00
        # Take last 7 bytes (skip first): 00 00 03 E8 00 00 00
        assert value == b'\x00\x00\x03\xe8\x00\x00\x00'

    def test_ticks_encoding(self):
        """Test encoding of ticks field (24-bit)."""
        # 16384 ticks = 0x4000 = 1 second
        tist = TagTIST(seconds=0, ticks=16384)
        value = tist.get_value()

        # Last 3 bytes should contain 16384 (big-endian)
        # As 7 bytes: 00 00 00 00 00 40 00
        assert value == b'\x00\x00\x00\x00\x00\x40\x00'

    def test_combined_encoding(self):
        """Test encoding of both seconds and ticks."""
        # 100 seconds + 8192 ticks (0.5 seconds)
        tist = TagTIST(seconds=100, ticks=8192)
        value = tist.get_value()

        # Combined: (100 << 24) | 8192 = 0x6400002000
        # As 7 bytes: 00 00 00 64 00 20 00
        assert value == b'\x00\x00\x00\x64\x00\x20\x00'

    def test_max_values(self):
        """Test encoding with maximum values."""
        # Max seconds: 2^32 - 1
        # Max ticks: 2^24 - 1
        tist = TagTIST(seconds=0xFFFFFFFF, ticks=0xFFFFFF)
        value = tist.get_value()

        # Should be 7 bytes of 0xFF
        assert value == b'\xff\xff\xff\xff\xff\xff\xff'


class TestTagTIST_UnixConversion:
    """Test Unix timestamp conversion."""

    def test_edi_epoch_conversion(self):
        """Test conversion at EDI epoch (2000-01-01)."""
        # EDI epoch in Unix time
        unix_ts = EDI_EPOCH_UNIX  # 946684800
        tist = TagTIST.from_unix_timestamp(float(unix_ts))

        # Should be 0 seconds in EDI epoch
        assert tist.seconds == 0
        assert tist.ticks == 0

    def test_unix_to_edi_seconds(self):
        """Test Unix to EDI seconds conversion."""
        # 1 year after EDI epoch = 31536000 seconds
        unix_ts = EDI_EPOCH_UNIX + 31536000
        tist = TagTIST.from_unix_timestamp(float(unix_ts))

        assert tist.seconds == 31536000

    def test_subsecond_ticks(self):
        """Test sub-second tick calculation."""
        # 0.5 seconds = 8192 ticks (16384 / 2)
        unix_ts = EDI_EPOCH_UNIX + 0.5
        tist = TagTIST.from_unix_timestamp(unix_ts)

        assert tist.seconds == 0
        assert tist.ticks == 8192

    def test_combined_timestamp(self):
        """Test conversion with both integer and fractional parts."""
        # 1000.25 seconds after epoch
        unix_ts = EDI_EPOCH_UNIX + 1000.25
        tist = TagTIST.from_unix_timestamp(unix_ts)

        assert tist.seconds == 1000
        # 0.25 seconds = 16384 / 4 = 4096 ticks
        assert tist.ticks == 4096

    def test_current_time_conversion(self):
        """Test conversion of current time."""
        unix_ts = time.time()
        tist = TagTIST.from_unix_timestamp(unix_ts)

        # Should be reasonable values
        assert tist.seconds > 0
        assert 0 <= tist.ticks < 16384


class TestTagTIST_Precision:
    """Test TIST timestamp precision."""

    def test_tick_resolution(self):
        """Test tick resolution is 1/16384 second (~61 microseconds)."""
        # 1 tick = 1/16384 second = 0.000061035 seconds
        tick_duration = 1.0 / 16384

        unix_ts = EDI_EPOCH_UNIX + tick_duration
        tist = TagTIST.from_unix_timestamp(unix_ts)

        assert tist.ticks == 1

    def test_tick_truncation(self):
        """Test that sub-tick precision is truncated (not rounded)."""
        # 0.5 ticks should truncate to 0
        unix_ts = EDI_EPOCH_UNIX + (0.5 / 16384)
        tist = TagTIST.from_unix_timestamp(unix_ts)

        assert tist.ticks == 0

    def test_24bit_tick_limit(self):
        """Test that ticks are limited to 24 bits."""
        # Try to create TIST with ticks > 24 bits
        tist = TagTIST(seconds=0, ticks=0x1FFFFFF)  # 25 bits

        # get_value should mask to 24 bits
        value = tist.get_value()
        # Last 3 bytes should only have 24 bits
        last_3_bytes = struct.unpack('>I', b'\x00' + value[-3:])[0]
        assert last_3_bytes == 0xFFFFFF


class TestTagTIST_Assembly:
    """Test TIST TAG assembly."""

    def test_assemble_complete_tag(self):
        """Test complete TAG assembly (name + length + value)."""
        tist = TagTIST(seconds=100, ticks=8192)
        tag_bytes = tist.assemble()

        # Should be: name(4) + length(4) + value(7) = 15 bytes
        assert len(tag_bytes) >= 8  # At least header

        # Check name
        assert tag_bytes[0:4] == b"tist"

        # Check length (in BITS)
        length_bits = struct.unpack('>I', tag_bytes[4:8])[0]
        assert length_bits == 56  # 7 bytes * 8 bits

    def test_assemble_with_value(self):
        """Test that assembled TAG includes correct value."""
        tist = TagTIST(seconds=12345, ticks=6789)
        tag_bytes = tist.assemble()

        # Extract value (skip name[4] + length[4])
        value = tag_bytes[8:]
        assert len(value) == 7

        # Verify value encoding
        expected_value = tist.get_value()
        assert value == expected_value


class TestTagTIST_EdgeCases:
    """Test TIST edge cases."""

    def test_negative_unix_timestamp(self):
        """Test handling of Unix timestamp before EDI epoch."""
        # Unix timestamp before 2000-01-01
        unix_ts = EDI_EPOCH_UNIX - 1000
        tist = TagTIST.from_unix_timestamp(float(unix_ts))

        # Should result in negative seconds (underflow)
        assert tist.seconds < 0 or tist.seconds > 0x7FFFFFFF

    def test_far_future_timestamp(self):
        """Test timestamp far in the future."""
        # Year 2100 (100 years after EDI epoch)
        unix_ts = EDI_EPOCH_UNIX + (100 * 365.25 * 24 * 3600)
        tist = TagTIST.from_unix_timestamp(unix_ts)

        # Should be within 32-bit range (until ~2136)
        assert 0 <= tist.seconds < 0x100000000

    def test_zero_ticks_edge(self):
        """Test exact second boundary (no fractional part)."""
        unix_ts = float(EDI_EPOCH_UNIX + 1234)
        tist = TagTIST.from_unix_timestamp(unix_ts)

        assert tist.seconds == 1234
        assert tist.ticks == 0
