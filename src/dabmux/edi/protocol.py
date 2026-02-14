"""
EDI protocol structures.

This module implements TAG items, AF packets, and related structures
for the EDI (Ensemble Distribution Interface) protocol.
"""
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from dabmux.utils.crc import crc16

# EDI constants
EDI_EPOCH_UNIX = 946684800  # 2000-01-01 00:00:00 UTC
AF_SYNC = b"AF"
AF_HEADER_VERSION = 0x10  # Major=1, Minor=0
AF_PT_TAG = ord('T')


class TagItem(ABC):
    """
    Abstract base class for EDI TAG items.

    TAG items have the structure:
    - Name: 4 bytes (ASCII)
    - Length: 4 bytes (value length in BITS, big-endian)
    - Value: variable length data
    """

    @abstractmethod
    def get_name(self) -> bytes:
        """Get the 4-byte TAG name."""
        pass

    @abstractmethod
    def get_value(self) -> bytes:
        """Get the TAG value bytes."""
        pass

    def assemble(self) -> bytes:
        """
        Assemble TAG item into bytes.

        Returns:
            Complete TAG item (name + length + value)
        """
        name = self.get_name()
        value = self.get_value()

        # Length is in BITS
        length_bits = len(value) * 8

        # Pack: name(4) + length(4, big-endian) + value
        return name + struct.pack('>I', length_bits) + value


@dataclass
class TagStarPTR(TagItem):
    """
    *ptr TAG: Protocol Type and Revision.

    Identifies the protocol used (e.g., "DETI" for DAB ETI).
    """
    protocol: str = "DETI"
    major: int = 0
    minor: int = 0

    def get_name(self) -> bytes:
        return b"*ptr"

    def get_value(self) -> bytes:
        """
        Assemble *ptr value.

        Structure:
        - Protocol: 4 bytes (ASCII, e.g., "DETI")
        - Major: 2 bytes (big-endian)
        - Minor: 2 bytes (big-endian)
        """
        protocol_bytes = self.protocol.encode('ascii')[:4].ljust(4, b'\x00')
        return protocol_bytes + struct.pack('>HH', self.major, self.minor)


@dataclass
class TagDETI(TagItem):
    """
    deti TAG: DAB ETI Management.

    Contains ETI frame header information and optional timestamp/FIC data.
    """
    # Frame counter (modulo 5000)
    dlfc: int = 0

    # ETI header fields
    stat: int = 0xFF  # Status (0xFF = no error)
    mid: int = 1      # Mode ID (1=TM-I, 2=TM-II, 3=TM-III, 0=TM-IV)
    fp: int = 0       # Frame phase (0-7)
    mnsc: int = 0     # MNSC (16 bits)

    # Optional fields flags
    atstf: bool = False  # Timestamp present
    ficf: bool = False   # FIC present
    rfudf: bool = False  # RFUD present

    # Timestamp fields (if atstf=True)
    utco: int = 0           # TAI-UTC offset - 32
    seconds: int = 0        # Seconds since 2000-01-01
    tsta: int = 0xFFFFFF    # 24-bit timestamp (0xFFFFFF = invalid)

    # FIC data (if ficf=True)
    fic_data: bytes = b""

    # RFUD (if rfudf=True)
    rfud: int = 0

    # Reserved fields
    rfa: int = 0
    rfu: int = 0

    def get_name(self) -> bytes:
        return b"deti"

    def get_value(self) -> bytes:
        """
        Assemble deti value.

        Structure:
        - FCT/FCTH header: 2 bytes
        - ETI header: 4 bytes
        - ATST: optional (8 bytes if atstf=1)
        - FIC: optional (96/128 bytes if ficf=1)
        - RFUD: optional (3 bytes if rfudf=1)
        """
        value = bytearray()

        # FCT/FCTH header (2 bytes)
        fct = self.dlfc % 250
        fcth = self.dlfc // 250
        header = fct | (fcth << 8) | (int(self.rfudf) << 13) | \
                 (int(self.ficf) << 14) | (int(self.atstf) << 15)
        value.extend(struct.pack('<H', header))

        # ETI header (4 bytes)
        eti_header = self.mnsc | (self.rfu << 16) | (self.rfa << 17) | \
                     (self.fp << 19) | (self.mid << 22) | (self.stat << 24)
        value.extend(struct.pack('<I', eti_header))

        # ATST (optional, 8 bytes)
        if self.atstf:
            value.append(self.utco & 0xFF)
            value.extend(struct.pack('>I', self.seconds))
            value.extend(struct.pack('>I', self.tsta)[1:])  # 3 bytes (24-bit)

        # FIC (optional)
        if self.ficf and self.fic_data:
            value.extend(self.fic_data)

        # RFUD (optional, 3 bytes)
        if self.rfudf:
            value.extend(struct.pack('>I', self.rfud)[1:])  # 3 bytes (24-bit)

        return bytes(value)


