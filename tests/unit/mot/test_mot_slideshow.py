"""
Unit tests for MOT Slideshow Manager.

Tests per ETSI TS 101 499 (MOT Slideshow).
"""

import pytest
import tempfile
from pathlib import Path

from dabmux.mot.slideshow import SlideshowManager, ImageInfo
from dabmux.mot.header import MotContentType


class TestSlideshowManager:
    """Tests for SlideshowManager."""

    def test_manager_creation(self):
        """Test creating slideshow manager."""
        manager = SlideshowManager()

        assert manager.max_object_size == 51200  # 50 KB default
        assert len(manager.objects) == 0
        assert manager.next_transport_id == 1

    def test_manager_custom_size_limit(self):
        """Test creating manager with custom size limit."""
        manager = SlideshowManager(max_object_size=100000)

        assert manager.max_object_size == 100000

    def test_add_jpeg_image(self):
        """Test adding JPEG image."""
        manager = SlideshowManager()

        # Create temporary JPEG
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            # JPEG magic + minimal valid structure
            jpeg_data = b'\xFF\xD8\xFF\xE0\x00\x10JFIF' + b'\x00' * 100
            f.write(jpeg_data)
            temp_path = f.name

        try:
            obj = manager.add_image(temp_path)

            assert obj is not None
            assert obj.header.content_type == MotContentType.IMAGE_JFIF
            assert obj.transport_id == 1
            assert len(manager.objects) == 1

        finally:
            Path(temp_path).unlink()

    def test_add_png_image(self):
        """Test adding PNG image."""
        manager = SlideshowManager()

        # Create temporary PNG
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            # PNG signature + IHDR chunk
            png_data = (
                b'\x89PNG\r\n\x1a\n'  # PNG signature
                b'\x00\x00\x00\x0DIHDR'  # IHDR chunk
                b'\x00\x00\x01\x00'  # Width: 256
                b'\x00\x00\x00\x80'  # Height: 128
                b'\x08\x02\x00\x00\x00'  # Bit depth, color type, etc.
            ) + b'\x00' * 100
            f.write(png_data)
            temp_path = f.name

        try:
            obj = manager.add_image(temp_path)

            assert obj is not None
            assert obj.header.content_type == MotContentType.IMAGE_PNG

        finally:
            Path(temp_path).unlink()

    def test_add_image_with_metadata(self):
        """Test adding image with metadata."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            temp_path = f.name

        try:
            metadata = {
                'category': 'logo',
                'slide_id': 10,
                'url': 'https://example.com',
                'priority': 3
            }

            obj = manager.add_image(temp_path, metadata=metadata)

            assert obj is not None
            assert obj.priority == 3

        finally:
            Path(temp_path).unlink()

    def test_add_image_custom_transport_id(self):
        """Test adding image with custom transport ID."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            temp_path = f.name

        try:
            obj = manager.add_image(temp_path, transport_id=100)

            assert obj is not None
            assert obj.transport_id == 100
            assert 100 in manager.objects

        finally:
            Path(temp_path).unlink()

    def test_add_multiple_images(self):
        """Test adding multiple images."""
        manager = SlideshowManager()

        images = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
                images.append(f.name)

        try:
            objs = []
            for path in images:
                obj = manager.add_image(path)
                assert obj is not None
                objs.append(obj)

            assert len(manager.objects) == 3
            assert objs[0].transport_id == 1
            assert objs[1].transport_id == 2
            assert objs[2].transport_id == 3

        finally:
            for path in images:
                Path(path).unlink()

    def test_remove_image(self):
        """Test removing image."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            temp_path = f.name

        try:
            obj = manager.add_image(temp_path)
            transport_id = obj.transport_id

            # Remove
            result = manager.remove_image(transport_id)
            assert result is True
            assert len(manager.objects) == 0

            # Try to remove again
            result = manager.remove_image(transport_id)
            assert result is False

        finally:
            Path(temp_path).unlink()

    def test_get_image(self):
        """Test getting image by transport ID."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            temp_path = f.name

        try:
            obj = manager.add_image(temp_path)
            transport_id = obj.transport_id

            # Get existing
            found = manager.get_image(transport_id)
            assert found == obj

            # Get non-existent
            not_found = manager.get_image(9999)
            assert not_found is None

        finally:
            Path(temp_path).unlink()

    def test_get_all_images(self):
        """Test getting all images."""
        manager = SlideshowManager()

        images = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
                images.append(f.name)

        try:
            for path in images:
                manager.add_image(path)

            all_images = manager.get_all_images()
            assert len(all_images) == 3

        finally:
            for path in images:
                Path(path).unlink()

    def test_clear(self):
        """Test clearing carousel."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
            temp_path = f.name

        try:
            manager.add_image(temp_path)
            assert len(manager.objects) > 0

            manager.clear()
            assert len(manager.objects) == 0
            assert manager.next_transport_id == 1

        finally:
            Path(temp_path).unlink()


class TestImageValidation:
    """Tests for image validation."""

    def test_validate_jpeg(self):
        """Test validating JPEG image."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.valid is True
            assert info.content_type == MotContentType.IMAGE_JFIF
            assert info.size_bytes == 1004
            assert info.error is None

        finally:
            Path(temp_path).unlink()

    def test_validate_png(self):
        """Test validating PNG image."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
            f.write(png_data)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.valid is True
            assert info.content_type == MotContentType.IMAGE_PNG

        finally:
            Path(temp_path).unlink()

    def test_validate_gif(self):
        """Test validating GIF image."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as f:
            # GIF89a signature + minimal header
            gif_data = b'GIF89a\x10\x00\x10\x00' + b'\x00' * 100
            f.write(gif_data)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.valid is True
            assert info.content_type == MotContentType.IMAGE_GIF

        finally:
            Path(temp_path).unlink()

    def test_validate_bmp(self):
        """Test validating BMP image."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as f:
            # BMP signature + minimal header
            bmp_data = b'BM' + b'\x00' * 100
            f.write(bmp_data)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.valid is True
            assert info.content_type == MotContentType.IMAGE_BMP

        finally:
            Path(temp_path).unlink()

    def test_validate_missing_file(self):
        """Test validation of missing file."""
        manager = SlideshowManager()

        info = manager.validate_image('/nonexistent/file.jpg')

        assert info.valid is False
        assert info.error == "File not found"

    def test_validate_empty_file(self):
        """Test validation of empty file."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
            # File is empty

        try:
            info = manager.validate_image(temp_path)

            assert info.valid is False
            assert info.error == "File is empty"

        finally:
            Path(temp_path).unlink()

    def test_validate_file_too_large(self):
        """Test validation of oversized file."""
        manager = SlideshowManager(max_object_size=1000)

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            # Create file larger than limit
            f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 2000)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.valid is False
            assert "too large" in info.error.lower()

        finally:
            Path(temp_path).unlink()

    def test_validate_unknown_format(self):
        """Test validation of unknown format."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'This is not an image')
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.valid is False
            assert "unsupported" in info.error.lower()

        finally:
            Path(temp_path).unlink()


class TestDimensionExtraction:
    """Tests for image dimension extraction."""

    def test_png_dimensions(self):
        """Test extracting PNG dimensions."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            # PNG with 256x128 dimensions
            png_data = (
                b'\x89PNG\r\n\x1a\n'
                b'\x00\x00\x00\x0DIHDR'
                b'\x00\x00\x01\x00'  # Width: 256
                b'\x00\x00\x00\x80'  # Height: 128
                b'\x08\x02\x00\x00\x00'
            ) + b'\x00' * 100
            f.write(png_data)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.width == 256
            assert info.height == 128

        finally:
            Path(temp_path).unlink()

    def test_gif_dimensions(self):
        """Test extracting GIF dimensions."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as f:
            # GIF with 320x240 dimensions (little-endian)
            gif_data = (
                b'GIF89a'
                b'\x40\x01'  # Width: 320 (0x0140 little-endian)
                b'\xF0\x00'  # Height: 240 (0x00F0 little-endian)
            ) + b'\x00' * 100
            f.write(gif_data)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.width == 320
            assert info.height == 240

        finally:
            Path(temp_path).unlink()

    def test_bmp_dimensions(self):
        """Test extracting BMP dimensions."""
        manager = SlideshowManager()

        with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as f:
            # BMP with 640x480 dimensions
            import struct
            bmp_data = (
                b'BM' + b'\x00' * 12 +  # File header
                b'\x28\x00\x00\x00' +  # DIB header size
                struct.pack('<i', 640) +  # Width
                struct.pack('<i', 480) +  # Height
                b'\x00' * 100
            )
            f.write(bmp_data)
            temp_path = f.name

        try:
            info = manager.validate_image(temp_path)

            assert info.width == 640
            assert info.height == 480

        finally:
            Path(temp_path).unlink()


class TestStatistics:
    """Tests for carousel statistics."""

    def test_empty_statistics(self):
        """Test statistics for empty carousel."""
        manager = SlideshowManager()

        stats = manager.get_statistics()

        assert stats['total_images'] == 0
        assert stats['total_size_bytes'] == 0
        assert stats['average_size_bytes'] == 0
        assert stats['formats'] == {}

    def test_statistics_with_images(self):
        """Test statistics with multiple images."""
        manager = SlideshowManager()

        images = []
        # Add 2 JPEGs and 1 PNG
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000)
                images.append(f.name)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 500)
            images.append(f.name)

        try:
            for path in images:
                manager.add_image(path)

            stats = manager.get_statistics()

            assert stats['total_images'] == 3
            assert stats['total_size_bytes'] > 0
            assert 'IMAGE_JFIF' in stats['formats']
            assert stats['formats']['IMAGE_JFIF'] == 2
            assert 'IMAGE_PNG' in stats['formats']
            assert stats['formats']['IMAGE_PNG'] == 1
            assert len(stats['transport_ids']) == 3

        finally:
            for path in images:
                Path(path).unlink()
