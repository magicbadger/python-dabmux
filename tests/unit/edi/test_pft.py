"""
Unit tests for PFT (Protection, Fragmentation and Transport) layer.
"""
import pytest
from dabmux.edi.pft import (
    PFTConfig,
    PFFragment,
    PFTFragmenter,
    PF_SYNC
)


class TestPFTConfig:
    """Test PFT configuration."""

    def test_create_default(self) -> None:
        """Test creating default config."""
        config = PFTConfig()
        assert config.fec is False
        assert config.fec_m == 0
        assert config.max_fragment_size == 1400

    def test_create_with_fec(self) -> None:
        """Test creating config with FEC."""
        config = PFTConfig(fec=True, fec_m=2)
        assert config.fec is True
        assert config.fec_m == 2


class TestPFFragment:
    """Test PF fragment structure."""

    def test_create_fragment(self) -> None:
        """Test creating PF fragment."""
        fragment = PFFragment(
            pseq=100,
            findex=0,
            fcount=1,
            fec=False,
            addr=False,
            payload=b"test"
        )
        assert fragment.pseq == 100
        assert fragment.findex == 0
        assert fragment.fcount == 1

    def test_assemble_without_fec(self) -> None:
        """Test assembling fragment without FEC."""
        fragment = PFFragment(
            pseq=1,
            findex=0,
            fcount=1,
            fec=False,
            addr=False,
            payload=b"Hello"
        )
        data = fragment.assemble()

        # Check structure
        assert data[:2] == PF_SYNC  # "PF"
        assert len(data) > 14  # Minimum header + payload

    def test_assemble_with_fec(self) -> None:
        """Test assembling fragment with FEC."""
        fragment = PFFragment(
            pseq=1,
            findex=0,
            fcount=1,
            fec=True,
            addr=False,
            payload=b"Hello",
            rs_k=207,
            rs_z=0
        )
        data = fragment.assemble()

        # With FEC, header includes RSk and RSz fields
        assert data[:2] == PF_SYNC
        assert len(data) > 16  # Longer header with FEC

    def test_assemble_with_addr(self) -> None:
        """Test assembling fragment with addresses."""
        fragment = PFFragment(
            pseq=1,
            findex=0,
            fcount=1,
            fec=False,
            addr=True,
            payload=b"Hello",
            source=0x1234,
            dest=0x5678
        )
        data = fragment.assemble()

        # With ADDR, header includes source and dest fields
        assert data[:2] == PF_SYNC
        assert len(data) > 18  # Longer header with addresses

    def test_parse_valid(self) -> None:
        """Test parsing valid PF fragment."""
        original = PFFragment(
            pseq=42,
            findex=0,
            fcount=1,
            fec=False,
            addr=False,
            payload=b"test payload"
        )
        data = original.assemble()

        # Parse back
        parsed = PFFragment.parse(data)
        assert parsed is not None
        assert parsed.pseq == 42
        assert parsed.findex == 0
        assert parsed.fcount == 1
        assert parsed.payload == b"test payload"

    def test_parse_invalid_sync(self) -> None:
        """Test parsing with invalid sync."""
        data = b"XX" + b'\x00' * 20
        parsed = PFFragment.parse(data)
        assert parsed is None

    def test_parse_too_short(self) -> None:
        """Test parsing data that's too short."""
        data = b"PF" + b'\x00' * 5
        parsed = PFFragment.parse(data)
        assert parsed is None

    def test_parse_invalid_crc(self) -> None:
        """Test parsing with invalid CRC."""
        original = PFFragment(
            pseq=1,
            findex=0,
            fcount=1,
            fec=False,
            addr=False,
            payload=b"test"
        )
        data = bytearray(original.assemble())

        # Corrupt CRC (CRC is after header, before payload)
        data[12] ^= 0xFF

        parsed = PFFragment.parse(bytes(data))
        assert parsed is None

    def test_roundtrip(self) -> None:
        """Test assemble -> parse roundtrip."""
        original = PFFragment(
            pseq=999,
            findex=2,
            fcount=5,
            fec=False,
            addr=False,
            payload=b"The quick brown fox"
        )
        data = original.assemble()
        parsed = PFFragment.parse(data)

        assert parsed is not None
        assert parsed.pseq == original.pseq
        assert parsed.findex == original.findex
        assert parsed.fcount == original.fcount
        assert parsed.payload == original.payload


