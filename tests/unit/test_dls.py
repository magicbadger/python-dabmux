"""Tests for DLS encoder."""

import pytest
from dabmux.pad.dls import DLSEncoder


class TestDLSEncoder:
    """Test DLS (Dynamic Label Segment) encoding."""

    def test_dls_initialization(self):
        """Test DLS encoder initialization."""
        encoder = DLSEncoder(charset='utf8')
        assert encoder.charset == 'utf8'
        assert encoder.current_label == ""
        assert len(encoder.segments) == 0

    def test_dls_simple_label(self):
        """Test encoding a simple label."""
        encoder = DLSEncoder(charset='utf8')
        encoder.set_label("Hello World")

        assert encoder.get_current_label() == "Hello World"
        assert encoder.get_num_segments() > 0

        # Get first segment
        seg = encoder.get_next_segment()
        assert seg is not None
        assert len(seg) > 0

        # First byte is prefix
        prefix = seg[0]
        # Extract segment number (bits 2-0)
        seg_num = prefix & 0x07
        assert seg_num == 0  # First segment

    def test_dls_segmentation_short_text(self):
        """Test DLS segmentation with short text (< 16 bytes)."""
        encoder = DLSEncoder(charset='utf8')
        encoder.set_label("Test")

        # Should create 1 segment
        assert encoder.get_num_segments() == 1

        seg = encoder.get_next_segment()
        assert seg is not None

        # Prefix + "Test" (4 bytes)
        assert len(seg) == 5  # 1 prefix + 4 data

        # Extract data (skip prefix)
        data = seg[1:]
        assert data == b'Test'

    def test_dls_segmentation_long_text(self):
        """Test DLS segmentation with text requiring multiple segments."""
        encoder = DLSEncoder(charset='utf8')

        # 50 characters = 50 bytes in ASCII
        long_text = "A" * 50
        encoder.set_label(long_text)

        # Should create ceil(50 / 16) = 4 segments
        assert encoder.get_num_segments() == 4

        # Collect all segments
        segments = [encoder.get_next_segment() for _ in range(4)]

        # Verify all segments retrieved
        assert all(seg is not None for seg in segments)

        # Reconstruct text from segments
        reconstructed = b''.join(seg[1:] for seg in segments)
        assert reconstructed == b'A' * 50

    def test_dls_segment_cycling(self):
        """Test that segments cycle repeatedly."""
        encoder = DLSEncoder(charset='utf8')
        encoder.set_label("ABC")

        # Should have 1 segment
        assert encoder.get_num_segments() == 1

        # Get segment multiple times - should be same each time
        seg1 = encoder.get_next_segment()
        seg2 = encoder.get_next_segment()
        seg3 = encoder.get_next_segment()

        assert seg1 == seg2 == seg3

    def test_dls_segment_order(self):
        """Test segment order with multi-segment label."""
        encoder = DLSEncoder(charset='utf8')

        # Create label with exactly 3 segments (16 + 16 + 1 = 33 bytes)
        label = "A" * 33
        encoder.set_label(label)

        assert encoder.get_num_segments() == 3

        # Get segments and check order
        for expected_seg_num in range(3):
            seg = encoder.get_next_segment()
            prefix = seg[0]
            seg_num = prefix & 0x07  # Segment number is 3 bits (bits 2-0)
            assert seg_num == expected_seg_num

        # After getting all 3, should cycle back to 0
        seg = encoder.get_next_segment()
        prefix = seg[0]
        seg_num = prefix & 0x07
        assert seg_num == 0

    def test_dls_utf8_encoding(self):
        """Test UTF-8 character encoding."""
        encoder = DLSEncoder(charset='utf8')

        # Test with UTF-8 characters
        encoder.set_label("Héllo Wörld 世界")

        seg = encoder.get_next_segment()
        assert seg is not None

        # Check charset bits in prefix (bits 6-4)
        prefix = seg[0]
        charset = (prefix >> 4) & 0x07  # 3 bits for charset (bit 6-4)
        # UTF-8 charset code should have bit 0 set (0x01 or 0x09 with last bit)
        assert (charset & 0x01) == 0x01  # UTF-8

    def test_dls_ebu_latin_encoding(self):
        """Test EBU Latin encoding."""
        encoder = DLSEncoder(charset='ebu-latin')

        encoder.set_label("Test Label")

        seg = encoder.get_next_segment()
        assert seg is not None

        # Check charset bits
        prefix = seg[0]
        charset = (prefix >> 4) & 0x07
        # EBU Latin should be 0x00 (or 0x08 with last bit)
        assert (charset & 0x01) == 0x00  # EBU Latin

    def test_dls_toggle_bit(self):
        """Test toggle bit changes on label update."""
        encoder = DLSEncoder(charset='utf8')

        # Set first label
        encoder.set_label("Label 1")
        seg1 = encoder.get_next_segment()
        prefix1 = seg1[0]
        toggle1 = (prefix1 & 0x80) >> 7

        # Update label
        encoder.set_label("Label 2")
        seg2 = encoder.get_next_segment()
        prefix2 = seg2[0]
        toggle2 = (prefix2 & 0x80) >> 7

        # Toggle bit should have flipped
        assert toggle1 != toggle2

        # Update again
        encoder.set_label("Label 3")
        seg3 = encoder.get_next_segment()
        prefix3 = seg3[0]
        toggle3 = (prefix3 & 0x80) >> 7

        # Should flip again (back to first state)
        assert toggle3 != toggle2
        assert toggle3 == toggle1

    def test_dls_last_segment_flag(self):
        """Test that last segment has proper flag set."""
        encoder = DLSEncoder(charset='utf8')

        # Use text that creates exactly 2 segments
        encoder.set_label("A" * 20)  # 20 bytes = 2 segments (16 + 4)

        assert encoder.get_num_segments() == 2

        # First segment - should NOT have last flag
        seg1 = encoder.get_next_segment()
        prefix1 = seg1[0]
        # Bit 3 indicates last segment
        is_last1 = (prefix1 & 0x08) != 0
        assert not is_last1

        # Second segment - SHOULD have last flag
        seg2 = encoder.get_next_segment()
        prefix2 = seg2[0]
        is_last2 = (prefix2 & 0x08) != 0
        assert is_last2

    def test_dls_empty_label(self):
        """Test encoding empty label."""
        encoder = DLSEncoder(charset='utf8')
        encoder.set_label("")

        # Should create at least one segment
        assert encoder.get_num_segments() >= 1

        seg = encoder.get_next_segment()
        assert seg is not None

        # Should be just prefix (or prefix + minimal data)
        assert len(seg) >= 1

    def test_dls_max_length_truncation(self):
        """Test that labels longer than 128 chars are truncated."""
        encoder = DLSEncoder(charset='utf8')

        # Create label longer than max (128 chars)
        long_label = "X" * 200
        encoder.set_label(long_label)

        # Should be truncated to 128
        assert len(encoder.get_current_label()) == 128
        assert encoder.get_current_label() == "X" * 128

    def test_dls_no_change_optimization(self):
        """Test that setting same label twice doesn't regenerate segments."""
        encoder = DLSEncoder(charset='utf8')

        encoder.set_label("Test")
        segments1 = encoder.segments

        # Set same label again
        encoder.set_label("Test")
        segments2 = encoder.segments

        # Should be same object (not regenerated)
        assert segments1 is segments2

    def test_dls_special_characters(self):
        """Test DLS with special characters."""
        encoder = DLSEncoder(charset='utf8')

        special_text = "Song: Artist - Album (2024) #1 ♫"
        encoder.set_label(special_text)

        seg = encoder.get_next_segment()
        assert seg is not None

        # Should encode without error
        assert len(seg) > 0

    def test_dls_newlines_and_formatting(self):
        """Test DLS with newlines and special formatting."""
        encoder = DLSEncoder(charset='utf8')

        # DLS typically doesn't support newlines, but should handle gracefully
        text_with_newlines = "Line 1\nLine 2\nLine 3"
        encoder.set_label(text_with_newlines)

        seg = encoder.get_next_segment()
        assert seg is not None

        # Should encode (newlines will be in UTF-8)
        data = seg[1:]
        assert b'\n' in data or len(data) > 0  # Newlines encoded or removed
