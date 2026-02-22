"""
Unit tests for MSC Data Group encoding.

Tests per ETSI EN 300 401 Section 5.3.3.
"""

import pytest
from dabmux.mot.msc_datagroup import (
    MscDataGroup, MscDataGroupSegmenter, segment_mot_object
)
from dabmux.mot.object import MotObject
from dabmux.mot.header import MotHeader, MotContentType


class TestMscDataGroup:
    """Tests for MscDataGroup class."""

    def test_datagroup_creation(self):
        """Test creating data group."""
        dg = MscDataGroup(
            extension=False,
            crc_flag=True,
            segment=False,
            user_access=0x001,
            data=b'test data'
        )

        assert dg.extension is False
        assert dg.crc_flag is True
        assert dg.segment is False
        assert dg.user_access == 0x001
        assert dg.data == b'test data'

    def test_datagroup_encode(self):
        """Test encoding data group."""
        dg = MscDataGroup(
            extension=False,
            crc_flag=True,
            segment=False,
            user_access=0x001,
            data=b'Hello'
        )

        encoded = dg.encode()

        # Check header byte
        # Bit 7: extension=0, Bit 6: crc=1, Bit 5: segment=0, Bits 4-0: user_access=0x01
        assert encoded[0] == 0x41  # 0b01000001

        # Check length (1 byte for short form)
        assert encoded[1] == 5  # "Hello" length

        # Check data
        assert encoded[2:7] == b'Hello'

        # Check CRC present (2 bytes)
        assert len(encoded) == 9  # header(1) + length(1) + data(5) + crc(2)

    def test_datagroup_encode_no_crc(self):
        """Test encoding data group without CRC."""
        dg = MscDataGroup(
            crc_flag=False,
            data=b'test'
        )

        encoded = dg.encode()

        # No CRC, so length = header(1) + length(1) + data(4)
        assert len(encoded) == 6

    def test_datagroup_encode_short_length(self):
        """Test encoding with short length form (< 128 bytes)."""
        data = b'x' * 100

        dg = MscDataGroup(data=data, crc_flag=False)
        encoded = dg.encode()

        # Header + length(1 byte) + data(100)
        assert len(encoded) == 102
        assert encoded[1] == 100  # Short form length

    def test_datagroup_encode_long_length(self):
        """Test encoding with long length form (>= 128 bytes)."""
        data = b'x' * 200

        dg = MscDataGroup(data=data, crc_flag=False)
        encoded = dg.encode()

        # Header + length(2 bytes) + data(200)
        assert len(encoded) == 203

        # Long form: first byte has bit 7 set
        assert encoded[1] & 0x80 == 0x80
        # Decode length
        length = ((encoded[1] & 0x7F) << 8) | encoded[2]
        assert length == 200

    def test_datagroup_decode_length_short(self):
        """Test decoding short length form."""
        data = bytes([0x00, 0x50, 0x00])  # Length = 80 (0x50)

        length, consumed = MscDataGroup.decode_length(data, offset=1)

        assert length == 80
        assert consumed == 1

    def test_datagroup_decode_length_long(self):
        """Test decoding long length form."""
        # Length = 300 = 0x012C
        # Byte 1: 0x81 (bit 7 set, high byte = 0x01)
        # Byte 2: 0x2C (low byte)
        data = bytes([0x00, 0x81, 0x2C, 0x00])

        length, consumed = MscDataGroup.decode_length(data, offset=1)

        assert length == 300
        assert consumed == 2


class TestMscDataGroupSegmenter:
    """Tests for MscDataGroupSegmenter."""

    def test_segmenter_creation(self):
        """Test creating segmenter."""
        segmenter = MscDataGroupSegmenter(max_segment_size=1000)

        assert segmenter.max_segment_size == 1000

    def test_segment_small_object(self):
        """Test segmenting small MOT object."""
        # Create small object
        header = MotHeader(
            body_size=100,
            content_type=MotContentType.IMAGE_JFIF
        )
        obj = MotObject(
            header=header,
            body=b'x' * 100,
            transport_id=10
        )

        segmenter = MscDataGroupSegmenter(max_segment_size=8188)
        segments = segmenter.segment_object(obj)

        # Should have 2 segments: header + body
        assert len(segments) == 2

        # First segment: header, more segments follow
        assert segments[0].segment is True  # More segments
        assert segments[0].user_access == 0x001  # MOT
        assert segments[0].crc_flag is True
        assert segments[0].segment_number == 0
        assert segments[0].last_segment is False

        # Second segment: body, last segment
        assert segments[1].segment is False  # No more segments
        assert segments[1].segment_number == 1
        assert segments[1].last_segment is True

    def test_segment_large_object(self):
        """Test segmenting large MOT object."""
        # Create large body that needs multiple segments
        body_size = 20000
        header = MotHeader(
            body_size=body_size,
            content_type=MotContentType.IMAGE_PNG
        )
        obj = MotObject(
            header=header,
            body=b'x' * body_size,
            transport_id=20
        )

        segmenter = MscDataGroupSegmenter(max_segment_size=8000)
        segments = segmenter.segment_object(obj)

        # Should have 1 header + 3 body segments (20000 / 8000 = 2.5 -> 3)
        assert len(segments) == 4

        # All segments except last should have segment=True
        for i in range(3):
            assert segments[i].segment is True

        # Last segment should have segment=False
        assert segments[3].segment is False
        assert segments[3].last_segment is True

        # Check segment numbers
        for i, seg in enumerate(segments):
            assert seg.segment_number == i

    def test_calculate_segment_count(self):
        """Test calculating segment count."""
        header = MotHeader(
            body_size=15000,
            content_type=MotContentType.IMAGE_JFIF
        )
        obj = MotObject(
            header=header,
            body=b'x' * 15000,
            transport_id=30
        )

        segmenter = MscDataGroupSegmenter(max_segment_size=8000)
        count = segmenter.calculate_segment_count(obj)

        # 1 header + 2 body segments (15000 / 8000 = 1.875 -> 2)
        assert count == 3

    def test_estimate_transmission_time(self):
        """Test estimating transmission time."""
        header = MotHeader(
            body_size=5000,
            content_type=MotContentType.IMAGE_PNG
        )
        obj = MotObject(
            header=header,
            body=b'x' * 5000,
            transport_id=40
        )

        segmenter = MscDataGroupSegmenter(max_segment_size=8000)
        time = segmenter.estimate_transmission_time(obj, bytes_per_frame=96)

        # Should return reasonable time in seconds
        assert isinstance(time, float)
        assert time > 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_segment_mot_object(self):
        """Test segment_mot_object convenience function."""
        header = MotHeader(
            body_size=1000,
            content_type=MotContentType.IMAGE_JFIF
        )
        obj = MotObject(
            header=header,
            body=b'x' * 1000,
            transport_id=50
        )

        segments = segment_mot_object(obj, max_segment_size=5000)

        # Should have 2 segments: header + body
        assert len(segments) == 2
        assert all(isinstance(seg, MscDataGroup) for seg in segments)
