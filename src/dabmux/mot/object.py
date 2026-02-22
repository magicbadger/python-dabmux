"""
MOT Object encoding per ETSI TS 101 499.

A MOT object consists of a header (metadata) and body (actual file data).
Objects can be created from files with accompanying YAML metadata.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import structlog

from dabmux.mot.header import MotHeader, MotContentType, MotParameterType

logger = structlog.get_logger(__name__)


@dataclass
class MotObject:
    """
    Complete MOT object (header + body).

    Per ETSI TS 101 499, a MOT object contains:
    - Header: Metadata about the object
    - Body: Actual data (image, EPG file, etc.)
    - Transport ID: Unique identifier for carousel
    """
    header: MotHeader
    body: bytes
    transport_id: int = 0
    enabled: bool = True
    priority: int = 1  # 1-8, higher = more frequent transmission

    def __post_init__(self):
        """Validate object fields."""
        if self.priority < 1 or self.priority > 8:
            raise ValueError(f"Priority {self.priority} out of range (1-8)")

        # Verify header body size matches actual body
        if self.header.body_size != len(self.body):
            logger.warning(
                "Header body size mismatch",
                header_size=self.header.body_size,
                actual_size=len(self.body)
            )
            # Update header to match
            self.header.body_size = len(self.body)

    @property
    def total_size(self) -> int:
        """Total object size (header + body) in bytes."""
        header_bytes = self.header.encode()
        return len(header_bytes) + len(self.body)

    def encode_header(self) -> bytes:
        """Encode just the header."""
        return self.header.encode()

    def encode_body(self) -> bytes:
        """Return the body bytes."""
        return self.body

    @classmethod
    def from_file(cls, file_path: str, metadata_path: Optional[str] = None,
                  transport_id: int = 0) -> 'MotObject':
        """
        Create MOT object from file and metadata.

        Args:
            file_path: Path to data file (image, EPG file, etc.)
            metadata_path: Path to YAML metadata file (defaults to file_path + '.yaml')
            transport_id: Transport ID for carousel

        Returns:
            MotObject instance

        Raises:
            FileNotFoundError: If file or metadata doesn't exist
            ValueError: If metadata is invalid
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Default metadata path
        if metadata_path is None:
            metadata_path = Path(str(file_path) + '.yaml')
        else:
            metadata_path = Path(metadata_path)

        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found: {metadata_path}")

        # Load metadata
        with open(metadata_path, 'r') as f:
            metadata = yaml.safe_load(f)

        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid metadata in {metadata_path}")

        # Load file data
        with open(file_path, 'rb') as f:
            body_data = f.read()

        # Parse metadata and create header
        header = cls._create_header_from_metadata(
            metadata=metadata,
            body_size=len(body_data),
            default_name=file_path.name
        )

        # Get transport_id from metadata, fallback to parameter
        tid = metadata.get('transport_id', transport_id)

        # Create object
        obj = cls(
            header=header,
            body=body_data,
            transport_id=tid,
            enabled=metadata.get('enabled', True),
            priority=metadata.get('priority', 1)
        )

        logger.info(
            "Created MOT object from file",
            file=str(file_path),
            size=len(body_data),
            content_type=header.content_type.name,
            priority=obj.priority
        )

        return obj

    @staticmethod
    def _create_header_from_metadata(metadata: Dict[str, Any], body_size: int,
                                      default_name: str) -> MotHeader:
        """
        Create MOT header from metadata dictionary.

        Args:
            metadata: Metadata from YAML
            body_size: Size of body data
            default_name: Default content name (filename)

        Returns:
            MotHeader instance
        """
        # Parse content type
        content_type_str = metadata.get('content_type', 'application/octet-stream')
        content_type = MotObject._parse_content_type(content_type_str)

        # Create header
        header = MotHeader(
            body_size=body_size,
            content_type=content_type,
            content_subtype=metadata.get('content_subtype', 0)
        )

        # Add content name
        content_name = metadata.get('content_name', default_name)
        header.set_content_name(content_name)

        # Add slideshow parameters
        if 'category' in metadata:
            category_id = MotObject._parse_category(metadata['category'])
            header.set_category_id(category_id)
        elif 'category_id' in metadata:
            header.set_category_id(metadata['category_id'])

        if 'slide_id' in metadata:
            header.set_slide_id(metadata['slide_id'])

        if 'url' in metadata:
            header.set_click_through_url(metadata['url'])

        if 'trigger_time' in metadata:
            header.set_trigger_time(metadata['trigger_time'])

        # Add EPG parameters
        if 'epg_profile' in metadata:
            header.add_parameter(
                MotParameterType.EPG_PROFILE,
                bytes([metadata['epg_profile']])
            )

        if 'epg_version' in metadata:
            header.add_parameter(
                MotParameterType.EPG_VERSION,
                bytes([metadata['epg_version']])
            )

        return header

    @staticmethod
    def _parse_content_type(content_type_str: str) -> MotContentType:
        """
        Parse content type string to MotContentType enum.

        Args:
            content_type_str: MIME type or MOT type name

        Returns:
            MotContentType enum value
        """
        # Map MIME types to MOT content types
        mime_map = {
            'image/jpeg': MotContentType.IMAGE_JFIF,
            'image/jpg': MotContentType.IMAGE_JFIF,
            'image/png': MotContentType.IMAGE_PNG,
            'image/gif': MotContentType.IMAGE_GIF,
            'image/bmp': MotContentType.IMAGE_BMP,
            'text/html': MotContentType.HTML,
            'text/plain': MotContentType.TEXT,
            'application/epg-si': MotContentType.EPG_SI,
            'application/epg-pi': MotContentType.EPG_PI,
            'application/epg-gi': MotContentType.EPG_GI,
        }

        content_type_lower = content_type_str.lower()

        # Try MIME type mapping
        if content_type_lower in mime_map:
            return mime_map[content_type_lower]

        # Try direct enum name
        try:
            return MotContentType[content_type_str.upper()]
        except KeyError:
            pass

        # Default to general data
        logger.warning(
            "Unknown content type, using GENERAL_DATA",
            content_type=content_type_str
        )
        return MotContentType.GENERAL_DATA

    @staticmethod
    def _parse_category(category_str: str) -> int:
        """
        Parse category string to CategoryID value.

        Args:
            category_str: Category name

        Returns:
            Category ID (0x01-0x20)
        """
        category_map = {
            'album_art': 0x01,
            'album': 0x01,
            'cover_art': 0x01,
            'logo': 0x02,
            'station_logo': 0x02,
            'programme_info': 0x03,
            'text': 0x10,
            'html': 0x20,
        }

        category_lower = category_str.lower()

        if category_lower in category_map:
            return category_map[category_lower]

        # Try parsing as integer
        try:
            cat_id = int(category_str, 0)  # Support 0x prefix
            if 0x01 <= cat_id <= 0x20:
                return cat_id
        except ValueError:
            pass

        logger.warning(
            "Unknown category, using album_art",
            category=category_str
        )
        return 0x01  # Default to album art

    @classmethod
    def create_slideshow(cls, image_path: str, category: str = 'album_art',
                        slide_id: int = 0, url: Optional[str] = None,
                        priority: int = 1, transport_id: int = 0) -> 'MotObject':
        """
        Convenience method to create slideshow object without metadata file.

        Args:
            image_path: Path to image file
            category: Category ('album_art', 'logo', etc.)
            slide_id: Slide identifier
            url: Optional click-through URL
            priority: Transmission priority (1-8)
            transport_id: Transport ID

        Returns:
            MotObject instance
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Detect content type from extension
        ext_map = {
            '.jpg': MotContentType.IMAGE_JFIF,
            '.jpeg': MotContentType.IMAGE_JFIF,
            '.png': MotContentType.IMAGE_PNG,
            '.gif': MotContentType.IMAGE_GIF,
            '.bmp': MotContentType.IMAGE_BMP,
        }

        ext = image_path.suffix.lower()
        content_type = ext_map.get(ext, MotContentType.GENERAL_DATA)

        # Load image
        with open(image_path, 'rb') as f:
            body_data = f.read()

        # Create header
        header = MotHeader(
            body_size=len(body_data),
            content_type=content_type
        )

        header.set_content_name(image_path.name)
        header.set_category_id(cls._parse_category(category))
        header.set_slide_id(slide_id)

        if url:
            header.set_click_through_url(url)

        return cls(
            header=header,
            body=body_data,
            transport_id=transport_id,
            enabled=True,
            priority=priority
        )
