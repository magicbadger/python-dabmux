"""Tests for F-PAD encoder."""

import pytest
from dabmux.pad.fpad import FPADEncoder


class TestFPADEncoder:
    """Test F-PAD (Fixed PAD) encoding."""

    def test_fpad_no_xpad(self):
        """Test F-PAD with no X-PAD."""
        encoder = FPADEncoder(xpad_length=0)
        fpad = encoder.encode(has_xpad=False)

        assert fpad == b'\x00\x00'
        assert len(fpad) == 2

    def test_fpad_basic_encoding(self):
        """Test basic F-PAD encoding with X-PAD."""
        encoder = FPADEncoder(xpad_length=12)
        fpad = encoder.encode(has_xpad=True, app_type=2)

        assert len(fpad) == 2

        # Check CI flag (bit 7 of byte 1)
        assert fpad[0] & 0x80 == 0x80  # CI = 1 (variable size)

        # Check application type (bits 6-2 of byte 1)
        app_type = (fpad[0] >> 2) & 0x1F
        assert app_type == 2  # DLS

    def test_fpad_l_value_calculation(self):
        """Test L value calculation for various X-PAD lengths."""
        test_cases = [
            (4, 0),    # L=0: 4 bytes
            (6, 1),    # L=1: 6 bytes
            (8, 2),    # L=2: 8 bytes
            (12, 4),   # L=4: 12 bytes
            (20, 8),   # L=8: 20 bytes
            (58, 27),  # L=27: 58 bytes (common for 48 kbps)
            (196, 96), # Maximum X-PAD length would give L=96, but clamped to 31
        ]

        for xpad_len, expected_l in test_cases:
            encoder = FPADEncoder(xpad_length=xpad_len)
            l_value = encoder._calculate_l_value(xpad_len)

            if xpad_len <= 66:
                assert l_value == expected_l, f"L value mismatch for {xpad_len} bytes"
            else:
                # For lengths > 66, L is clamped to 31
                assert l_value <= 31

    def test_fpad_common_pad_lengths(self):
        """Test F-PAD with common PAD lengths for various bitrates."""
        # Formula: L = (X-PAD length - 4) / 2
        common_lengths = {
            20: 7,   # 24 kbps: 20 bytes PAD → 18 bytes X-PAD → L=(18-4)/2=7
            26: 10,  # 32 kbps: 26 bytes PAD → 24 bytes X-PAD → L=(24-4)/2=10
            58: 26,  # 48-80 kbps: 58 bytes PAD → 56 bytes X-PAD → L=(56-4)/2=26
        }

        for pad_length, expected_l in common_lengths.items():
            xpad_length = pad_length - 2  # Subtract F-PAD
            encoder = FPADEncoder(xpad_length=xpad_length)
            fpad = encoder.encode(has_xpad=True)

            l_value = fpad[1]
            assert l_value == expected_l, \
                f"L value mismatch for PAD length {pad_length}: got {l_value}, expected {expected_l}"

    def test_fpad_application_types(self):
        """Test F-PAD with different application types."""
        encoder = FPADEncoder(xpad_length=12)

        # Test DLS (app_type = 2)
        fpad_dls = encoder.encode(has_xpad=True, app_type=2)
        app_type_dls = (fpad_dls[0] >> 2) & 0x1F
        assert app_type_dls == 2

        # Test MOT (app_type = 12)
        fpad_mot = encoder.encode(has_xpad=True, app_type=12)
        app_type_mot = (fpad_mot[0] >> 2) & 0x1F
        assert app_type_mot == 12

    def test_fpad_length_bounds(self):
        """Test F-PAD with boundary X-PAD lengths."""
        # Minimum X-PAD length
        encoder_min = FPADEncoder(xpad_length=4)
        fpad_min = encoder_min.encode(has_xpad=True)
        assert len(fpad_min) == 2
        assert fpad_min[1] == 0  # L=0 for 4 bytes

        # Maximum standard X-PAD length (66 bytes for short X-PAD)
        encoder_max = FPADEncoder(xpad_length=66)
        fpad_max = encoder_max.encode(has_xpad=True)
        assert len(fpad_max) == 2
        assert fpad_max[1] == 31  # L=31 for 66 bytes

    def test_fpad_odd_length_warning(self):
        """Test that odd X-PAD lengths are handled (should warn but continue)."""
        # Odd lengths are not standard but should not crash
        encoder = FPADEncoder(xpad_length=13)
        fpad = encoder.encode(has_xpad=True)
        assert len(fpad) == 2
