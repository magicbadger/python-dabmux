"""
MOT Slideshow management per ETSI TS 101 499.

Manages slideshow objects, validates images, and handles carousel rotation.
"""

import os
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import structlog

from dabmux.mot.object import MotObject
from dabmux.mot.header import MotContentType

logger = structlog.get_logger(__name__)


# Image format magic bytes
IMAGE_SIGNATURES = {
    MotContentType.IMAGE_JFIF: [
        b'\xFF\xD8\xFF\xE0',  # JFIF
        b'\xFF\xD8\xFF\xE1',  # EXIF
        b'\xFF\xD8\xFF\xDB',  # JPEG
    ],
    MotContentType.IMAGE_PNG: [b'\x89PNG\r\n\x1a\n'],
    MotContentType.IMAGE_GIF: [b'GIF87a', b'GIF89a'],
    MotContentType.IMAGE_BMP: [b'BM'],
}


@dataclass
class ImageInfo:
    """Information about an image file."""
    path: Path
    content_type: MotContentType
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    valid: bool = True
    error: Optional[str] = None


class SlideshowManager:
    """
    Manages slideshow objects and carousel.

    Handles image validation, format detection, and object creation
    for MOT slideshow transmission.
    """

    def __init__(self, max_object_size: int = 51200):
        """
        Initialize slideshow manager.

        Args:
            max_object_size: Maximum object size in bytes (default 50 KB)
        """
        self.max_object_size = max_object_size
        self.objects: Dict[int, MotObject] = {}  # transport_id -> object
        self.next_transport_id = 1

    def add_image(self, path: str, metadata: Optional[Dict] = None,
                  transport_id: Optional[int] = None) -> Optional[MotObject]:
        """
        Add image to slideshow.

        Args:
            path: Path to image file
            metadata: Optional metadata dict (category, slide_id, url, etc.)
            transport_id: Optional transport ID (auto-assigned if None)

        Returns:
            MotObject if successful, None if validation fails
        """
        image_path = Path(path)

        # Validate image
        info = self.validate_image(str(image_path))
        if not info.valid:
            logger.error(
                "Image validation failed",
                path=str(image_path),
                error=info.error
            )
            return None

        # Prepare metadata
        if metadata is None:
            metadata = {}

        # Auto-assign transport ID
        if transport_id is None:
            transport_id = self._get_next_transport_id()

        # Set defaults
        category = metadata.get('category', 'album_art')
        slide_id = metadata.get('slide_id', transport_id)
        url = metadata.get('url', None)
        priority = metadata.get('priority', 1)

        # Create MOT object
        try:
            obj = MotObject.create_slideshow(
                image_path=str(image_path),
                category=category,
                slide_id=slide_id,
                url=url,
                priority=priority,
                transport_id=transport_id
            )

            self.objects[transport_id] = obj

            logger.info(
                "Added slideshow image",
                path=image_path.name,
                transport_id=transport_id,
                size=info.size_bytes,
                format=info.content_type.name
            )

            return obj

        except Exception as e:
            logger.error(
                "Failed to create slideshow object",
                path=str(image_path),
                error=str(e)
            )
            return None

    def remove_image(self, transport_id: int) -> bool:
        """
        Remove image from slideshow.

        Args:
            transport_id: Transport ID to remove

        Returns:
            True if removed, False if not found
        """
        if transport_id in self.objects:
            del self.objects[transport_id]
            logger.info("Removed slideshow image", transport_id=transport_id)
            return True
        return False

    def get_image(self, transport_id: int) -> Optional[MotObject]:
        """
        Get image by transport ID.

        Args:
            transport_id: Transport ID

        Returns:
            MotObject if found, None otherwise
        """
        return self.objects.get(transport_id)

    def get_all_images(self) -> List[MotObject]:
        """
        Get all images in carousel.

        Returns:
            List of MotObject instances
        """
        return list(self.objects.values())

    def validate_image(self, path: str) -> ImageInfo:
        """
        Validate image file.

        Checks:
        - File exists
        - File is readable
        - Format is supported (JPEG, PNG, GIF, BMP)
        - Size is within limits
        - Magic bytes match format

        Args:
            path: Path to image file

        Returns:
            ImageInfo with validation results
        """
        image_path = Path(path)

        # Check existence
        if not image_path.exists():
            return ImageInfo(
                path=image_path,
                content_type=MotContentType.GENERAL_DATA,
                size_bytes=0,
                valid=False,
                error="File not found"
            )

        # Check file size
        size_bytes = image_path.stat().st_size

        if size_bytes == 0:
            return ImageInfo(
                path=image_path,
                content_type=MotContentType.GENERAL_DATA,
                size_bytes=0,
                valid=False,
                error="File is empty"
            )

        if size_bytes > self.max_object_size:
            return ImageInfo(
                path=image_path,
                content_type=MotContentType.GENERAL_DATA,
                size_bytes=size_bytes,
                valid=False,
                error=f"File too large ({size_bytes} > {self.max_object_size})"
            )

        # Read file header
        try:
            with open(image_path, 'rb') as f:
                header = f.read(16)  # Read first 16 bytes for magic detection
        except Exception as e:
            return ImageInfo(
                path=image_path,
                content_type=MotContentType.GENERAL_DATA,
                size_bytes=size_bytes,
                valid=False,
                error=f"Cannot read file: {e}"
            )

        # Detect format from magic bytes
        content_type = self._detect_format(header)

        if content_type == MotContentType.GENERAL_DATA:
            return ImageInfo(
                path=image_path,
                content_type=content_type,
                size_bytes=size_bytes,
                valid=False,
                error="Unknown or unsupported image format"
            )

        # Try to extract dimensions
        width, height = self._extract_dimensions(image_path, content_type)

        return ImageInfo(
            path=image_path,
            content_type=content_type,
            size_bytes=size_bytes,
            width=width,
            height=height,
            valid=True
        )

    def _detect_format(self, header: bytes) -> MotContentType:
        """
        Detect image format from magic bytes.

        Args:
            header: First bytes of file

        Returns:
            MotContentType enum
        """
        for content_type, signatures in IMAGE_SIGNATURES.items():
            for signature in signatures:
                if header.startswith(signature):
                    return content_type

        return MotContentType.GENERAL_DATA

    def _extract_dimensions(self, path: Path, content_type: MotContentType) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract image dimensions.

        Args:
            path: Path to image file
            content_type: Detected content type

        Returns:
            Tuple of (width, height) or (None, None) if cannot extract
        """
        try:
            with open(path, 'rb') as f:
                data = f.read()

            if content_type == MotContentType.IMAGE_PNG:
                return self._extract_png_dimensions(data)
            elif content_type == MotContentType.IMAGE_JFIF:
                return self._extract_jpeg_dimensions(data)
            elif content_type == MotContentType.IMAGE_GIF:
                return self._extract_gif_dimensions(data)
            elif content_type == MotContentType.IMAGE_BMP:
                return self._extract_bmp_dimensions(data)

        except Exception as e:
            logger.debug("Could not extract dimensions", path=str(path), error=str(e))

        return None, None

    @staticmethod
    def _extract_png_dimensions(data: bytes) -> Tuple[int, int]:
        """
        Extract PNG dimensions.

        PNG IHDR chunk at offset 16, width/height are 4 bytes each.

        Args:
            data: PNG file data

        Returns:
            (width, height)
        """
        if len(data) < 24:
            raise ValueError("PNG data too short")

        # IHDR chunk starts at byte 12 (after PNG signature + chunk length)
        # Width: bytes 16-19 (big-endian)
        # Height: bytes 20-23 (big-endian)
        width = struct.unpack('>I', data[16:20])[0]
        height = struct.unpack('>I', data[20:24])[0]

        return width, height

    @staticmethod
    def _extract_jpeg_dimensions(data: bytes) -> Tuple[int, int]:
        """
        Extract JPEG dimensions from SOF marker.

        Args:
            data: JPEG file data

        Returns:
            (width, height)
        """
        offset = 2  # Skip initial 0xFFD8

        while offset < len(data) - 9:
            # Look for marker
            if data[offset] != 0xFF:
                offset += 1
                continue

            marker = data[offset + 1]

            # SOF markers (Start Of Frame)
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                # SOF structure:
                # 0xFF, marker, length (2 bytes), precision (1 byte),
                # height (2 bytes), width (2 bytes)
                height = struct.unpack('>H', data[offset + 5:offset + 7])[0]
                width = struct.unpack('>H', data[offset + 7:offset + 9])[0]
                return width, height

            # Skip to next marker
            if marker == 0xD8 or marker == 0xD9:  # SOI or EOI
                offset += 2
            else:
                # Read segment length
                if offset + 3 < len(data):
                    length = struct.unpack('>H', data[offset + 2:offset + 4])[0]
                    offset += 2 + length
                else:
                    break

        raise ValueError("Could not find SOF marker in JPEG")

    @staticmethod
    def _extract_gif_dimensions(data: bytes) -> Tuple[int, int]:
        """
        Extract GIF dimensions.

        GIF header: signature (6 bytes) + width (2) + height (2)

        Args:
            data: GIF file data

        Returns:
            (width, height)
        """
        if len(data) < 10:
            raise ValueError("GIF data too short")

        # Width at bytes 6-7 (little-endian)
        # Height at bytes 8-9 (little-endian)
        width = struct.unpack('<H', data[6:8])[0]
        height = struct.unpack('<H', data[8:10])[0]

        return width, height

    @staticmethod
    def _extract_bmp_dimensions(data: bytes) -> Tuple[int, int]:
        """
        Extract BMP dimensions.

        BMP header: 14 bytes file header + 40 bytes DIB header
        Width/height at offsets 18-21 and 22-25

        Args:
            data: BMP file data

        Returns:
            (width, height)
        """
        if len(data) < 26:
            raise ValueError("BMP data too short")

        # Width at bytes 18-21 (little-endian, signed)
        # Height at bytes 22-25 (little-endian, signed)
        width = struct.unpack('<i', data[18:22])[0]
        height = struct.unpack('<i', data[22:26])[0]

        return abs(width), abs(height)

    def _get_next_transport_id(self) -> int:
        """
        Get next available transport ID.

        Returns:
            Transport ID (1-65535, avoiding 0 which is reserved for directory)
        """
        while self.next_transport_id in self.objects:
            self.next_transport_id += 1
            if self.next_transport_id > 65535:
                self.next_transport_id = 1

        transport_id = self.next_transport_id
        self.next_transport_id += 1

        return transport_id

    def clear(self) -> None:
        """Clear all images from carousel."""
        self.objects.clear()
        self.next_transport_id = 1
        logger.info("Cleared slideshow carousel")

    def get_statistics(self) -> Dict:
        """
        Get carousel statistics.

        Returns:
            Dictionary with statistics
        """
        if not self.objects:
            return {
                'total_images': 0,
                'total_size_bytes': 0,
                'average_size_bytes': 0,
                'formats': {}
            }

        total_size = sum(obj.header.body_size for obj in self.objects.values())
        formats = {}

        for obj in self.objects.values():
            format_name = obj.header.content_type.name
            formats[format_name] = formats.get(format_name, 0) + 1

        return {
            'total_images': len(self.objects),
            'total_size_bytes': total_size,
            'average_size_bytes': total_size // len(self.objects),
            'formats': formats,
            'transport_ids': sorted(self.objects.keys())
        }
