"""
Unit tests for MOT Object.

Tests per ETSI TS 101 499.
"""

import pytest
import tempfile
import os
from pathlib import Path

from dabmux.mot.object import MotObject
from dabmux.mot.header import MotHeader, MotContentType


class TestMotObject:
    """Tests for MotObject."""

    def test_object_creation(self):
        """Test creating a MOT object."""
        header = MotHeader(
            body_size=1024,
            content_type=MotContentType.IMAGE_JFIF
        )
        body = b'x' * 1024

        obj = MotObject(
            header=header,
            body=body,
            transport_id=1
        )

        assert obj.header == header
        assert obj.body == body
        assert obj.transport_id == 1
        assert obj.enabled is True
        assert obj.priority == 1

    def test_priority_validation(self):
        """Test priority validation (1-8)."""
        header = MotHeader(body_size=100, content_type=MotContentType.TEXT)
        body = b'test'

        # Valid priorities
        for priority in range(1, 9):
            obj = MotObject(header=header, body=body, priority=priority)
            assert obj.priority == priority

        # Invalid: too low
        with pytest.raises(ValueError):
            MotObject(header=header, body=body, priority=0)

        # Invalid: too high
        with pytest.raises(ValueError):
            MotObject(header=header, body=body, priority=9)

    def test_total_size(self):
        """Test total_size property."""
        header = MotHeader(
            body_size=500,
            content_type=MotContentType.IMAGE_PNG
        )
        header.set_content_name('test.png')

        body = b'x' * 500

        obj = MotObject(header=header, body=body)

        # Total size should be header + body
        header_size = len(header.encode())
        assert obj.total_size == header_size + 500

    def test_encode_header(self):
        """Test encoding just the header."""
        header = MotHeader(
            body_size=100,
            content_type=MotContentType.IMAGE_JFIF
        )
        body = b'y' * 100

        obj = MotObject(header=header, body=body)

        encoded_header = obj.encode_header()
        assert isinstance(encoded_header, bytes)
        assert len(encoded_header) >= 7  # Minimum header size

    def test_encode_body(self):
        """Test encoding the body."""
        header = MotHeader(
            body_size=50,
            content_type=MotContentType.TEXT
        )
        body = b'This is test data'

        obj = MotObject(header=header, body=body)

        encoded_body = obj.encode_body()
        assert encoded_body == body

    def test_create_slideshow_jpeg(self):
        """Test creating slideshow object from JPEG."""
        # Create temporary JPEG file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            image_data = b'\xFF\xD8\xFF\xE0' + b'x' * 1000  # JPEG magic + data
            f.write(image_data)
            temp_path = f.name

        try:
            obj = MotObject.create_slideshow(
                image_path=temp_path,
                category='album_art',
                slide_id=5,
                priority=2
            )

            assert obj.header.content_type == MotContentType.IMAGE_JFIF
            assert obj.body == image_data
            assert obj.priority == 2
            assert obj.enabled is True

        finally:
            os.unlink(temp_path)

    def test_create_slideshow_png(self):
        """Test creating slideshow object from PNG."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image_data = b'\x89PNG\r\n\x1a\n' + b'x' * 500  # PNG magic + data
            f.write(image_data)
            temp_path = f.name

        try:
            obj = MotObject.create_slideshow(
                image_path=temp_path,
                category='logo',
                slide_id=1
            )

            assert obj.header.content_type == MotContentType.IMAGE_PNG
            assert obj.body == image_data

        finally:
            os.unlink(temp_path)

    def test_create_slideshow_with_url(self):
        """Test creating slideshow with click-through URL."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'test')
            temp_path = f.name

        try:
            obj = MotObject.create_slideshow(
                image_path=temp_path,
                category='album_art',
                slide_id=1,
                url='https://example.com/album'
            )

            # Check that URL parameter was added
            assert any(
                p.param_id == 0x28  # CLICK_THROUGH_URL
                for p in obj.header.parameters
            )

        finally:
            os.unlink(temp_path)

    def test_from_file_with_metadata(self):
        """Test creating object from file with YAML metadata."""
        # Create temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create image file
            image_path = Path(tmpdir) / 'test.jpg'
            with open(image_path, 'wb') as f:
                f.write(b'\xFF\xD8\xFF\xE0' + b'x' * 2000)

            # Create metadata file
            metadata_path = Path(tmpdir) / 'test.jpg.yaml'
            with open(metadata_path, 'w') as f:
                f.write("""
content_type: 'image/jpeg'
category: 'album_art'
slide_id: 10
url: 'https://example.com'
enabled: true
priority: 3
""")

            # Create object
            obj = MotObject.from_file(
                file_path=str(image_path),
                transport_id=5
            )

            assert obj.header.content_type == MotContentType.IMAGE_JFIF
            assert len(obj.body) == 2004
            assert obj.transport_id == 5
            assert obj.enabled is True
            assert obj.priority == 3

    def test_from_file_missing_file(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            MotObject.from_file('/nonexistent/file.jpg')

    def test_from_file_missing_metadata(self):
        """Test error when metadata doesn't exist."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'test')
            temp_path = f.name

        try:
            # No .yaml file exists
            with pytest.raises(FileNotFoundError):
                MotObject.from_file(temp_path)

        finally:
            os.unlink(temp_path)

    def test_parse_content_type_mime(self):
        """Test parsing MIME types to MotContentType."""
        parse = MotObject._parse_content_type

        assert parse('image/jpeg') == MotContentType.IMAGE_JFIF
        assert parse('image/png') == MotContentType.IMAGE_PNG
        assert parse('image/gif') == MotContentType.IMAGE_GIF
        assert parse('text/html') == MotContentType.HTML
        assert parse('application/epg-si') == MotContentType.EPG_SI

    def test_parse_category(self):
        """Test parsing category strings."""
        parse = MotObject._parse_category

        assert parse('album_art') == 0x01
        assert parse('logo') == 0x02
        assert parse('programme_info') == 0x03

        # Integer formats
        assert parse('0x01') == 0x01
        assert parse('2') == 0x02

    def test_body_size_mismatch_correction(self):
        """Test that body size mismatch is corrected."""
        # Create header with wrong body size
        header = MotHeader(
            body_size=100,  # Wrong!
            content_type=MotContentType.TEXT
        )

        body = b'x' * 200  # Actual size

        obj = MotObject(header=header, body=body)

        # Should be auto-corrected
        assert obj.header.body_size == 200
