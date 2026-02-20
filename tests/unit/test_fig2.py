"""
Tests for FIG Type 2: Dynamic Labels.

Per ETSI EN 300 401 Section 8.1.13.
"""
import pytest
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabComponent, DabSubchannel,
    DabLabel, DabProtection, ProtectionForm, SubchannelType,
    DabProtectionEEP, EEPProfile, DynamicLabel
)
from dabmux.fig.fig2 import FIG2_1
from dabmux.fig.base import FIGRate, FIGPriority


def create_test_ensemble():
    """Create a basic test ensemble with one component."""
    ensemble = DabEnsemble(
        id=0xCE15,
        ecc=0xE1,
        label=DabLabel(text="Test Ensemble")
    )

    # Add a subchannel
    protection = DabProtection(
        form=ProtectionForm.EEP,
        level=3,
        eep=DabProtectionEEP(profile=EEPProfile.EEP_A)
    )
    subchannel = DabSubchannel(
        uid='sub1',
        id=0,
        type=SubchannelType.DABPlusAudio,
        bitrate=48,
        protection=protection,
        start_address=0,
        input_uri='file://test.dabp'
    )
    ensemble.subchannels.append(subchannel)

    # Add a service
    service = DabService(
        uid='svc1',
        id=0x5001,
        label=DabLabel(text="Service 1")
    )
    ensemble.services.append(service)

    # Add a component with dynamic label
    component = DabComponent(
        uid='comp1',
        service_id=0x5001,
        subchannel_id=0
    )
    ensemble.components.append(component)

    return ensemble


class TestDynamicLabel:
    """Test DynamicLabel dataclass."""

    def test_update_text_changes_toggle(self):
        """Test that update_text toggles the toggle flag."""
        label = DynamicLabel(text="Initial")

        initial_toggle = label.toggle
        changed = label.update_text("New Text")

        assert changed is True
        assert label.toggle != initial_toggle
        assert label.text == "New Text"

    def test_update_text_unchanged(self):
        """Test that update_text returns False when text unchanged."""
        label = DynamicLabel(text="Same Text")

        toggle_before = label.toggle
        changed = label.update_text("Same Text")

        assert changed is False
        assert label.toggle == toggle_before

    def test_utf8_encoding(self):
        """Test UTF-8 charset encoding."""
        label = DynamicLabel(charset=2)  # UTF-8
        label.update_text("Hello World")

        encoded = label._encode_text()
        assert encoded == b"Hello World"

    def test_ucs2_encoding(self):
        """Test UCS-2 (UTF-16 BE) charset encoding."""
        label = DynamicLabel(charset=1)  # UCS-2
        label.update_text("Hello")

        encoded = label._encode_text()
        assert encoded == "Hello".encode('utf-16-be')

    def test_text_truncation(self):
        """Test that text is truncated to 128 bytes."""
        label = DynamicLabel(charset=2)  # UTF-8
        long_text = "A" * 200
        label.update_text(long_text)

        encoded = label._encode_text()
        assert len(encoded) == 128

    def test_segmentation_short_text(self):
        """Test segmentation of short text (single segment)."""
        label = DynamicLabel(charset=2)
        label.update_text("Short")

        assert len(label._segments) == 1
        assert label._segments[0] == b"Short"

    def test_segmentation_long_text(self):
        """Test segmentation of long text (multiple segments)."""
        label = DynamicLabel(charset=2)
        # 50 bytes = 4 segments (16+16+16+2)
        label.update_text("A" * 50)

        assert len(label._segments) == 4
        assert len(label._segments[0]) == 16
        assert len(label._segments[1]) == 16
        assert len(label._segments[2]) == 16
        assert len(label._segments[3]) == 2

    def test_get_next_segment_circular(self):
        """Test circular segment retrieval."""
        label = DynamicLabel(charset=2)
        label.update_text("ABC")  # Single segment

        # Get segment multiple times
        seg1 = label.get_next_segment()
        seg2 = label.get_next_segment()

        # Should wrap around
        assert seg1 == b"ABC"
        assert seg2 == b"ABC"

    def test_empty_text(self):
        """Test handling of empty text."""
        label = DynamicLabel(charset=2)
        label.update_text("")

        assert len(label._segments) == 0
        assert label.get_next_segment() is None


class TestFIG2_1_Header:
    """Test FIG 2/1 header encoding."""

    def test_header_type_and_charset(self):
        """Test header encoding with UTF-8 charset."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(charset=2, text="Test")

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written > 0

        # Byte 0: Type (3 bits) = 2 | Length (5 bits)
        fig_type = (buf[0] >> 5) & 0x07
        assert fig_type == 2

        # Byte 1: Charset (4 bits) = 2 | OE (1) = 0 | Rfa (1) = 0 | Ext (2) = 1
        charset = (buf[1] >> 4) & 0x0F
        extension = buf[1] & 0x0F
        assert charset == 2  # UTF-8
        assert extension == 1

    def test_header_ebu_latin_charset(self):
        """Test header with EBU Latin charset."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(charset=0, text="Test")

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        charset = (buf[1] >> 4) & 0x0F
        assert charset == 0  # EBU Latin


