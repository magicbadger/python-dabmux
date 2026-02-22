"""
MSC Packet encoding per ETSI EN 300 401 Section 5.3.2.

MSC packets transport data groups in packet mode subchannels.
"""

import struct
from dataclasses import dataclass
from typing import List, Optional
import structlog

from dabmux.mot.msc_datagroup import MscDataGroup

logger = structlog.get_logger(__name__)


@dataclass
class MscPacket:
    """
    MSC Packet per EN 300 401 Section 5.3.2.

    Packet structure:
    - Header (3 bytes):
      - Packet address (10 bits)
      - Useful data length (13 bits)
      - Continuity index (2 bits)
      - First flag (1 bit)
      - Last flag (1 bit)
      - Padding (1 bit)
    - Data field (variable, 0-8188 bytes)
    """
    address: int  # 10-bit packet address (0-1023)
    useful_data_length: int  # 13-bit length (0-8191)
    continuity_index: int  # 2-bit counter (0-3)
    first: bool  # First packet of data group
    last: bool  # Last packet of data group
    data: bytes = b''

    def __post_init__(self):
        """Validate packet fields."""
        if self.address < 0 or self.address > 1023:
            raise ValueError(f"Address {self.address} out of range (0-1023)")

        if self.useful_data_length < 0 or self.useful_data_length > 8191:
            raise ValueError(f"Length {self.useful_data_length} out of range (0-8191)")

        if self.continuity_index < 0 or self.continuity_index > 3:
            raise ValueError(f"Continuity index {self.continuity_index} out of range (0-3)")

        if len(self.data) > 8188:
            raise ValueError(f"Data size {len(self.data)} exceeds maximum 8188 bytes")

    def encode(self) -> bytes:
        """
        Encode packet to bytes.

        Header structure (3 bytes, 24 bits):
        - Bits 23-14: Packet address (10 bits)
        - Bits 13-1: Useful data length (13 bits)
        - Bits 0: Padding indicator (1 bit, always 0)

        Additional byte (1 byte):
        - Bits 7-6: Continuity index (2 bits)
        - Bit 5: First flag (1 bit)
        - Bit 4: Last flag (1 bit)
        - Bits 3-0: Reserved (4 bits, set to 0)

        Actually, per EN 300 401 Section 5.3.2.2:
        Header is 3 bytes total containing all fields.

        Returns:
            Encoded packet bytes
        """
        # Pack header (3 bytes = 24 bits)
        # Bits 23-14: Address (10 bits)
        # Bits 13-1: Useful data length (13 bits)
        # Bit 0: Padding indicator (1 bit, always 0 for us)

        header_value = (self.address << 14) | (self.useful_data_length << 1) | 0

        # Convert to 3 bytes (big-endian)
        header_bytes = struct.pack('>I', header_value)[1:]  # Take last 3 bytes

        # Build packet data field with continuity/flags
        # These are embedded in the data field per EN 300 401

        # For now, we'll use a simplified approach:
        # Byte 0 of data field contains: CI (2 bits) + First (1) + Last (1) + reserved (4)
        ci_flags = (self.continuity_index << 6) | (int(self.first) << 5) | (int(self.last) << 4)

        # Full packet: header + [CI/flags byte] + actual data
        packet_data = bytes([ci_flags]) + self.data

        # Pad to useful_data_length if needed
        if len(packet_data) < self.useful_data_length:
            packet_data += b'\x00' * (self.useful_data_length - len(packet_data))

        return header_bytes + packet_data

    @classmethod
    def decode(cls, data: bytes) -> 'MscPacket':
        """
        Decode packet from bytes.

        Args:
            data: Encoded packet bytes (minimum 3 bytes header)

        Returns:
            MscPacket instance

        Raises:
            ValueError: If data is too short or invalid
        """
        if len(data) < 3:
            raise ValueError(f"Packet data too short: {len(data)} bytes (minimum 3)")

        # Decode header (3 bytes)
        header_value = struct.unpack('>I', b'\x00' + data[0:3])[0]

        # Extract fields
        address = (header_value >> 14) & 0x3FF  # 10 bits
        useful_data_length = (header_value >> 1) & 0x1FFF  # 13 bits
        padding = header_value & 0x01  # 1 bit

        # Extract CI and flags from first data byte
        if len(data) > 3:
            ci_flags = data[3]
            continuity_index = (ci_flags >> 6) & 0x03
            first = bool((ci_flags >> 5) & 0x01)
            last = bool((ci_flags >> 4) & 0x01)

            # Actual data starts at byte 4
            packet_data = data[4:4 + useful_data_length - 1] if useful_data_length > 1 else b''
        else:
            continuity_index = 0
            first = False
            last = False
            packet_data = b''

        return cls(
            address=address,
            useful_data_length=useful_data_length,
            continuity_index=continuity_index,
            first=first,
            last=last,
            data=packet_data
        )


