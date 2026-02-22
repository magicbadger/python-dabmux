"""
Unit tests for MSC Packet encoding.

Tests per ETSI EN 300 401 Section 5.3.2.
"""

import pytest
from dabmux.mot.msc_packet import (
    MscPacket, MscPacketizer, packetize_mot_object
)
from dabmux.mot.msc_datagroup import MscDataGroup
from dabmux.mot.object import MotObject
from dabmux.mot.header import MotHeader, MotContentType


class TestMscPacket:
    """Tests for MscPacket class."""

    def test_packet_creation(self):
        """Test creating packet."""
        packet = MscPacket(
            address=100,
            useful_data_length=50,
            continuity_index=1,
            first=True,
            last=False,
            data=b'test data'
        )

        assert packet.address == 100
        assert packet.useful_data_length == 50
        assert packet.continuity_index == 1
        assert packet.first is True
        assert packet.last is False
        assert packet.data == b'test data'

    def test_packet_address_validation(self):
        """Test address range validation (0-1023)."""
        # Valid addresses
        MscPacket(address=0, useful_data_length=10, continuity_index=0, first=True, last=True)
        MscPacket(address=1023, useful_data_length=10, continuity_index=0, first=True, last=True)

        # Invalid addresses
        with pytest.raises(ValueError):
            MscPacket(address=-1, useful_data_length=10, continuity_index=0, first=True, last=True)

        with pytest.raises(ValueError):
            MscPacket(address=1024, useful_data_length=10, continuity_index=0, first=True, last=True)

    def test_packet_length_validation(self):
        """Test length range validation (0-8191)."""
        # Valid lengths
        MscPacket(address=0, useful_data_length=0, continuity_index=0, first=True, last=True)
        MscPacket(address=0, useful_data_length=8191, continuity_index=0, first=True, last=True)

        # Invalid lengths
        with pytest.raises(ValueError):
            MscPacket(address=0, useful_data_length=-1, continuity_index=0, first=True, last=True)

        with pytest.raises(ValueError):
            MscPacket(address=0, useful_data_length=8192, continuity_index=0, first=True, last=True)

    def test_packet_continuity_validation(self):
        """Test continuity index range validation (0-3)."""
        # Valid continuity
        for ci in range(4):
            MscPacket(address=0, useful_data_length=10, continuity_index=ci, first=True, last=True)

        # Invalid continuity
        with pytest.raises(ValueError):
            MscPacket(address=0, useful_data_length=10, continuity_index=-1, first=True, last=True)

        with pytest.raises(ValueError):
            MscPacket(address=0, useful_data_length=10, continuity_index=4, first=True, last=True)

    def test_packet_data_size_validation(self):
        """Test data size validation (max 8188 bytes)."""
        # Valid data size
        MscPacket(
            address=0,
            useful_data_length=8188,
            continuity_index=0,
            first=True,
            last=True,
            data=b'x' * 8188
        )

        # Invalid data size
        with pytest.raises(ValueError):
            MscPacket(
                address=0,
                useful_data_length=8189,
                continuity_index=0,
                first=True,
                last=True,
                data=b'x' * 8189
            )

    def test_packet_encode(self):
        """Test encoding packet."""
        packet = MscPacket(
            address=100,
            useful_data_length=10,
            continuity_index=2,
            first=True,
            last=False,
            data=b'Hello'
        )

        encoded = packet.encode()

        # Check structure: header(3 bytes) + CI/flags(1 byte) + data + padding
        assert len(encoded) >= 13  # 3 + 10

        # Decode header (3 bytes)
        header_value = (encoded[0] << 16) | (encoded[1] << 8) | encoded[2]

        # Extract fields
        address = (header_value >> 14) & 0x3FF  # 10 bits
        length = (header_value >> 1) & 0x1FFF  # 13 bits

        assert address == 100
        assert length == 10

        # Check CI/flags byte
        ci_flags = encoded[3]
        ci = (ci_flags >> 6) & 0x03
        first = bool((ci_flags >> 5) & 0x01)
        last = bool((ci_flags >> 4) & 0x01)

        assert ci == 2
        assert first is True
        assert last is False

        # Check data
        assert encoded[4:9] == b'Hello'

    def test_packet_decode(self):
        """Test decoding packet."""
        # Create encoded packet
        packet = MscPacket(
            address=500,
            useful_data_length=15,
            continuity_index=1,
            first=False,
            last=True,
            data=b'Test Data'
        )

        encoded = packet.encode()

        # Decode
        decoded = MscPacket.decode(encoded)

        assert decoded.address == 500
        assert decoded.useful_data_length == 15
        assert decoded.continuity_index == 1
        assert decoded.first is False
        assert decoded.last is True


