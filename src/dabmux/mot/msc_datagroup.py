"""
MSC Data Group encoding per ETSI EN 300 401 Section 5.3.3.

MSC (Main Service Channel) data groups transport MOT objects
in the subchannel data stream.
"""

import struct
from dataclasses import dataclass
from typing import List, Optional
import structlog

from dabmux.mot.object import MotObject
from dabmux.pad.crc import crc16_ccitt_pad

logger = structlog.get_logger(__name__)


@dataclass
class MscDataGroup:
    """
    MSC Data Group per EN 300 401 Section 5.3.3.

    Similar to PAD data groups but used in MSC (subchannel) for larger objects.

    Structure:
    - Extension flag (1 bit): 0 = no session header, 1 = session header present
    - CRC flag (1 bit): 0 = no CRC, 1 = CRC present
    - Segment flag (1 bit): 0 = last segment, 1 = more segments follow
    - User Access field (5 bits): Application type
    - Data Group Length (variable, 1 or 2 bytes)
    - Session Header (optional)
    - Data field (variable)
    - CRC (2 bytes if CRC flag = 1)
    """
    extension: bool = False
    crc_flag: bool = True
    segment: bool = False  # True if more segments follow
    user_access: int = 0x001  # 0x001 for MOT
    data: bytes = b''
    segment_number: int = 0
    last_segment: bool = False

    def encode(self) -> bytes:
        """
        Encode data group to bytes.

        Returns:
            Encoded data group bytes including header, data, and CRC
        """
        # Header byte (1 byte)
        # Bit 7: Extension flag
        # Bit 6: CRC flag
        # Bit 5: Segment flag
        # Bits 4-0: User Access field
        header = 0
        if self.extension:
            header |= 0x80
        if self.crc_flag:
            header |= 0x40
        if self.segment:
            header |= 0x20
        header |= (self.user_access & 0x1F)

        # Data group length (1 or 2 bytes)
        # Length includes data field only (not header or CRC)
        data_len = len(self.data)
        length_bytes = self._encode_length(data_len)

        # Build data group (header + length + data)
        result = bytes([header]) + length_bytes + self.data

        # Add CRC if enabled
        if self.crc_flag:
            # CRC calculated over everything except the CRC itself
            crc = crc16_ccitt_pad(result)
            result += struct.pack('>H', crc)  # Big-endian 16-bit CRC

        return result

    def _encode_length(self, length: int) -> bytes:
        """
        Encode length field (variable size: 1 or 2 bytes).

        If length < 128: 1 byte (bit 7 = 0, bits 6-0 = length)
        If length >= 128: 2 bytes (first byte bit 7 = 1, 15 bits for length)

        Args:
            length: Data field length

        Returns:
            Encoded length bytes
        """
        if length < 128:
            # Short form: 1 byte
            return bytes([length])
        else:
            # Long form: 2 bytes
            byte1 = 0x80 | ((length >> 8) & 0x7F)
            byte2 = length & 0xFF
            return bytes([byte1, byte2])

    @classmethod
    def decode_length(cls, data: bytes, offset: int = 0) -> tuple[int, int]:
        """
        Decode length field from data.

        Args:
            data: Data bytes
            offset: Offset to start of length field

        Returns:
            Tuple of (length_value, bytes_consumed)
        """
        if offset >= len(data):
            return (0, 0)

        first_byte = data[offset]

        if first_byte & 0x80:
            # Long form: 2 bytes
            if offset + 1 >= len(data):
                return (0, 1)

            length = ((first_byte & 0x7F) << 8) | data[offset + 1]
            return (length, 2)
        else:
            # Short form: 1 byte
            return (first_byte & 0x7F, 1)


