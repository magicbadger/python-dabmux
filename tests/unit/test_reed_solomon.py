"""
Unit tests for Reed-Solomon error correction.

These tests verify RS encoding for DAB error protection.
"""
import pytest
from dabmux.fec.reed_solomon import ReedSolomonEncoder, ReedSolomonDAB


class TestReedSolomonEncoder:
    """Test Reed-Solomon encoder."""

    def test_create_encoder(self) -> None:
        """Test creating RS encoder."""
        encoder = ReedSolomonEncoder(n=255, k=223)
        assert encoder.n == 255
        assert encoder.k == 223
        assert encoder.nroots == 32

    def test_invalid_parameters(self) -> None:
        """Test invalid RS parameters."""
        # n > 255
        with pytest.raises(ValueError):
            ReedSolomonEncoder(n=256, k=200)

        # k >= n
        with pytest.raises(ValueError):
            ReedSolomonEncoder(n=255, k=255)

        # k <= 0
        with pytest.raises(ValueError):
            ReedSolomonEncoder(n=255, k=0)

    def test_encode_small_block(self) -> None:
        """Test encoding small data block."""
        encoder = ReedSolomonEncoder(n=10, k=6)
        data = b'\x01\x02\x03\x04\x05\x06'

        parity = encoder.encode(data)

        assert len(parity) == 4  # n - k = 10 - 6 = 4

    def test_encode_wrong_length(self) -> None:
        """Test encoding with wrong data length."""
        encoder = ReedSolomonEncoder(n=10, k=6)
        data = b'\x01\x02\x03'  # Only 3 bytes, need 6

        with pytest.raises(ValueError):
            encoder.encode(data)

    def test_encode_block(self) -> None:
        """Test encoding block (data + parity)."""
        encoder = ReedSolomonEncoder(n=10, k=6)
        data = b'\x01\x02\x03\x04\x05\x06'

        encoded = encoder.encode_block(data)

        assert len(encoded) == 10  # n = 10
        assert encoded[:6] == data  # First k bytes are data
        assert len(encoded[6:]) == 4  # Last n-k bytes are parity

    def test_encode_all_zeros(self) -> None:
        """Test encoding all zeros."""
        encoder = ReedSolomonEncoder(n=10, k=6)
        data = b'\x00' * 6

        parity = encoder.encode(data)

        # Encoding all zeros should produce all zero parity
        assert parity == b'\x00' * 4

    def test_encode_deterministic(self) -> None:
        """Test encoding is deterministic."""
        encoder = ReedSolomonEncoder(n=10, k=6)
        data = b'\x01\x02\x03\x04\x05\x06'

        parity1 = encoder.encode(data)
        parity2 = encoder.encode(data)

        assert parity1 == parity2

    def test_encode_different_data(self) -> None:
        """Test encoding different data produces different parity."""
        encoder = ReedSolomonEncoder(n=10, k=6)
        data1 = b'\x01\x02\x03\x04\x05\x06'
        data2 = b'\x06\x05\x04\x03\x02\x01'

        parity1 = encoder.encode(data1)
        parity2 = encoder.encode(data2)

        assert parity1 != parity2

    def test_packet_mode_encoder(self) -> None:
        """Test packet mode RS encoder."""
        encoder = ReedSolomonDAB.packet_mode()

        assert encoder.n == 204
        assert encoder.k == 188
        assert encoder.nroots == 16

    def test_packet_mode_encoding(self) -> None:
        """Test packet mode encoding."""
        encoder = ReedSolomonDAB.packet_mode()

        # Create 188-byte data block
        data = bytes(range(188))

        parity = encoder.encode(data)

        assert len(parity) == 16

    def test_edi_pft_encoder(self) -> None:
        """Test EDI/PFT RS encoder."""
        encoder = ReedSolomonDAB.edi_pft(n=100, k=80)

        assert encoder.n == 100
        assert encoder.k == 80
        assert encoder.nroots == 20


class TestReedSolomonProperties:
    """Test RS encoder mathematical properties."""

    def test_systematic_encoding(self) -> None:
        """Test that encoding is systematic (data unchanged)."""
        encoder = ReedSolomonEncoder(n=20, k=16)
        data = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10'

        encoded = encoder.encode_block(data)

        # First k symbols should be unchanged
        assert encoded[:16] == data

    def test_linearity(self) -> None:
        """Test RS encoding linearity property."""
        encoder = ReedSolomonEncoder(n=10, k=6)

        # For linear codes: encode(a) XOR encode(b) == encode(a XOR b)
        data_a = b'\x01\x02\x03\x04\x05\x06'
        data_b = b'\x07\x08\x09\x0a\x0b\x0c'

        parity_a = encoder.encode(data_a)
        parity_b = encoder.encode(data_b)

        # XOR the data
        data_xor = bytes(a ^ b for a, b in zip(data_a, data_b))
        parity_xor = encoder.encode(data_xor)

        # XOR the parities
        expected_parity = bytes(a ^ b for a, b in zip(parity_a, parity_b))

        assert parity_xor == expected_parity

    def test_single_error_detection(self) -> None:
        """Test that parity changes with single bit flip."""
        encoder = ReedSolomonEncoder(n=10, k=6)

        data_original = b'\x01\x02\x03\x04\x05\x06'
        data_error = b'\x01\x02\x03\x04\x05\x07'  # Last byte changed

        parity_original = encoder.encode(data_original)
        parity_error = encoder.encode(data_error)

        # Parity should be different
        assert parity_original != parity_error


class TestReedSolomonLargeBlocks:
    """Test RS encoder with larger blocks."""

    def test_encode_255_223(self) -> None:
        """Test standard RS(255, 223)."""
        encoder = ReedSolomonEncoder(n=255, k=223)

        data = bytes(range(223))
        parity = encoder.encode(data)

        assert len(parity) == 32

    def test_encode_204_188_packet_mode(self) -> None:
        """Test packet mode RS(204, 188)."""
        encoder = ReedSolomonEncoder(n=204, k=188)

        data = bytes(i % 256 for i in range(188))
        parity = encoder.encode(data)

        assert len(parity) == 16

    def test_encode_multiple_blocks(self) -> None:
        """Test encoding multiple blocks."""
        encoder = ReedSolomonEncoder(n=204, k=188)

        # Encode 12 blocks (like enhanced packet mode)
        for i in range(12):
            data = bytes((i * j) % 256 for j in range(188))
            parity = encoder.encode(data)
            assert len(parity) == 16