@dataclass
class TagESTn(TagItem):
    """
    estN TAG: ETI Sub-Channel Stream.

    Contains MST data for a specific subchannel.
    """
    id: int           # Subchannel index (1-based)
    scid: int         # Sub-channel ID (0-63)
    sad: int          # Sub-channel start address (0-1023)
    tpl: int          # Time Profile Level (0-63)
    mst_data: bytes   # MST payload data
    rfa: int = 0      # Reserved

    def get_name(self) -> bytes:
        """Get TAG name (e.g., b"est1", b"est2", ...)."""
        return f"est{self.id}".encode('ascii')

    def get_value(self) -> bytes:
        """
        Assemble estN value.

        Structure:
        - SSTC: 3 bytes (scid, sad, tpl, rfa)
        - MST Data: variable length
        """
        # SSTC (3 bytes, 24 bits total)
        # Bits: scid(6) | sad(10) | tpl(6) | rfa(2)
        sstc = ((self.scid & 0x3F) << 18) | \
               ((self.sad & 0x3FF) << 8) | \
               ((self.tpl & 0x3F) << 2) | \
               (self.rfa & 0x03)

        value = struct.pack('>I', sstc)[1:]  # 3 bytes (24-bit)
        value += self.mst_data

        return value


@dataclass
class TagPacket:
    """
    TAG Packet: Collection of TAG items.

    Contains multiple TAG items with optional padding for alignment.
    """
    tag_items: List[TagItem] = field(default_factory=list)
    alignment: int = 8  # Byte alignment (0 = no padding)

    def assemble(self) -> bytes:
        """
        Assemble TAG packet.

        Returns:
            Concatenated TAG items with alignment padding
        """
        data = bytearray()

        # Assemble all TAG items
        for tag in self.tag_items:
            data.extend(tag.assemble())

        # Apply alignment padding
        if self.alignment > 0:
            padding_needed = (self.alignment - (len(data) % self.alignment)) % self.alignment
            data.extend(b'\x00' * padding_needed)

        return bytes(data)


@dataclass
class AFPacket:
    """
    AF Packet: Application Framing packet.

    Wraps TAG packets with framing header and CRC.
    """
    seq: int           # Sequence number (16-bit, wraps at 0xFFFF)
    payload: bytes     # TAG packet data

    def assemble(self) -> bytes:
        """
        Assemble AF packet.

        Structure:
        - SYNC: 2 bytes = "AF"
        - LEN: 4 bytes (payload length, big-endian)
        - SEQ: 2 bytes (sequence number, big-endian)
        - AR_CF: 1 byte (version | CRC flag)
        - PT: 1 byte = 'T'
        - Payload: TAG packet data
        - CRC: 2 bytes (CRC-16 over header + payload)
        """
        # Build header (10 bytes total)
        header = bytearray()
        header.extend(AF_SYNC)                                    # SYNC (2 bytes)
        header.extend(struct.pack('>I', len(self.payload)))      # LEN (4 bytes)
        header.extend(struct.pack('>H', self.seq & 0xFFFF))      # SEQ (2 bytes)
        header.append(AF_HEADER_VERSION | 0x80)                  # AR_CF (1 byte, CRC=1)
        header.append(AF_PT_TAG)                                 # PT (1 byte)

        # Combine header + payload
        packet_data = bytes(header) + self.payload

        # Calculate CRC over header + payload
        crc_value = crc16(packet_data)

        # Append CRC (big-endian)
        packet_data += struct.pack('>H', crc_value)

        return packet_data

    @classmethod
    def parse(cls, data: bytes) -> Optional['AFPacket']:
        """
        Parse AF packet from bytes.

        Args:
            data: AF packet bytes

        Returns:
            Parsed AFPacket or None if invalid
        """
        if len(data) < 12:  # Minimum: 10-byte header + 2-byte CRC
            return None

        # Check SYNC
        if data[:2] != AF_SYNC:
            return None

        # Parse header
        payload_len = struct.unpack('>I', data[2:6])[0]
        seq = struct.unpack('>H', data[6:8])[0]
        ar_cf = data[8]
        pt = data[9]

        # Verify PT
        if pt != AF_PT_TAG:
            return None

        # Check length
        if len(data) < 10 + payload_len + 2:
            return None

        # Extract payload and CRC
        payload = data[10:10 + payload_len]
        crc_received = struct.unpack('>H', data[10 + payload_len:10 + payload_len + 2])[0]

        # Verify CRC (if CRC flag is set)
        if ar_cf & 0x80:
            crc_calculated = crc16(data[:10 + payload_len])
            if crc_calculated != crc_received:
                return None

        return cls(seq=seq, payload=payload)
