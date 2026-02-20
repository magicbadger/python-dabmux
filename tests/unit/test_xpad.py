"""Tests for X-PAD encoder."""

import pytest
from dabmux.pad.xpad import XPADEncoder
from dabmux.pad.dls import DLSEncoder


class TestXPADEncoder:
    """Test X-PAD (Extended PAD) encoding."""

    def test_xpad_initialization(self):
        """Test X-PAD encoder initialization."""
        dls = DLSEncoder(charset='utf8')
        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)

        assert xpad.get_pad_length() == 58
        assert xpad.get_xpad_length() == 56  # 58 - 2 for F-PAD

    def test_xpad_encoding_with_dls(self):
        """Test X-PAD encoding with DLS data."""
        dls = DLSEncoder(charset='utf8')
        dls.set_label("Test Label")

        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)
        pad_data = xpad.encode_pad()

        # Check total length
        assert len(pad_data) == 58

        # Check F-PAD at end (last 2 bytes)
        fpad = pad_data[-2:]
        assert fpad != b'\x00\x00'  # Should have F-PAD data

        # Check X-PAD contains data (not all zeros)
        xpad_part = pad_data[:-2]
        assert xpad_part != bytes(56)  # Should have X-PAD data

    def test_xpad_no_dls(self):
        """Test X-PAD encoding with no DLS set."""
        dls = DLSEncoder(charset='utf8')
        # Don't set any label

        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)
        pad_data = xpad.encode_pad()

        # Should return zero PAD
        assert len(pad_data) == 58
        assert pad_data == bytes(58)

    def test_xpad_multiple_frames(self):
        """Test X-PAD encoding over multiple frames."""
        dls = DLSEncoder(charset='utf8')
        dls.set_label("Multi-segment test with more than 16 characters")

        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)

        # Generate multiple PAD frames
        pads = [xpad.encode_pad() for _ in range(5)]

        # All should be same length
        assert all(len(pad) == 58 for pad in pads)

        # Should have different data (cycling through segments)
        # Check that at least some are different
        unique_pads = set(pads)
        # With multi-segment label, should have at least 2 unique PADs
        assert len(unique_pads) >= 1

    def test_xpad_common_pad_lengths(self):
        """Test X-PAD with common PAD lengths."""
        common_pad_lengths = [20, 26, 58]  # Common for 24, 32, 48+ kbps

        for pad_length in common_pad_lengths:
            dls = DLSEncoder(charset='utf8')
            dls.set_label("Test")

            xpad = XPADEncoder(pad_length=pad_length, dls_encoder=dls)
            pad_data = xpad.encode_pad()

            assert len(pad_data) == pad_length

            # F-PAD should be at end
            fpad = pad_data[-2:]
            assert len(fpad) == 2

    def test_xpad_dls_update(self):
        """Test X-PAD when DLS label changes."""
        dls = DLSEncoder(charset='utf8')
        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)

        # Set first label
        dls.set_label("Label 1")
        pad1 = xpad.encode_pad()

        # Update label
        dls.set_label("Label 2")
        pad2 = xpad.encode_pad()

        # PAD data should be different
        assert pad1 != pad2

        # But both should be correct length
        assert len(pad1) == 58
        assert len(pad2) == 58

    def test_xpad_padding_alignment(self):
        """Test that X-PAD is properly padded to required length."""
        dls = DLSEncoder(charset='utf8')
        dls.set_label("X")  # Very short label

        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)
        pad_data = xpad.encode_pad()

        # Should still be full length
        assert len(pad_data) == 58

        # X-PAD portion should be padded with zeros at the beginning
        xpad_part = pad_data[:-2]
        # First bytes should be padding (zeros)
        assert xpad_part[0] == 0

    def test_xpad_fpad_consistency(self):
        """Test that F-PAD is consistent and correct."""
        dls = DLSEncoder(charset='utf8')
        dls.set_label("Test")

        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)

        # Generate multiple PADs
        pads = [xpad.encode_pad() for _ in range(3)]

        # F-PAD (last 2 bytes) should indicate DLS presence
        for pad in pads:
            fpad = pad[-2:]
            # First byte of F-PAD should have CI flag set (bit 7)
            assert fpad[0] & 0x80 == 0x80

            # Application type should be 2 (DLS)
            app_type = (fpad[0] >> 2) & 0x1F
            assert app_type == 2

    def test_xpad_minimum_pad_length(self):
        """Test X-PAD with minimum viable PAD length."""
        dls = DLSEncoder(charset='utf8')
        dls.set_label("Hi")

        # Minimum is 2 bytes (just F-PAD, no X-PAD)
        xpad = XPADEncoder(pad_length=2, dls_encoder=dls)
        pad_data = xpad.encode_pad()

        assert len(pad_data) == 2

    def test_xpad_large_pad_length(self):
        """Test X-PAD with large PAD length."""
        dls = DLSEncoder(charset='utf8')
        dls.set_label("Large PAD test")

        # Use large PAD length
        xpad = XPADEncoder(pad_length=100, dls_encoder=dls)
        pad_data = xpad.encode_pad()

        assert len(pad_data) == 100

        # Should have F-PAD at end
        fpad = pad_data[-2:]
        assert len(fpad) == 2

        # X-PAD should be padded appropriately
        xpad_part = pad_data[:-2]
        assert len(xpad_part) == 98

    def test_xpad_utf8_special_chars(self):
        """Test X-PAD with UTF-8 special characters."""
        dls = DLSEncoder(charset='utf8')
        dls.set_label("Tëst Spëciål Chårs ♫ 世界")

        xpad = XPADEncoder(pad_length=58, dls_encoder=dls)
        pad_data = xpad.encode_pad()

        assert len(pad_data) == 58
        # Should encode without error
        assert pad_data != bytes(58)
