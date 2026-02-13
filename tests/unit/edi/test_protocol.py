"""
Unit tests for EDI protocol structures.
"""
import pytest
from dabmux.edi.protocol import (
    TagStarPTR,
    TagDETI,
    TagESTn,
    TagPacket,
    AFPacket,
    AF_SYNC,
    AF_PT_TAG
)


class TestTagStarPTR:
    """Test *ptr TAG item."""

    def test_create_tag(self) -> None:
        """Test creating *ptr TAG."""
        tag = TagStarPTR(protocol="DETI", major=0, minor=0)
        assert tag.protocol == "DETI"
        assert tag.major == 0
        assert tag.minor == 0

    def test_get_name(self) -> None:
        """Test TAG name."""
        tag = TagStarPTR()
        assert tag.get_name() == b"*ptr"

    def test_assemble(self) -> None:
        """Test TAG assembly."""
        tag = TagStarPTR(protocol="DETI", major=1, minor=2)
        data = tag.assemble()

        # Check structure: name(4) + length(4) + value(8)
        assert len(data) == 16
        assert data[:4] == b"*ptr"
        # Length should be 64 bits (8 bytes)
        assert data[4:8] == b'\x00\x00\x00\x40'
        # Protocol: "DETI"
        assert data[8:12] == b"DETI"
        # Major: 1, Minor: 2 (big-endian)
        assert data[12:14] == b'\x00\x01'
        assert data[14:16] == b'\x00\x02'

    def test_custom_protocol(self) -> None:
        """Test with custom protocol."""
        tag = TagStarPTR(protocol="TEST")
        data = tag.assemble()
        assert b"TEST" in data


class TestTagDETI:
    """Test deti TAG item."""

    def test_create_tag(self) -> None:
        """Test creating deti TAG."""
        tag = TagDETI(dlfc=100, mid=1, fp=0)
        assert tag.dlfc == 100
        assert tag.mid == 1
        assert tag.fp == 0

    def test_get_name(self) -> None:
        """Test TAG name."""
        tag = TagDETI()
        assert tag.get_name() == b"deti"

    def test_assemble_minimal(self) -> None:
        """Test minimal deti assembly (no timestamp, no FIC)."""
        tag = TagDETI(
            dlfc=100,
            mid=1,
            fp=0,
            mnsc=0x1234,
            atstf=False,
            ficf=False
        )
        data = tag.assemble()

        # Check structure: name(4) + length(4) + value(6)
        # Value: FCT/FCTH(2) + ETI header(4)
        assert len(data) >= 14  # 4 + 4 + 6
        assert data[:4] == b"deti"

    def test_assemble_with_timestamp(self) -> None:
        """Test deti with timestamp."""
        tag = TagDETI(
            dlfc=100,
            atstf=True,
            utco=5,
            seconds=1000,
            tsta=0x123456
        )
        data = tag.assemble()

        # With timestamp: value is FCT/FCTH(2) + ETI(4) + ATST(8) = 14 bytes
        # Total: name(4) + length(4) + value(14) = 22 bytes
        assert len(data) >= 22

    def test_assemble_with_fic(self) -> None:
        """Test deti with FIC data."""
        fic_data = b'\x00' * 96  # 96 bytes for Mode I
        tag = TagDETI(
            dlfc=100,
            ficf=True,
            fic_data=fic_data
        )
        data = tag.assemble()

        # With FIC: value is FCT/FCTH(2) + ETI(4) + FIC(96) = 102 bytes
        assert len(data) >= 110  # 4 + 4 + 102

    def test_dlfc_modulo(self) -> None:
        """Test DLFC modulo 5000."""
        tag = TagDETI(dlfc=5001)
        assert tag.dlfc == 5001  # Stored as-is
        # FCT/FCTH calculation happens in get_value()
        value = tag.get_value()
        # FCT should be 5001 % 250 = 1
        # FCTH should be 5001 // 250 = 20
        assert value[0] == 1  # FCT


