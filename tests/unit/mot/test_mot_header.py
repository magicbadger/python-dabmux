"""
Unit tests for MOT Header encoding.

Tests per ETSI TS 101 499 Section 6.
"""

import pytest
from dabmux.mot.header import (
    MotHeader, MotParameter, MotContentType, MotParameterType
)


class TestMotParameter:
    """Tests for MotParameter encoding."""

    def test_parameter_creation(self):
        """Test creating a parameter."""
        param = MotParameter(param_id=0x0C, data=b'test.jpg')
        assert param.param_id == 0x0C
        assert param.data == b'test.jpg'

    def test_parameter_encode_short_length(self):
        """Test encoding parameter with short length (< 128 bytes)."""
        param = MotParameter(param_id=0x0C, data=b'test.jpg')
        encoded = param.encode()

        # Header byte: param_id (6 bits) << 2
        assert encoded[0] == (0x0C << 2)

        # Length byte: short form (bit 7 = 0)
        assert encoded[1] == 8  # len('test.jpg')

        # Data
        assert encoded[2:] == b'test.jpg'

    def test_parameter_encode_long_length(self):
        """Test encoding parameter with long length (>= 128 bytes)."""
        data = b'x' * 200
        param = MotParameter(param_id=0x25, data=data)
        encoded = param.encode()

        # Header byte
        assert encoded[0] == (0x25 << 2)

        # Length: long form (2 bytes, bit 7 = 1)
        assert encoded[1] & 0x80  # Long form flag
        length = ((encoded[1] & 0x7F) << 8) | encoded[2]
        assert length == 200

        # Data
        assert encoded[3:] == data


class TestMotHeader:
    """Tests for MotHeader encoding."""

    def test_header_creation(self):
        """Test creating a basic header."""
        header = MotHeader(
            body_size=1024,
            content_type=MotContentType.IMAGE_JFIF
        )

        assert header.body_size == 1024
        assert header.content_type == MotContentType.IMAGE_JFIF
        assert header.content_subtype == 0x00
        assert len(header.parameters) == 0

    def test_header_body_size_validation(self):
        """Test body size validation."""
        # Valid size
        header = MotHeader(
            body_size=1000,
            content_type=MotContentType.IMAGE_PNG
        )
        assert header.body_size == 1000

        # Maximum size (28 bits)
        max_size = (1 << 28) - 1
        header = MotHeader(
            body_size=max_size,
            content_type=MotContentType.IMAGE_PNG
        )
        assert header.body_size == max_size

        # Invalid: negative
        with pytest.raises(ValueError):
            MotHeader(
                body_size=-1,
                content_type=MotContentType.IMAGE_PNG
            )

        # Invalid: too large
        with pytest.raises(ValueError):
            MotHeader(
                body_size=(1 << 28),
                content_type=MotContentType.IMAGE_PNG
            )

    def test_add_parameter(self):
        """Test adding parameters to header."""
        header = MotHeader(
            body_size=100,
            content_type=MotContentType.IMAGE_JFIF
        )

        header.add_parameter(MotParameterType.CONTENT_NAME, b'image.jpg')
        assert len(header.parameters) == 1
        assert header.parameters[0].param_id == MotParameterType.CONTENT_NAME
        assert header.parameters[0].data == b'image.jpg'

    def test_set_content_name(self):
        """Test setting content name."""
        header = MotHeader(
            body_size=100,
            content_type=MotContentType.IMAGE_PNG
        )

        header.set_content_name('test.png')

        assert len(header.parameters) == 1
        assert header.parameters[0].param_id == MotParameterType.CONTENT_NAME
        assert header.parameters[0].data == b'test.png'

    def test_set_slideshow_parameters(self):
        """Test setting slideshow parameters."""
        header = MotHeader(
            body_size=50000,
            content_type=MotContentType.IMAGE_JFIF
        )

        header.set_content_name('album.jpg')
        header.set_category_id(0x01)  # Album art
        header.set_slide_id(5)
        header.set_click_through_url('https://example.com')
        header.set_trigger_time(0)

        assert len(header.parameters) == 5

    def test_encode_basic_header(self):
        """Test encoding basic header without parameters."""
        header = MotHeader(
            body_size=1024,
            content_type=MotContentType.IMAGE_JFIF,
            content_subtype=0x00
        )

        encoded = header.encode()

        # Should be 7 bytes for header without parameters
        assert len(encoded) == 7

        # Extension flag should be 0 (no parameters)
        assert (encoded[6] & 0x01) == 0

    def test_encode_header_with_parameters(self):
        """Test encoding header with parameters."""
        header = MotHeader(
            body_size=2048,
            content_type=MotContentType.IMAGE_PNG
        )

        header.set_content_name('test.png')

        encoded = header.encode()

        # Should be > 7 bytes (header + parameter)
        assert len(encoded) > 7

        # Extension flag should be 1 (has parameters)
        assert (encoded[6] & 0x01) == 1

    def test_decode_basic_header(self):
        """Test decoding basic header."""
        # Create and encode
        original = MotHeader(
            body_size=5000,
            content_type=MotContentType.IMAGE_JFIF,
            content_subtype=0x05
        )

        encoded = original.encode()

        # Decode
        decoded = MotHeader.decode(encoded)

        assert decoded.body_size == original.body_size
        assert decoded.content_type == original.content_type
        assert decoded.content_subtype == original.content_subtype
        assert len(decoded.parameters) == 0

    def test_decode_header_with_parameters(self):
        """Test decoding header with parameters."""
        # Create and encode
        original = MotHeader(
            body_size=10000,
            content_type=MotContentType.IMAGE_PNG
        )

        original.set_content_name('image.png')
        original.set_category_id(0x02)  # Logo

        encoded = original.encode()

        # Decode
        decoded = MotHeader.decode(encoded)

        assert decoded.body_size == original.body_size
        assert decoded.content_type == original.content_type
        assert len(decoded.parameters) == 2

        # Check parameters
        assert decoded.parameters[0].param_id == MotParameterType.CONTENT_NAME
        assert decoded.parameters[0].data == b'image.png'
        assert decoded.parameters[1].param_id == MotParameterType.CATEGORY_ID
        assert decoded.parameters[1].data == b'\x02'

    def test_encode_decode_roundtrip(self):
        """Test that encode/decode is reversible."""
        original = MotHeader(
            body_size=25000,
            content_type=MotContentType.IMAGE_JFIF
        )

        original.set_content_name('album_art.jpg')
        original.set_category_id(0x01)
        original.set_slide_id(10)

        # Encode and decode
        encoded = original.encode()
        decoded = MotHeader.decode(encoded)

        # Verify
        assert decoded.body_size == original.body_size
        assert decoded.content_type == original.content_type
        assert len(decoded.parameters) == len(original.parameters)
