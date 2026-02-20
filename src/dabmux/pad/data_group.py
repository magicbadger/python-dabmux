"""
PAD Data Group encoding.

Data groups are the transport mechanism for PAD data (DLS, MOT, etc.).
Structure defined in ETSI EN 300 401 Section 7.4.2.2
"""

import struct
from dataclasses import dataclass
from dabmux.pad.crc import crc16_ccitt_pad


@dataclass
class PADDataGroup:
    """
    PAD Data Group (ETSI EN 300 401, Section 7.4.2.2).

    Structure:
    - Extension flag (1 bit): 0 = no session header, 1 = session header present
    - CRC flag (1 bit): 0 = no CRC, 1 = CRC present
    - Segment flag (1 bit): 0 = last segment, 1 = more segments follow
    - User Access field (5 bits): Application type
    - Data Group Length (variable, 1 or 2 bytes)
    - Session Header (optional, if Extension flag = 1)
    - MSC Data Group header (4 bytes if present)
    - Data field (variable)
    - Padding (if needed to align)
    - CRC (2 bytes if CRC flag = 1)

    For DLS, we typically use:
    - Extension flag = 0 (no session header)
    - CRC flag = 1 (CRC present for reliability)
    - Segment flag = 1 (DLS uses segmentation)
    - User Access = 2 (DLS application type)
    """

    extension: bool = False
    crc_flag: bool = True
    segment: bool = True
    user_access: int = 2  # 2 = DLS
    data: bytes = b''

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
            # First byte: bit 7 = 1, bits 6-0 = upper 7 bits of length
            # Second byte: lower 8 bits of length
            # This gives 15-bit length (0-32767)
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
