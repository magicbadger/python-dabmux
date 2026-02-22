"""
Unit tests for MOT EPG encoding.

Tests per ETSI TS 102 371 (EPG Binary Encoding).
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from dabmux.mot.epg import (
    EpgEncoder, EpgProgramme, EpgService, EpgGenre,
    EpgContentType, EpgScope
)
from dabmux.mot.header import MotContentType


class TestEpgProgramme:
    """Tests for EpgProgramme dataclass."""

    def test_programme_creation(self):
        """Test creating a programme."""
        start_time = datetime(2026, 2, 22, 14, 0, 0)

        prog = EpgProgramme(
            programme_id=1,
            start_time=start_time,
            duration_seconds=3600,
            title="News Hour"
        )

        assert prog.programme_id == 1
        assert prog.start_time == start_time
        assert prog.duration_seconds == 3600
        assert prog.title == "News Hour"
        assert prog.short_description is None
        assert prog.genre is None

    def test_programme_with_full_metadata(self):
        """Test programme with all optional fields."""
        start_time = datetime(2026, 2, 22, 20, 0, 0)

        prog = EpgProgramme(
            programme_id=2,
            start_time=start_time,
            duration_seconds=7200,
            title="Movie Night",
            short_description="An exciting thriller",
            long_description="A gripping story about...",
            genre=0x10,  # Movie genre
            parental_rating=12,
            recommended=True
        )

        assert prog.short_description == "An exciting thriller"
        assert prog.long_description == "A gripping story about..."
        assert prog.genre == 0x10
        assert prog.parental_rating == 12
        assert prog.recommended is True


class TestEpgService:
    """Tests for EpgService dataclass."""

    def test_service_creation(self):
        """Test creating a service."""
        service = EpgService(
            service_id=0x5001,
            service_name="Test Radio"
        )

        assert service.service_id == 0x5001
        assert service.service_name == "Test Radio"
        assert len(service.programmes) == 0
        assert service.provider_name is None
        assert service.logo_id is None

    def test_service_with_programmes(self):
        """Test service with programmes."""
        start_time = datetime.now()

        prog1 = EpgProgramme(
            programme_id=1,
            start_time=start_time,
            duration_seconds=3600,
            title="Programme 1"
        )

        prog2 = EpgProgramme(
            programme_id=2,
            start_time=start_time + timedelta(hours=1),
            duration_seconds=1800,
            title="Programme 2"
        )

        service = EpgService(
            service_id=0x5001,
            service_name="Test Radio",
            provider_name="Test Provider",
            programmes=[prog1, prog2],
            logo_id=100
        )

        assert len(service.programmes) == 2
        assert service.provider_name == "Test Provider"
        assert service.logo_id == 100


class TestEpgGenre:
    """Tests for EpgGenre dataclass."""

    def test_genre_creation(self):
        """Test creating a genre."""
        genre = EpgGenre(
            genre_id=0x10,
            genre_name="Movies"
        )

        assert genre.genre_id == 0x10
        assert genre.genre_name == "Movies"
        assert genre.parent_genre_id is None

    def test_genre_with_parent(self):
        """Test genre with parent."""
        genre = EpgGenre(
            genre_id=0x11,
            genre_name="Action Movies",
            parent_genre_id=0x10
        )

        assert genre.parent_genre_id == 0x10


class TestEpgEncoder:
    """Tests for EpgEncoder."""

    def test_encoder_creation(self):
        """Test creating encoder."""
        encoder = EpgEncoder()

        assert len(encoder.services) == 0
        assert len(encoder.genres) == 0

    def test_add_service(self):
        """Test adding service to encoder."""
        encoder = EpgEncoder()

        service = EpgService(
            service_id=0x5001,
            service_name="Test Radio"
        )

        encoder.add_service(service)

        assert 0x5001 in encoder.services
        assert encoder.services[0x5001] == service

    def test_add_genre(self):
        """Test adding genre to encoder."""
        encoder = EpgEncoder()

        genre = EpgGenre(genre_id=0x10, genre_name="News")

        encoder.add_genre(genre)

        assert 0x10 in encoder.genres
        assert encoder.genres[0x10] == genre

    def test_encode_service_info(self):
        """Test encoding SI file."""
        encoder = EpgEncoder()

        # Create service with programmes
        start_time = datetime(2026, 2, 22, 14, 0, 0)

        prog1 = EpgProgramme(
            programme_id=1,
            start_time=start_time,
            duration_seconds=3600,
            title="News"
        )

        service = EpgService(
            service_id=0x5001,
            service_name="Test Radio",
            provider_name="Test Provider",
            programmes=[prog1]
        )

        encoder.add_service(service)

        # Encode SI
        si_data = encoder.encode_service_info(0x5001)

        assert isinstance(si_data, bytes)
        assert len(si_data) > 0

        # Check header
        assert si_data[0] == 0x01  # Version
        assert si_data[1] == EpgScope.SCHEDULE

    def test_encode_service_info_missing_service(self):
        """Test error when encoding non-existent service."""
        encoder = EpgEncoder()

        with pytest.raises(ValueError):
            encoder.encode_service_info(0x9999)

    def test_encode_programme_info(self):
        """Test encoding PI file."""
        encoder = EpgEncoder()

        start_time = datetime(2026, 2, 22, 20, 0, 0)

        prog = EpgProgramme(
            programme_id=100,
            start_time=start_time,
            duration_seconds=7200,
            title="Movie Night",
            short_description="An exciting thriller"
        )

        # Encode PI
        pi_data = encoder.encode_programme_info(prog)

        assert isinstance(pi_data, bytes)
        assert len(pi_data) > 0

        # Check header
        assert pi_data[0] == 0x01  # Version

    def test_encode_group_info(self):
        """Test encoding GI file."""
        encoder = EpgEncoder()

        # Add genres
        encoder.add_genre(EpgGenre(genre_id=0x10, genre_name="News"))
        encoder.add_genre(EpgGenre(genre_id=0x20, genre_name="Music"))
        encoder.add_genre(EpgGenre(genre_id=0x21, genre_name="Rock", parent_genre_id=0x20))

        # Encode GI
        gi_data = encoder.encode_group_info()

        assert isinstance(gi_data, bytes)
        assert len(gi_data) > 0

        # Check header
        assert gi_data[0] == 0x01  # Version
        # Genre count (16-bit big-endian)
        genre_count = (gi_data[1] << 8) | gi_data[2]
        assert genre_count == 3

    def test_create_si_object(self):
        """Test creating SI MOT object."""
        encoder = EpgEncoder()

        service = EpgService(
            service_id=0x5001,
            service_name="Test Radio"
        )

        encoder.add_service(service)

        # Create MOT object
        obj = encoder.create_si_object(
            service_id=0x5001,
            transport_id=10,
            priority=2
        )

        assert obj.transport_id == 10
        assert obj.priority == 2
        assert obj.header.content_type == MotContentType.EPG_SI
        assert obj.enabled is True

    def test_create_pi_object(self):
        """Test creating PI MOT object."""
        encoder = EpgEncoder()

        start_time = datetime.now()

        prog = EpgProgramme(
            programme_id=1,
            start_time=start_time,
            duration_seconds=3600,
            title="News Hour"
        )

        # Create MOT object
        obj = encoder.create_pi_object(
            programme=prog,
            transport_id=20,
            priority=1
        )

        assert obj.transport_id == 20
        assert obj.priority == 1
        assert obj.header.content_type == MotContentType.EPG_PI

    def test_create_gi_object(self):
        """Test creating GI MOT object."""
        encoder = EpgEncoder()

        encoder.add_genre(EpgGenre(genre_id=0x10, genre_name="News"))

        # Create MOT object
        obj = encoder.create_gi_object(transport_id=30, priority=3)

        assert obj.transport_id == 30
        assert obj.priority == 3
        assert obj.header.content_type == MotContentType.EPG_GI

    def test_create_logo_object_jpeg(self):
        """Test creating logo MOT object (JPEG)."""
        # Create temporary logo file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            logo_data = b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000
            f.write(logo_data)
            temp_path = f.name

        try:
            obj = EpgEncoder.create_logo_object(
                logo_path=temp_path,
                logo_id=100,
                transport_id=40,
                priority=2
            )

            assert obj.transport_id == 40
            assert obj.priority == 2
            assert obj.header.content_type == MotContentType.IMAGE_JFIF
            assert obj.body == logo_data

        finally:
            Path(temp_path).unlink()

    def test_create_logo_object_png(self):
        """Test creating logo MOT object (PNG)."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            logo_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 500
            f.write(logo_data)
            temp_path = f.name

        try:
            obj = EpgEncoder.create_logo_object(
                logo_path=temp_path,
                logo_id=101,
                transport_id=41
            )

            assert obj.header.content_type == MotContentType.IMAGE_PNG

        finally:
            Path(temp_path).unlink()

    def test_create_logo_object_missing_file(self):
        """Test error when logo file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            EpgEncoder.create_logo_object(
                logo_path='/nonexistent/logo.jpg',
                logo_id=100,
                transport_id=40
            )


class TestEpgEncoding:
    """Tests for EPG binary encoding."""

    def test_encode_programme_with_utf8(self):
        """Test encoding programme with UTF-8 text."""
        encoder = EpgEncoder()

        start_time = datetime.now()

        prog = EpgProgramme(
            programme_id=1,
            start_time=start_time,
            duration_seconds=3600,
            title="Émission spéciale"  # UTF-8 characters
        )

        pi_data = encoder.encode_programme_info(prog)

        # Should encode without error
        assert len(pi_data) > 0

    def test_encode_multiple_services(self):
        """Test encoding multiple services."""
        encoder = EpgEncoder()

        start_time = datetime.now()

        # Service 1
        service1 = EpgService(
            service_id=0x5001,
            service_name="Radio 1",
            programmes=[
                EpgProgramme(
                    programme_id=1,
                    start_time=start_time,
                    duration_seconds=3600,
                    title="News"
                )
            ]
        )

        # Service 2
        service2 = EpgService(
            service_id=0x5002,
            service_name="Radio 2",
            programmes=[
                EpgProgramme(
                    programme_id=2,
                    start_time=start_time,
                    duration_seconds=1800,
                    title="Music"
                )
            ]
        )

        encoder.add_service(service1)
        encoder.add_service(service2)

        # Encode both
        si1_data = encoder.encode_service_info(0x5001)
        si2_data = encoder.encode_service_info(0x5002)

        assert len(si1_data) > 0
        assert len(si2_data) > 0
        # Different services should have different data
        assert si1_data != si2_data

    def test_encode_programme_schedule(self):
        """Test encoding programme schedule."""
        encoder = EpgEncoder()

        start_time = datetime(2026, 2, 22, 6, 0, 0)

        # Create day schedule
        programmes = []
        for hour in range(24):
            prog = EpgProgramme(
                programme_id=hour,
                start_time=start_time + timedelta(hours=hour),
                duration_seconds=3600,
                title=f"Programme {hour}"
            )
            programmes.append(prog)

        service = EpgService(
            service_id=0x5001,
            service_name="24h Radio",
            programmes=programmes
        )

        encoder.add_service(service)

        # Encode
        si_data = encoder.encode_service_info(0x5001)

        # Should contain all 24 programmes
        assert len(si_data) > 100  # Reasonable size for schedule
