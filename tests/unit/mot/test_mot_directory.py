"""
Unit tests for MOT Directory.

Tests per ETSI TS 101 499 Section 6.3.
"""

import pytest
from dabmux.mot.directory import MotDirectory, DirectoryEntry
from dabmux.mot.object import MotObject
from dabmux.mot.header import MotHeader, MotContentType


class TestDirectoryEntry:
    """Tests for DirectoryEntry."""

    def test_entry_creation(self):
        """Test creating a directory entry."""
        entry = DirectoryEntry(transport_id=5, size=10000)

        assert entry.transport_id == 5
        assert entry.size == 10000

    def test_entry_encode(self):
        """Test encoding directory entry."""
        entry = DirectoryEntry(transport_id=10, size=50000)

        encoded = entry.encode()

        # Should be 6 bytes (2 for ID, 4 for size)
        assert len(encoded) == 6

        # Verify values
        assert int.from_bytes(encoded[0:2], 'big') == 10
        assert int.from_bytes(encoded[2:6], 'big') == 50000

    def test_entry_decode(self):
        """Test decoding directory entry."""
        # Create and encode
        original = DirectoryEntry(transport_id=15, size=75000)
        encoded = original.encode()

        # Decode
        decoded = DirectoryEntry.decode(encoded)

        assert decoded.transport_id == original.transport_id
        assert decoded.size == original.size

    def test_entry_roundtrip(self):
        """Test encode/decode roundtrip."""
        original = DirectoryEntry(transport_id=100, size=123456)

        encoded = original.encode()
        decoded = DirectoryEntry.decode(encoded)

        assert decoded.transport_id == original.transport_id
        assert decoded.size == original.size


class TestMotDirectory:
    """Tests for MotDirectory."""

    def test_directory_creation(self):
        """Test creating empty directory."""
        directory = MotDirectory()

        assert len(directory.objects) == 0
        assert directory.transport_id == 0

    def test_add_object(self):
        """Test adding objects to directory."""
        directory = MotDirectory()

        # Create test objects
        obj1 = self._create_test_object(transport_id=1, size=1000)
        obj2 = self._create_test_object(transport_id=2, size=2000)

        directory.add_object(obj1)
        directory.add_object(obj2)

        assert len(directory.objects) == 2
        assert directory.objects[0] == obj1
        assert directory.objects[1] == obj2

    def test_remove_object(self):
        """Test removing objects from directory."""
        directory = MotDirectory()

        obj1 = self._create_test_object(transport_id=1, size=1000)
        obj2 = self._create_test_object(transport_id=2, size=2000)

        directory.add_object(obj1)
        directory.add_object(obj2)

        # Remove obj1
        result = directory.remove_object(transport_id=1)

        assert result is True
        assert len(directory.objects) == 1
        assert directory.objects[0] == obj2

        # Try to remove non-existent
        result = directory.remove_object(transport_id=99)
        assert result is False

    def test_get_object(self):
        """Test getting object by transport ID."""
        directory = MotDirectory()

        obj1 = self._create_test_object(transport_id=5, size=500)
        obj2 = self._create_test_object(transport_id=10, size=1000)

        directory.add_object(obj1)
        directory.add_object(obj2)

        # Get existing
        found = directory.get_object(transport_id=5)
        assert found == obj1

        # Get non-existent
        not_found = directory.get_object(transport_id=99)
        assert not_found is None

    def test_get_entry_list(self):
        """Test getting list of directory entries."""
        directory = MotDirectory()

        obj1 = self._create_test_object(transport_id=1, size=1000)
        obj2 = self._create_test_object(transport_id=2, size=2000)

        directory.add_object(obj1)
        directory.add_object(obj2)

        entries = directory.get_entry_list()

        assert len(entries) == 2
        assert entries[0].transport_id == 1
        assert entries[0].size == obj1.total_size
        assert entries[1].transport_id == 2
        assert entries[1].size == obj2.total_size

    def test_encode_directory_object(self):
        """Test encoding directory as MOT object."""
        directory = MotDirectory()

        # Add some objects
        obj1 = self._create_test_object(transport_id=1, size=5000)
        obj2 = self._create_test_object(transport_id=2, size=10000)

        directory.add_object(obj1)
        directory.add_object(obj2)

        # Encode directory
        dir_obj = directory.encode_directory_object()

        # Verify directory object
        assert dir_obj.transport_id == 0
        assert dir_obj.header.content_type == MotContentType.MOT_TRANSPORT
        assert dir_obj.priority == 8  # High priority

        # Body should contain 2 entries (12 bytes total)
        assert len(dir_obj.body) == 12  # 2 entries * 6 bytes each

    def test_decode_directory_object(self):
        """Test decoding directory from MOT object."""
        # Create directory and encode
        original_dir = MotDirectory()

        obj1 = self._create_test_object(transport_id=3, size=3000)
        obj2 = self._create_test_object(transport_id=4, size=4000)

        original_dir.add_object(obj1)
        original_dir.add_object(obj2)

        dir_obj = original_dir.encode_directory_object()

        # Decode
        decoded_dir = MotDirectory.decode_directory_object(dir_obj)

        assert decoded_dir.transport_id == 0

        # Note: decode only creates structure, not full objects
        # Just verify it doesn't crash and basic structure is correct

    def test_validate_success(self):
        """Test validation of valid directory."""
        directory = MotDirectory()

        obj1 = self._create_test_object(transport_id=1, size=1000)
        obj2 = self._create_test_object(transport_id=2, size=2000)

        directory.add_object(obj1)
        directory.add_object(obj2)

        assert directory.validate() is True

    def test_validate_wrong_directory_id(self):
        """Test validation fails for wrong directory transport ID."""
        directory = MotDirectory(transport_id=5)  # Should be 0

        assert directory.validate() is False

    def test_validate_duplicate_ids(self):
        """Test validation fails for duplicate transport IDs."""
        directory = MotDirectory()

        obj1 = self._create_test_object(transport_id=1, size=1000)
        obj2 = self._create_test_object(transport_id=1, size=2000)  # Duplicate!

        directory.add_object(obj1)
        directory.add_object(obj2)

        assert directory.validate() is False

    def test_validate_zero_object_id(self):
        """Test validation fails for object with transport_id=0."""
        directory = MotDirectory()

        obj = self._create_test_object(transport_id=0, size=1000)  # Reserved!

        directory.add_object(obj)

        assert directory.validate() is False

    @staticmethod
    def _create_test_object(transport_id: int, size: int) -> MotObject:
        """Helper to create test MOT object."""
        header = MotHeader(
            body_size=size,
            content_type=MotContentType.IMAGE_JFIF
        )

        body = b'x' * size

        return MotObject(
            header=header,
            body=body,
            transport_id=transport_id
        )
