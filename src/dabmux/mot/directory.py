"""
MOT Directory encoding per ETSI TS 101 499 Section 6.3.

The MOT directory provides an index of all objects in the carousel,
allowing receivers to efficiently acquire objects.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional
import structlog

from dabmux.mot.object import MotObject
from dabmux.mot.header import MotHeader, MotContentType

logger = structlog.get_logger(__name__)


@dataclass
class DirectoryEntry:
    """
    Single entry in MOT directory.

    Per TS 101 499, each entry contains:
    - Transport ID
    - Object size (header + body)
    """
    transport_id: int
    size: int  # Total size (header + body)

    def encode(self) -> bytes:
        """
        Encode directory entry.

        Format:
        - Transport ID (16 bits)
        - Size (32 bits)

        Returns:
            Encoded entry (6 bytes)
        """
        return struct.pack('>HI', self.transport_id, self.size)

    @classmethod
    def decode(cls, data: bytes) -> 'DirectoryEntry':
        """
        Decode directory entry.

        Args:
            data: Encoded entry (6 bytes)

        Returns:
            DirectoryEntry instance
        """
        if len(data) < 6:
            raise ValueError(f"Entry too short: {len(data)} bytes (need 6)")

        transport_id, size = struct.unpack('>HI', data[:6])

        return cls(transport_id=transport_id, size=size)


@dataclass
class MotDirectory:
    """
    MOT Directory per ETSI TS 101 499 Section 6.3.

    The directory is itself a MOT object that contains an index
    of all objects in the carousel.
    """
    objects: List[MotObject] = field(default_factory=list)
    transport_id: int = 0  # Directory has TransportID 0

    def add_object(self, obj: MotObject) -> None:
        """
        Add object to directory.

        Args:
            obj: MotObject to add
        """
        self.objects.append(obj)

    def remove_object(self, transport_id: int) -> bool:
        """
        Remove object from directory by transport ID.

        Args:
            transport_id: Transport ID to remove

        Returns:
            True if object was removed, False if not found
        """
        original_len = len(self.objects)
        self.objects = [obj for obj in self.objects if obj.transport_id != transport_id]
        return len(self.objects) < original_len

    def get_object(self, transport_id: int) -> Optional[MotObject]:
        """
        Get object by transport ID.

        Args:
            transport_id: Transport ID to find

        Returns:
            MotObject if found, None otherwise
        """
        for obj in self.objects:
            if obj.transport_id == transport_id:
                return obj
        return None

    def encode_directory_object(self) -> MotObject:
        """
        Encode directory as a MOT object.

        The directory is transmitted as a special MOT object with:
        - Transport ID = 0
        - Content type = MOT_TRANSPORT (0x60)
        - Body = list of directory entries

        Returns:
            MotObject representing the directory
        """
        # Create directory entries
        entries = []
        for obj in self.objects:
            entry = DirectoryEntry(
                transport_id=obj.transport_id,
                size=obj.total_size
            )
            entries.append(entry)

        # Encode entries to body
        body_data = b''
        for entry in entries:
            body_data += entry.encode()

        # Create header
        header = MotHeader(
            body_size=len(body_data),
            content_type=MotContentType.MOT_TRANSPORT,
            content_subtype=0x00
        )

        # Directory doesn't need content name or other parameters

        # Create directory object
        directory_obj = MotObject(
            header=header,
            body=body_data,
            transport_id=self.transport_id,
            enabled=True,
            priority=8  # High priority for directory
        )

        logger.debug(
            "Encoded MOT directory",
            num_objects=len(self.objects),
            directory_size=len(body_data)
        )

        return directory_obj

    @classmethod
    def decode_directory_object(cls, directory_obj: MotObject) -> 'MotDirectory':
        """
        Decode directory from MOT object.

        Args:
            directory_obj: MotObject containing directory data

        Returns:
            MotDirectory instance

        Raises:
            ValueError: If object is not a valid directory
        """
        if directory_obj.header.content_type != MotContentType.MOT_TRANSPORT:
            raise ValueError(
                f"Not a directory object: content_type={directory_obj.header.content_type}"
            )

        # Decode entries from body
        body = directory_obj.body
        offset = 0
        entries = []

        while offset + 6 <= len(body):
            entry = DirectoryEntry.decode(body[offset:offset + 6])
            entries.append(entry)
            offset += 6

        if offset != len(body):
            logger.warning(
                "Directory has trailing bytes",
                expected=offset,
                actual=len(body)
            )

        # Create directory (without actual objects, just structure)
        directory = cls(transport_id=directory_obj.transport_id)

        logger.debug(
            "Decoded MOT directory",
            num_entries=len(entries),
            directory_size=len(body)
        )

        return directory

    def get_entry_list(self) -> List[DirectoryEntry]:
        """
        Get list of directory entries.

        Returns:
            List of DirectoryEntry instances
        """
        entries = []
        for obj in self.objects:
            entry = DirectoryEntry(
                transport_id=obj.transport_id,
                size=obj.total_size
            )
            entries.append(entry)
        return entries

    def validate(self) -> bool:
        """
        Validate directory structure.

        Checks:
        - No duplicate transport IDs
        - All objects have valid IDs
        - Directory transport ID is 0

        Returns:
            True if valid, False otherwise
        """
        if self.transport_id != 0:
            logger.error("Directory must have transport_id=0", id=self.transport_id)
            return False

        # Check for duplicate IDs
        ids = [obj.transport_id for obj in self.objects]
        if len(ids) != len(set(ids)):
            logger.error("Duplicate transport IDs found", ids=ids)
            return False

        # Check for valid IDs (non-zero)
        if 0 in ids:
            logger.error("Object has transport_id=0 (reserved for directory)")
            return False

        return True
