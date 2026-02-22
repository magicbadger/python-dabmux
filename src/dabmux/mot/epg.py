"""
EPG (Electronic Programme Guide) binary encoding per ETSI TS 102 371.

Provides encoding for Service Information (SI), Programme Information (PI),
Group Information (GI), and logo files for DAB EPG.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import IntEnum
import structlog

from dabmux.mot.object import MotObject
from dabmux.mot.header import MotHeader, MotContentType

logger = structlog.get_logger(__name__)


class EpgContentType(IntEnum):
    """EPG content types per TS 102 371."""
    SERVICE_INFO = 0x11  # SI file
    PROGRAMME_INFO = 0x12  # PI file
    GROUP_INFO = 0x13  # GI file
    PROGRAMME_LOGO = 0x14  # Logo file


class EpgScope(IntEnum):
    """EPG scope identifiers."""
    NOW = 0x00  # Current programme
    NEXT = 0x01  # Next programme
    NOW_AND_NEXT = 0x02  # Both current and next
    SCHEDULE = 0x03  # Full schedule


@dataclass
class EpgProgramme:
    """
    EPG Programme information.

    Represents a single programme in the schedule.
    """
    programme_id: int  # Unique ID for this programme
    start_time: datetime
    duration_seconds: int
    title: str
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    genre: Optional[int] = None  # Genre code
    parental_rating: Optional[int] = None
    broadcast_flag: int = 0x00
    recommended: bool = False


@dataclass
class EpgService:
    """
    EPG Service information.

    Represents metadata about a service and its programmes.
    """
    service_id: int  # DAB service ID
    service_name: str
    provider_name: Optional[str] = None
    programmes: List[EpgProgramme] = field(default_factory=list)
    logo_id: Optional[int] = None


@dataclass
class EpgGenre:
    """EPG Genre/Group information."""
    genre_id: int
    genre_name: str
    parent_genre_id: Optional[int] = None


class EpgEncoder:
    """
    EPG binary encoder per ETSI TS 102 371.

    Encodes Service Information (SI), Programme Information (PI),
    and Group Information (GI) files for DAB EPG transmission.
    """

    def __init__(self):
        """Initialize EPG encoder."""
        self.services: Dict[int, EpgService] = {}
        self.genres: Dict[int, EpgGenre] = {}

    def add_service(self, service: EpgService) -> None:
        """
        Add service to encoder.

        Args:
            service: EpgService instance
        """
        self.services[service.service_id] = service
        logger.debug("Added EPG service", service_id=service.service_id)

    def add_genre(self, genre: EpgGenre) -> None:
        """
        Add genre to encoder.

        Args:
            genre: EpgGenre instance
        """
        self.genres[genre.genre_id] = genre
        logger.debug("Added EPG genre", genre_id=genre.genre_id)

    def encode_service_info(self, service_id: int) -> bytes:
        """
        Encode Service Information (SI) file.

        SI contains metadata about the service and its current/next programmes.

        Per TS 102 371 Section 4.1.

        Args:
            service_id: Service ID to encode

        Returns:
            Binary SI data

        Raises:
            ValueError: If service not found
        """
        if service_id not in self.services:
            raise ValueError(f"Service {service_id} not found")

        service = self.services[service_id]

        # SI file structure (simplified):
        # - Header (version, service_id, scope)
        # - Service metadata (name, provider)
        # - Programme list (now/next or schedule)

        data = bytearray()

        # Header (8 bytes)
        data.append(0x01)  # Version
        data.append(EpgScope.SCHEDULE)  # Scope
        data.extend(struct.pack('>H', service_id))  # Service ID (16-bit)
        data.extend(struct.pack('>I', len(service.programmes)))  # Programme count

        # Service name (length-prefixed string)
        name_bytes = service.service_name.encode('utf-8')
        data.append(len(name_bytes))
        data.extend(name_bytes)

        # Provider name (optional)
        if service.provider_name:
            provider_bytes = service.provider_name.encode('utf-8')
            data.append(len(provider_bytes))
            data.extend(provider_bytes)
        else:
            data.append(0)  # No provider name

        # Logo ID (optional)
        if service.logo_id is not None:
            data.append(1)  # Has logo
            data.extend(struct.pack('>H', service.logo_id))
        else:
            data.append(0)  # No logo

        # Programme entries
        for programme in service.programmes:
            prog_data = self._encode_programme(programme)
            data.extend(prog_data)

        logger.info(
            "Encoded SI file",
            service_id=service_id,
            programmes=len(service.programmes),
            size=len(data)
        )

        return bytes(data)

    def encode_programme_info(self, programme: EpgProgramme) -> bytes:
        """
        Encode Programme Information (PI) file.

        PI contains detailed information about a single programme.

        Per TS 102 371 Section 4.2.

        Args:
            programme: EpgProgramme instance

        Returns:
            Binary PI data
        """
        data = bytearray()

        # Header
        data.append(0x01)  # Version
        data.extend(struct.pack('>I', programme.programme_id))

        # Programme data
        prog_data = self._encode_programme(programme, include_id=False)
        data.extend(prog_data)

        logger.info(
            "Encoded PI file",
            programme_id=programme.programme_id,
            title=programme.title,
            size=len(data)
        )

        return bytes(data)

    def encode_group_info(self) -> bytes:
        """
        Encode Group Information (GI) file.

        GI contains genre/category information for programme classification.

        Per TS 102 371 Section 4.3.

        Returns:
            Binary GI data
        """
        data = bytearray()

        # Header
        data.append(0x01)  # Version
        data.extend(struct.pack('>H', len(self.genres)))  # Genre count

        # Genre entries
        for genre in self.genres.values():
            # Genre ID (16-bit)
            data.extend(struct.pack('>H', genre.genre_id))

            # Genre name (length-prefixed)
            name_bytes = genre.genre_name.encode('utf-8')
            data.append(len(name_bytes))
            data.extend(name_bytes)

            # Parent genre ID (optional)
            if genre.parent_genre_id is not None:
                data.append(1)  # Has parent
                data.extend(struct.pack('>H', genre.parent_genre_id))
            else:
                data.append(0)  # No parent

        logger.info("Encoded GI file", genres=len(self.genres), size=len(data))

        return bytes(data)

    def _encode_programme(self, programme: EpgProgramme, include_id: bool = True) -> bytes:
        """
        Encode single programme entry.

        Args:
            programme: EpgProgramme instance
            include_id: Whether to include programme ID

        Returns:
            Binary programme data
        """
        data = bytearray()

        # Programme ID (optional)
        if include_id:
            data.extend(struct.pack('>I', programme.programme_id))

        # Start time (Unix timestamp, 32-bit)
        timestamp = int(programme.start_time.timestamp())
        data.extend(struct.pack('>I', timestamp))

        # Duration (seconds, 32-bit)
        data.extend(struct.pack('>I', programme.duration_seconds))

        # Title (length-prefixed UTF-8)
        title_bytes = programme.title.encode('utf-8')
        data.append(len(title_bytes))
        data.extend(title_bytes)

        # Short description (optional)
        if programme.short_description:
            short_bytes = programme.short_description.encode('utf-8')
            data.extend(struct.pack('>H', len(short_bytes)))
            data.extend(short_bytes)
        else:
            data.extend(struct.pack('>H', 0))

        # Long description (optional)
        if programme.long_description:
            long_bytes = programme.long_description.encode('utf-8')
            data.extend(struct.pack('>H', len(long_bytes)))
            data.extend(long_bytes)
        else:
            data.extend(struct.pack('>H', 0))

        # Genre (optional)
        if programme.genre is not None:
            data.append(1)  # Has genre
            data.extend(struct.pack('>H', programme.genre))
        else:
            data.append(0)  # No genre

        # Parental rating (optional)
        if programme.parental_rating is not None:
            data.append(1)  # Has rating
            data.append(programme.parental_rating)
        else:
            data.append(0)  # No rating

        # Flags
        flags = programme.broadcast_flag
        if programme.recommended:
            flags |= 0x80  # Recommended bit
        data.append(flags)

        return bytes(data)

    def create_si_object(self, service_id: int, transport_id: int,
                        priority: int = 1) -> MotObject:
        """
        Create MOT object for SI file.

        Args:
            service_id: Service ID
            transport_id: Transport ID for carousel
            priority: Transmission priority (1-8)

        Returns:
            MotObject containing SI data
        """
        si_data = self.encode_service_info(service_id)

        header = MotHeader(
            body_size=len(si_data),
            content_type=MotContentType.EPG_SI
        )

        # Add content name
        service = self.services[service_id]
        filename = f"si_{service_id:04X}.bin"
        header.set_content_name(filename)

        obj = MotObject(
            header=header,
            body=si_data,
            transport_id=transport_id,
            enabled=True,
            priority=priority
        )

        logger.info(
            "Created SI MOT object",
            service_id=service_id,
            transport_id=transport_id,
            size=len(si_data)
        )

        return obj

    def create_pi_object(self, programme: EpgProgramme, transport_id: int,
                        priority: int = 1) -> MotObject:
        """
        Create MOT object for PI file.

        Args:
            programme: EpgProgramme instance
            transport_id: Transport ID for carousel
            priority: Transmission priority (1-8)

        Returns:
            MotObject containing PI data
        """
        pi_data = self.encode_programme_info(programme)

        header = MotHeader(
            body_size=len(pi_data),
            content_type=MotContentType.EPG_PI
        )

        # Add content name
        filename = f"pi_{programme.programme_id:08X}.bin"
        header.set_content_name(filename)

        obj = MotObject(
            header=header,
            body=pi_data,
            transport_id=transport_id,
            enabled=True,
            priority=priority
        )

        logger.info(
            "Created PI MOT object",
            programme_id=programme.programme_id,
            transport_id=transport_id,
            size=len(pi_data)
        )

        return obj

    def create_gi_object(self, transport_id: int, priority: int = 1) -> MotObject:
        """
        Create MOT object for GI file.

        Args:
            transport_id: Transport ID for carousel
            priority: Transmission priority (1-8)

        Returns:
            MotObject containing GI data
        """
        gi_data = self.encode_group_info()

        header = MotHeader(
            body_size=len(gi_data),
            content_type=MotContentType.EPG_GI
        )

        header.set_content_name("gi.bin")

        obj = MotObject(
            header=header,
            body=gi_data,
            transport_id=transport_id,
            enabled=True,
            priority=priority
        )

        logger.info(
            "Created GI MOT object",
            transport_id=transport_id,
            genres=len(self.genres),
            size=len(gi_data)
        )

        return obj

    @classmethod
    def create_logo_object(cls, logo_path: str, logo_id: int,
                          transport_id: int, priority: int = 1) -> MotObject:
        """
        Create MOT object for programme/service logo.

        Args:
            logo_path: Path to logo image file
            logo_id: Logo identifier
            transport_id: Transport ID for carousel
            priority: Transmission priority (1-8)

        Returns:
            MotObject containing logo image
        """
        from pathlib import Path

        logo_path = Path(logo_path)

        if not logo_path.exists():
            raise FileNotFoundError(f"Logo not found: {logo_path}")

        # Detect logo format
        with open(logo_path, 'rb') as f:
            header_bytes = f.read(8)

        # Determine content type
        if header_bytes.startswith(b'\xFF\xD8\xFF'):
            content_type = MotContentType.IMAGE_JFIF
        elif header_bytes.startswith(b'\x89PNG'):
            content_type = MotContentType.IMAGE_PNG
        elif header_bytes.startswith(b'GIF'):
            content_type = MotContentType.IMAGE_GIF
        elif header_bytes.startswith(b'BM'):
            content_type = MotContentType.IMAGE_BMP
        else:
            content_type = MotContentType.GENERAL_DATA

        # Load logo data
        with open(logo_path, 'rb') as f:
            logo_data = f.read()

        # Create header
        header = MotHeader(
            body_size=len(logo_data),
            content_type=content_type
        )

        # Set content name with logo ID
        filename = f"logo_{logo_id:04X}{logo_path.suffix}"
        header.set_content_name(filename)

        # Add logo-specific parameters
        # CategoryID for logo (0x02)
        header.set_category_id(0x02)

        obj = MotObject(
            header=header,
            body=logo_data,
            transport_id=transport_id,
            enabled=True,
            priority=priority
        )

        logger.info(
            "Created logo MOT object",
            logo_id=logo_id,
            transport_id=transport_id,
            format=content_type.name,
            size=len(logo_data)
        )

        return obj