class TestFIG2_1_SegmentEncoding:
    """Test FIG 2/1 segment encoding."""

    def test_toggle_flag_encoding(self):
        """Test toggle flag in segment header."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(text="Test", toggle=True)

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Segment header at byte 2
        toggle = (buf[2] >> 7) & 0x01
        assert toggle == 1

    def test_segment_number_encoding(self):
        """Test segment number encoding."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(text="A" * 50)  # Multiple segments

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Segment number at byte 2, bits 6-4
        seg_num = (buf[2] >> 4) & 0x07
        assert 0 <= seg_num < 8

    def test_last_segment_flag(self):
        """Test last segment flag encoding."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(text="Short")  # Single segment

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Last flag at byte 2, bit 3
        last = (buf[2] >> 3) & 0x01
        assert last == 1  # Single segment is also last segment

    def test_character_flag(self):
        """Test character flag encoding."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(text="Test")

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Character flag at byte 3
        char_flag = buf[3]
        assert char_flag == 0xFF  # All positions used

    def test_text_data_encoding(self):
        """Test actual text data in segment."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(charset=2, text="Hello")

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Text data starts at byte 4
        text_data = bytes(buf[4:4+5])
        assert text_data == b"Hello"


class TestFIG2_1_CircularTransmission:
    """Test FIG 2/1 circular transmission."""

    def test_single_component_retransmission(self):
        """Test that single component is retransmitted."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(text="Test")

        fig = FIG2_1(ensemble)

        # First transmission
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)
        assert status1.num_bytes_written > 0
        assert status1.complete_fig_transmitted is True

        # Second transmission
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)
        assert status2.num_bytes_written > 0

    def test_multiple_components_round_robin(self):
        """Test round-robin transmission with multiple components."""
        ensemble = create_test_ensemble()

        # Add second component
        component2 = DabComponent(
            uid='comp2',
            service_id=0x5001,
            subchannel_id=0,
            dynamic_label=DynamicLabel(text="Component 2")
        )
        ensemble.components.append(component2)

        # First component
        ensemble.components[0].dynamic_label = DynamicLabel(text="Component 1")

        fig = FIG2_1(ensemble)

        # Transmit multiple times
        for i in range(4):
            buf = bytearray(32)
            status = fig.fill(buf, 32)
            assert status.num_bytes_written > 0

        # After 2 transmissions (one per component), should be complete
        # component_index should wrap around
        assert fig.component_index == 0


class TestFIG2_1_EmptyLabel:
    """Test FIG 2/1 with empty or missing labels."""

    def test_no_dynamic_labels(self):
        """Test FIG 2/1 when no components have dynamic labels."""
        ensemble = create_test_ensemble()
        # No dynamic label set

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is True

    def test_empty_text(self):
        """Test FIG 2/1 with empty text."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(text="")

        fig = FIG2_1(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Empty text still gets filtered out (text is falsy)
        assert status.num_bytes_written == 0


class TestFIG2_1_Metadata:
    """Test FIG 2/1 metadata methods."""

    def test_repetition_rate(self):
        """Test FIG 2/1 repetition rate is A (100ms)."""
        ensemble = create_test_ensemble()
        fig = FIG2_1(ensemble)

        assert fig.repetition_rate() == FIGRate.A

    def test_priority(self):
        """Test FIG 2/1 priority is NORMAL."""
        ensemble = create_test_ensemble()
        fig = FIG2_1(ensemble)

        assert fig.priority() == FIGPriority.NORMAL

    def test_fig_type(self):
        """Test FIG type is 2."""
        ensemble = create_test_ensemble()
        fig = FIG2_1(ensemble)

        assert fig.fig_type() == 2

    def test_fig_extension(self):
        """Test FIG extension is 1."""
        ensemble = create_test_ensemble()
        fig = FIG2_1(ensemble)

        assert fig.fig_extension() == 1


class TestDynamicLabel_Integration:
    """Integration tests for DynamicLabel with FIG 2/1."""

    def test_text_update_propagates(self):
        """Test that text updates are reflected in FIG 2/1."""
        ensemble = create_test_ensemble()
        component = ensemble.components[0]
        component.dynamic_label = DynamicLabel(text="Original")

        fig = FIG2_1(ensemble)

        # Get first transmission
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)
        toggle1 = (buf1[2] >> 7) & 0x01

        # Update text
        component.dynamic_label.update_text("Updated")

        # Get second transmission
        buf2 = bytearray(32)
        # Reset component index to force same component
        fig.component_index = 0
        status2 = fig.fill(buf2, 32)
        toggle2 = (buf2[2] >> 7) & 0x01

        # Toggle should have flipped
        assert toggle1 != toggle2