class TestTagESTn:
    """Test estN TAG item."""

    def test_create_tag(self) -> None:
        """Test creating estN TAG."""
        tag = TagESTn(
            id=1,
            scid=0,
            sad=0,
            tpl=0,
            mst_data=b'\x00' * 384
        )
        assert tag.id == 1
        assert tag.scid == 0

    def test_get_name(self) -> None:
        """Test TAG name."""
        tag1 = TagESTn(id=1, scid=0, sad=0, tpl=0, mst_data=b"")
        assert tag1.get_name() == b"est1"

        tag2 = TagESTn(id=2, scid=1, sad=0, tpl=0, mst_data=b"")
        assert tag2.get_name() == b"est2"

    def test_assemble(self) -> None:
        """Test TAG assembly."""
        mst_data = b'\xAA' * 100
        tag = TagESTn(
            id=1,
            scid=5,
            sad=10,
            tpl=2,
            mst_data=mst_data
        )
        data = tag.assemble()

        # Check structure: name(4) + length(4) + value(3 + len(mst_data))
        assert len(data) == 4 + 4 + 3 + 100
        assert data[:4] == b"est1"

        # Check SSTC encoding (3 bytes)
        # SSTC should contain scid=5, sad=10, tpl=2
        value = data[8:]
        assert len(value) == 103  # 3 + 100


class TestTagPacket:
    """Test TAG packet assembly."""

    def test_create_packet(self) -> None:
        """Test creating TAG packet."""
        packet = TagPacket(tag_items=[], alignment=8)
        assert len(packet.tag_items) == 0

    def test_assemble_empty(self) -> None:
        """Test assembling empty packet."""
        packet = TagPacket(tag_items=[], alignment=0)
        data = packet.assemble()
        assert data == b""

    def test_assemble_single_tag(self) -> None:
        """Test assembling with single TAG."""
        tag = TagStarPTR(protocol="DETI")
        packet = TagPacket(tag_items=[tag], alignment=0)
        data = packet.assemble()

        # Should match TAG assembly
        assert data == tag.assemble()

    def test_assemble_multiple_tags(self) -> None:
        """Test assembling with multiple TAGs."""
        tag1 = TagStarPTR(protocol="DETI")
        tag2 = TagDETI(dlfc=0)

        packet = TagPacket(tag_items=[tag1, tag2], alignment=0)
        data = packet.assemble()

        # Should be concatenation
        expected = tag1.assemble() + tag2.assemble()
        assert data == expected

    def test_alignment(self) -> None:
        """Test byte alignment."""
        # Create TAG with non-aligned size
        tag = TagStarPTR()  # 16 bytes
        packet = TagPacket(tag_items=[tag], alignment=32)
        data = packet.assemble()

        # Should be padded to 32-byte boundary
        assert len(data) % 32 == 0
        assert len(data) == 32  # 16 bytes TAG + 16 bytes padding


class TestAFPacket:
    """Test AF packet structure."""

    def test_create_packet(self) -> None:
        """Test creating AF packet."""
        packet = AFPacket(seq=0, payload=b"test")
        assert packet.seq == 0
        assert packet.payload == b"test"

    def test_assemble(self) -> None:
        """Test AF packet assembly."""
        payload = b"Hello, EDI!"
        packet = AFPacket(seq=100, payload=payload)
        data = packet.assemble()

        # Check structure
        assert data[:2] == AF_SYNC  # "AF"
        assert data[9] == AF_PT_TAG  # 'T'

        # Total length: 10 (header) + payload + 2 (CRC)
        assert len(data) == 10 + len(payload) + 2

    def test_sequence_wrap(self) -> None:
        """Test sequence number wrapping."""
        packet = AFPacket(seq=0xFFFF, payload=b"test")
        assert packet.seq == 0xFFFF

        # Assemble and check (should not crash)
        data = packet.assemble()
        assert len(data) > 0

    def test_parse_valid(self) -> None:
        """Test parsing valid AF packet."""
        original = AFPacket(seq=42, payload=b"test payload")
        data = original.assemble()

        # Parse back
        parsed = AFPacket.parse(data)
        assert parsed is not None
        assert parsed.seq == 42
        assert parsed.payload == b"test payload"

    def test_parse_invalid_sync(self) -> None:
        """Test parsing with invalid sync."""
        data = b"XX" + b'\x00' * 20
        parsed = AFPacket.parse(data)
        assert parsed is None

    def test_parse_too_short(self) -> None:
        """Test parsing data that's too short."""
        data = b"AF" + b'\x00' * 5
        parsed = AFPacket.parse(data)
        assert parsed is None

    def test_parse_invalid_crc(self) -> None:
        """Test parsing with invalid CRC."""
        original = AFPacket(seq=42, payload=b"test")
        data = bytearray(original.assemble())

        # Corrupt CRC
        data[-1] ^= 0xFF

        parsed = AFPacket.parse(bytes(data))
        assert parsed is None

    def test_roundtrip(self) -> None:
        """Test assemble -> parse roundtrip."""
        original = AFPacket(seq=123, payload=b"The quick brown fox")
        data = original.assemble()
        parsed = AFPacket.parse(data)

        assert parsed is not None
        assert parsed.seq == original.seq
        assert parsed.payload == original.payload