class MscDataGroupSegmenter:
    """
    Segments MOT objects into MSC data groups.

    Handles splitting large MOT objects (header + body) into
    multiple data groups that fit within packet size constraints.
    """

    def __init__(self, max_segment_size: int = 8188):
        """
        Initialize segmenter.

        Args:
            max_segment_size: Maximum data size per segment (default 8188 for packet mode)
        """
        self.max_segment_size = max_segment_size

    def segment_object(self, mot_object: MotObject) -> List[MscDataGroup]:
        """
        Segment MOT object into data groups.

        The object is split as follows:
        1. First segment: MOT header
        2. Subsequent segments: MOT body data

        Each segment is wrapped in an MSC data group with:
        - CRC protection
        - Segment flag (indicating more segments follow)
        - User access = 0x001 (MOT)

        Args:
            mot_object: MotObject to segment

        Returns:
            List of MscDataGroup instances
        """
        segments = []

        # Encode header and body
        header_bytes = mot_object.encode_header()
        body_bytes = mot_object.encode_body()

        # Segment 1: Header
        # Header goes in first segment
        header_segment = MscDataGroup(
            extension=False,
            crc_flag=True,
            segment=True,  # More segments follow (body)
            user_access=0x001,  # MOT
            data=header_bytes,
            segment_number=0,
            last_segment=False
        )
        segments.append(header_segment)

        # Segment body into chunks
        body_offset = 0
        segment_number = 1

        while body_offset < len(body_bytes):
            # Calculate chunk size
            chunk_size = min(self.max_segment_size, len(body_bytes) - body_offset)
            chunk_data = body_bytes[body_offset:body_offset + chunk_size]

            # Check if this is the last segment
            is_last = (body_offset + chunk_size) >= len(body_bytes)

            # Create data group for this chunk
            body_segment = MscDataGroup(
                extension=False,
                crc_flag=True,
                segment=not is_last,  # More segments follow if not last
                user_access=0x001,
                data=chunk_data,
                segment_number=segment_number,
                last_segment=is_last
            )
            segments.append(body_segment)

            body_offset += chunk_size
            segment_number += 1

        logger.info(
            "Segmented MOT object",
            transport_id=mot_object.transport_id,
            total_size=len(header_bytes) + len(body_bytes),
            segments=len(segments),
            header_size=len(header_bytes),
            body_size=len(body_bytes)
        )

        return segments

    def calculate_segment_count(self, mot_object: MotObject) -> int:
        """
        Calculate number of segments needed for object.

        Args:
            mot_object: MotObject to calculate for

        Returns:
            Number of segments required
        """
        header_size = len(mot_object.encode_header())
        body_size = mot_object.header.body_size

        # 1 segment for header
        header_segments = 1

        # Body segments
        body_segments = (body_size + self.max_segment_size - 1) // self.max_segment_size

        return header_segments + body_segments

    def estimate_transmission_time(self, mot_object: MotObject,
                                   bytes_per_frame: int = 96) -> float:
        """
        Estimate transmission time for object.

        Args:
            mot_object: MotObject to estimate
            bytes_per_frame: Bytes per ETI frame (depends on subchannel bitrate)

        Returns:
            Estimated time in seconds (at 24ms per frame for Mode I)
        """
        segments = self.segment_object(mot_object)

        # Calculate total encoded size
        total_bytes = sum(len(seg.encode()) for seg in segments)

        # Calculate frames needed
        frames_needed = (total_bytes + bytes_per_frame - 1) // bytes_per_frame

        # Time per frame (24ms for Mode I)
        frame_time_ms = 24

        return (frames_needed * frame_time_ms) / 1000.0


def segment_mot_object(mot_object: MotObject,
                      max_segment_size: int = 8188) -> List[MscDataGroup]:
    """
    Convenience function to segment a MOT object.

    Args:
        mot_object: MotObject to segment
        max_segment_size: Maximum segment size (default 8188)

    Returns:
        List of MscDataGroup instances
    """
    segmenter = MscDataGroupSegmenter(max_segment_size=max_segment_size)
    return segmenter.segment_object(mot_object)