class TestMscPacketizer:
    """Tests for MscPacketizer."""

    def test_packetizer_creation(self):
        """Test creating packetizer."""
        packetizer = MscPacketizer(address=10, max_packet_size=96)

        assert packetizer.address == 10
        assert packetizer.max_packet_size == 96
        assert packetizer.continuity_index == 0

    def test_packetize_small_datagroup(self):
        """Test packetizing small data group."""
        # Create small data group
        dg = MscDataGroup(
            data=b'Small data',
            crc_flag=True
        )

        packetizer = MscPacketizer(address=0, max_packet_size=96)
        packets = packetizer.packetize_datagroup(dg)

        # Should fit in single packet
        assert len(packets) == 1

        packet = packets[0]
        assert packet.address == 0
        assert packet.first is True
        assert packet.last is True
        assert packet.continuity_index == 0

    def test_packetize_large_datagroup(self):
        """Test packetizing large data group."""
        # Create large data group
        large_data = b'x' * 500
        dg = MscDataGroup(
            data=large_data,
            crc_flag=True
        )

        packetizer = MscPacketizer(address=5, max_packet_size=96)
        packets = packetizer.packetize_datagroup(dg)

        # Should split into multiple packets (500 + overhead > 96)
        assert len(packets) > 1

        # Check first packet
        assert packets[0].first is True
        assert packets[0].last is False

        # Check middle packets
        for packet in packets[1:-1]:
            assert packet.first is False
            assert packet.last is False

        # Check last packet
        assert packets[-1].first is False
        assert packets[-1].last is True

        # All packets should have same address
        for packet in packets:
            assert packet.address == 5

    def test_packetize_continuity_index(self):
        """Test continuity index wrapping (0-3)."""
        # Create data that needs 5 packets to force wrapping
        large_data = b'x' * 1000
        dg = MscDataGroup(data=large_data, crc_flag=False)

        packetizer = MscPacketizer(address=0, max_packet_size=50)
        packets = packetizer.packetize_datagroup(dg)

        # Should have multiple packets
        assert len(packets) > 4

        # Check continuity indices wrap correctly (0, 1, 2, 3, 0, 1, ...)
        for i, packet in enumerate(packets):
            expected_ci = i % 4
            assert packet.continuity_index == expected_ci

    def test_packetize_multiple_datagroups(self):
        """Test packetizing multiple data groups."""
        dg1 = MscDataGroup(data=b'Group 1', crc_flag=True)
        dg2 = MscDataGroup(data=b'Group 2', crc_flag=True)

        packetizer = MscPacketizer(address=10, max_packet_size=96)
        packets = packetizer.packetize_datagroups([dg1, dg2])

        # Should have packets for both groups
        assert len(packets) >= 2

        # Continuity should be continuous across groups
        for i in range(len(packets) - 1):
            expected_next_ci = (packets[i].continuity_index + 1) % 4
            assert packets[i + 1].continuity_index == expected_next_ci

    def test_reset_continuity(self):
        """Test resetting continuity index."""
        packetizer = MscPacketizer(address=0, max_packet_size=96)

        # Send some packets
        dg = MscDataGroup(data=b'test', crc_flag=True)
        packetizer.packetize_datagroup(dg)

        # Continuity should be non-zero now
        assert packetizer.continuity_index > 0

        # Reset
        packetizer.reset_continuity()
        assert packetizer.continuity_index == 0

    def test_empty_datagroup(self):
        """Test packetizing empty data group."""
        dg = MscDataGroup(data=b'', crc_flag=False)

        packetizer = MscPacketizer(address=0, max_packet_size=96)
        packets = packetizer.packetize_datagroup(dg)

        # Empty data group still produces valid encoded packet (header + length)
        assert len(packets) == 1
        assert packets[0].first is True
        assert packets[0].last is True


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_packetize_mot_object(self):
        """Test packetize_mot_object convenience function."""
        # Create MOT object
        header = MotHeader(
            body_size=1000,
            content_type=MotContentType.IMAGE_JFIF
        )
        obj = MotObject(
            header=header,
            body=b'x' * 1000,
            transport_id=100
        )

        # Packetize
        packets = packetize_mot_object(
            obj,
            address=20,
            max_segment_size=8188,
            max_packet_size=96
        )

        # Should return list of packets
        assert len(packets) > 0
        assert all(isinstance(p, MscPacket) for p in packets)

        # All packets should have correct address
        for packet in packets:
            assert packet.address == 20

        # First packet should have first=True
        assert packets[0].first is True

        # Last packet should have last=True
        assert packets[-1].last is True