class MscPacketizer:
    """
    Packetizes MSC data groups into packets.

    Handles splitting data groups into packets that fit within
    subchannel capacity, managing continuity index and first/last flags.
    """

    def __init__(self, address: int = 0, max_packet_size: int = 96):
        """
        Initialize packetizer.

        Args:
            address: Packet address (0-1023)
            max_packet_size: Maximum useful data per packet in bytes
        """
        self.address = address
        self.max_packet_size = max_packet_size
        self.continuity_index = 0

    def packetize_datagroup(self, datagroup: MscDataGroup) -> List[MscPacket]:
        """
        Packetize a single data group into packets.

        Args:
            datagroup: MscDataGroup to packetize

        Returns:
            List of MscPacket instances
        """
        # Encode data group
        dg_bytes = datagroup.encode()

        if len(dg_bytes) == 0:
            return []

        packets = []
        offset = 0

        while offset < len(dg_bytes):
            # Calculate chunk size (reserve 1 byte for CI/flags)
            available_size = self.max_packet_size - 1
            chunk_size = min(available_size, len(dg_bytes) - offset)
            chunk_data = dg_bytes[offset:offset + chunk_size]

            # Determine flags
            is_first = (offset == 0)
            is_last = (offset + chunk_size >= len(dg_bytes))

            # Create packet
            # Useful data length includes CI/flags byte + actual data
            useful_length = len(chunk_data) + 1

            packet = MscPacket(
                address=self.address,
                useful_data_length=useful_length,
                continuity_index=self.continuity_index,
                first=is_first,
                last=is_last,
                data=chunk_data
            )

            packets.append(packet)

            # Advance
            offset += chunk_size
            self.continuity_index = (self.continuity_index + 1) % 4

        logger.debug(
            "Packetized data group",
            dg_size=len(dg_bytes),
            packets=len(packets),
            address=self.address
        )

        return packets

    def packetize_datagroups(self, datagroups: List[MscDataGroup]) -> List[MscPacket]:
        """
        Packetize multiple data groups.

        Args:
            datagroups: List of MscDataGroup instances

        Returns:
            List of MscPacket instances
        """
        all_packets = []

        for datagroup in datagroups:
            packets = self.packetize_datagroup(datagroup)
            all_packets.extend(packets)

        logger.info(
            "Packetized data groups",
            datagroups=len(datagroups),
            total_packets=len(all_packets),
            address=self.address
        )

        return all_packets

    def reset_continuity(self) -> None:
        """Reset continuity index to 0."""
        self.continuity_index = 0


def packetize_mot_object(mot_object, address: int = 0,
                        max_segment_size: int = 8188,
                        max_packet_size: int = 96) -> List[MscPacket]:
    """
    Convenience function to fully packetize a MOT object.

    Args:
        mot_object: MotObject to packetize
        address: Packet address (0-1023)
        max_segment_size: Maximum data group segment size
        max_packet_size: Maximum packet size

    Returns:
        List of MscPacket instances ready for transmission
    """
    from dabmux.mot.msc_datagroup import segment_mot_object

    # Segment into data groups
    datagroups = segment_mot_object(mot_object, max_segment_size=max_segment_size)

    # Packetize data groups
    packetizer = MscPacketizer(address=address, max_packet_size=max_packet_size)
    packets = packetizer.packetize_datagroups(datagroups)

    logger.info(
        "Fully packetized MOT object",
        transport_id=mot_object.transport_id,
        datagroups=len(datagroups),
        packets=len(packets)
    )

    return packets