class TestPFTFragmenter:
    """Test PFT fragmenter."""

    def test_create_fragmenter(self) -> None:
        """Test creating fragmenter."""
        config = PFTConfig()
        fragmenter = PFTFragmenter(config)
        assert fragmenter.config == config
        assert fragmenter._pseq == 0

    def test_fragment_small_packet(self) -> None:
        """Test fragmenting small packet (no fragmentation needed)."""
        config = PFTConfig(fec=False, max_fragment_size=1400)
        fragmenter = PFTFragmenter(config)

        # Small packet that fits in one fragment
        af_packet = b"Small packet"
        fragments = fragmenter.fragment(af_packet)

        assert len(fragments) == 1
        assert fragments[0].findex == 0
        assert fragments[0].fcount == 1
        assert fragments[0].payload == af_packet

    def test_fragment_large_packet(self) -> None:
        """Test fragmenting large packet (multiple fragments)."""
        config = PFTConfig(fec=False, max_fragment_size=100)
        fragmenter = PFTFragmenter(config)

        # Large packet that needs fragmentation
        af_packet = b"X" * 250
        fragments = fragmenter.fragment(af_packet)

        # Should create 3 fragments (250 / 100 = 2.5 -> 3)
        assert len(fragments) == 3
        assert all(f.fcount == 3 for f in fragments)

        # Check indices
        for i, fragment in enumerate(fragments):
            assert fragment.findex == i

        # Reassemble
        reassembled = b"".join(f.payload for f in fragments)
        assert reassembled == af_packet

    def test_fragment_with_fec(self) -> None:
        """Test fragmenting with FEC enabled."""
        config = PFTConfig(fec=True, fec_m=2, max_fragment_size=500)
        fragmenter = PFTFragmenter(config)

        # Packet to fragment
        af_packet = b"A" * 200
        fragments = fragmenter.fragment(af_packet)

        # Should create fragments with FEC enabled
        assert len(fragments) > 0
        assert all(f.fec is True for f in fragments)
        assert all(f.rs_k > 0 for f in fragments)

    def test_sequence_increment(self) -> None:
        """Test that sequence number increments."""
        config = PFTConfig()
        fragmenter = PFTFragmenter(config)

        # Fragment first packet
        fragments1 = fragmenter.fragment(b"packet 1")
        assert fragments1[0].pseq == 0

        # Fragment second packet
        fragments2 = fragmenter.fragment(b"packet 2")
        assert fragments2[0].pseq == 1

        # Fragment third packet
        fragments3 = fragmenter.fragment(b"packet 3")
        assert fragments3[0].pseq == 2

    def test_sequence_wrap(self) -> None:
        """Test sequence number wrapping."""
        config = PFTConfig()
        fragmenter = PFTFragmenter(config)

        # Set sequence to near max
        fragmenter._pseq = 0xFFFF

        # Fragment packet
        fragments = fragmenter.fragment(b"test")
        assert fragments[0].pseq == 0xFFFF

        # Next should wrap to 0
        fragments = fragmenter.fragment(b"test")
        assert fragments[0].pseq == 0

    def test_reset_counter(self) -> None:
        """Test resetting sequence counter."""
        config = PFTConfig()
        fragmenter = PFTFragmenter(config)

        # Fragment some packets
        fragmenter.fragment(b"packet 1")
        fragmenter.fragment(b"packet 2")
        assert fragmenter._pseq == 2

        # Reset
        fragmenter.reset_counter()
        assert fragmenter._pseq == 0
