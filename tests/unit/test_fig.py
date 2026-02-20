"""
Unit tests for FIG generation.

These tests verify that FIGs are correctly generated and encoded.
"""
import pytest
from dabmux.fig.base import FIGBase, FIGRate, FillStatus, rate_increment_ms
from dabmux.fig.fig0 import FIG0_0, FIG0_1, FIG0_2
from dabmux.fig.fig1 import FIG1_0, FIG1_1
from dabmux.fig.carousel import FIGCarousel
from dabmux.fig.fic import FICEncoder
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabComponent, DabSubchannel,
    DabLabel, SubchannelType, TransmissionMode, DabProtection, ProtectionForm
)


class TestFIGRate:
    """Test FIG rate enum and functions."""

    def test_fig_rate_values(self) -> None:
        """Test FIG rate enum values."""
        assert FIGRate.FIG0_0.value == "fig0_0"
        assert FIGRate.A.value == "a"
        assert FIGRate.B.value == "b"

    def test_rate_increment_ms(self) -> None:
        """Test rate increment mapping."""
        assert rate_increment_ms(FIGRate.FIG0_0) == 96
        assert rate_increment_ms(FIGRate.A) == 100
        assert rate_increment_ms(FIGRate.B) == 1000
        assert rate_increment_ms(FIGRate.C) == 10000


class TestFillStatus:
    """Test FillStatus dataclass."""

    def test_default_values(self) -> None:
        """Test default fill status values."""
        status = FillStatus()
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_custom_values(self) -> None:
        """Test custom fill status values."""
        status = FillStatus(num_bytes_written=10, complete_fig_transmitted=True)
        assert status.num_bytes_written == 10
        assert status.complete_fig_transmitted is True


class TestFIG0_0:
    """Test FIG 0/0 (Ensemble information)."""

    def test_create_fig0_0(self) -> None:
        """Test creating FIG 0/0."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.alarm_flag = False

        fig = FIG0_0(ensemble, current_frame=0)
        assert fig.fig_type() == 0
        assert fig.fig_extension() == 0
        assert fig.name() == "0/0"

    def test_fig0_0_repetition_rate(self) -> None:
        """Test FIG 0/0 repetition rate."""
        ensemble = DabEnsemble()
        fig = FIG0_0(ensemble)
        assert fig.repetition_rate() == FIGRate.FIG0_0

    def test_fig0_0_fill(self) -> None:
        """Test filling FIG 0/0."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.alarm_flag = True

        fig = FIG0_0(ensemble, current_frame=100)
        buf = bytearray(32)

        status = fig.fill(buf, 32)
        assert status.num_bytes_written == 6
        assert status.complete_fig_transmitted is True

        # Check header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[0] & 0x1F) == 4  # Length 4 (data bytes after header)

        # Check extension
        assert (buf[1] & 0x1F) == 0  # Extension 0

        # Check EId (big-endian)
        eid = (buf[2] << 8) | buf[3]
        assert eid == 0x4FFF

    def test_fig0_0_insufficient_space(self) -> None:
        """Test FIG 0/0 with insufficient space."""
        ensemble = DabEnsemble()
        fig = FIG0_0(ensemble)
        buf = bytearray(4)  # Too small

        status = fig.fill(buf, 4)
        assert status.num_bytes_written == 0


class TestFIG0_1:
    """Test FIG 0/1 (Sub-channel organization)."""

    def test_create_fig0_1(self) -> None:
        """Test creating FIG 0/1."""
        ensemble = DabEnsemble()
        fig = FIG0_1(ensemble)
        assert fig.fig_type() == 0
        assert fig.fig_extension() == 1

    def test_fig0_1_repetition_rate(self) -> None:
        """Test FIG 0/1 repetition rate."""
        ensemble = DabEnsemble()
        fig = FIG0_1(ensemble)
        assert fig.repetition_rate() == FIGRate.B

    def test_fig0_1_with_subchannels_uep(self) -> None:
        """Test FIG 0/1 with UEP subchannels."""
        ensemble = DabEnsemble()

        # Add subchannel with UEP
        sub = DabSubchannel(uid="audio1", id=1, bitrate=128)
        sub.start_address = 0
        sub.protection.form = ProtectionForm.UEP
        sub.protection.level = 3
        ensemble.subchannels.append(sub)

        fig = FIG0_1(ensemble)
        buf = bytearray(32)

        status = fig.fill(buf, 32)
        assert status.num_bytes_written > 0
        assert status.complete_fig_transmitted is True

        # Check header
        assert (buf[0] >> 5) == 0  # FIG type 0
        assert (buf[1] & 0x1F) == 1  # Extension 1

    def test_fig0_1_empty_ensemble(self) -> None:
        """Test FIG 0/1 with no subchannels."""
        ensemble = DabEnsemble()
        fig = FIG0_1(ensemble)
        buf = bytearray(32)

        status = fig.fill(buf, 32)
        assert status.num_bytes_written == 0


class TestFIG0_2:
    """Test FIG 0/2 (Service organization)."""

    def test_create_fig0_2(self) -> None:
        """Test creating FIG 0/2."""
        ensemble = DabEnsemble()
        fig = FIG0_2(ensemble)
        assert fig.fig_type() == 0
        assert fig.fig_extension() == 2

    def test_fig0_2_repetition_rate(self) -> None:
        """Test FIG 0/2 repetition rate."""
        ensemble = DabEnsemble()
        fig = FIG0_2(ensemble)
        assert fig.repetition_rate() == FIGRate.A_B

    def test_fig0_2_with_services(self) -> None:
        """Test FIG 0/2 with services."""
        ensemble = DabEnsemble()

        # Add service and component
        service = DabService(uid="radio1", id=0x1234)
        ensemble.services.append(service)

        component = DabComponent(uid="comp1")
        component.service_id = 0x1234
        component.subchannel_id = 1
        ensemble.components.append(component)

        fig = FIG0_2(ensemble)
        buf = bytearray(32)

        status = fig.fill(buf, 32)
        assert status.num_bytes_written > 0

    def test_fig0_2_empty_ensemble(self) -> None:
        """Test FIG 0/2 with no services."""
        ensemble = DabEnsemble()
        fig = FIG0_2(ensemble)
        buf = bytearray(32)

        status = fig.fill(buf, 32)
        assert status.complete_fig_transmitted is True


class TestFIG1_0:
    """Test FIG 1/0 (Ensemble label)."""

    def test_create_fig1_0(self) -> None:
        """Test creating FIG 1/0."""
        ensemble = DabEnsemble()
        fig = FIG1_0(ensemble)
        assert fig.fig_type() == 1
        assert fig.fig_extension() == 0

    def test_fig1_0_repetition_rate(self) -> None:
        """Test FIG 1/0 repetition rate."""
        ensemble = DabEnsemble()
        fig = FIG1_0(ensemble)
        assert fig.repetition_rate() == FIGRate.B

    def test_fig1_0_with_label(self) -> None:
        """Test FIG 1/0 with ensemble label."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.label = DabLabel(text="Test Ensemble", short_text="Test")

        fig = FIG1_0(ensemble)
        buf = bytearray(32)

        status = fig.fill(buf, 32)
        assert status.num_bytes_written == 22
        assert status.complete_fig_transmitted is True

        # Check header
        assert (buf[0] >> 5) == 1  # FIG type 1
        assert (buf[0] & 0x1F) == 21  # Length 21

    def test_fig1_0_without_label(self) -> None:
        """Test FIG 1/0 without label."""
        ensemble = DabEnsemble()
        ensemble.label = DabLabel(text="")

        fig = FIG1_0(ensemble)
        buf = bytearray(32)

        status = fig.fill(buf, 32)
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is True


class TestFIG1_1:
    """Test FIG 1/1 (Service labels)."""

    def test_create_fig1_1(self) -> None:
        """Test creating FIG 1/1."""
        ensemble = DabEnsemble()
        fig = FIG1_1(ensemble)
        assert fig.fig_type() == 1
        assert fig.fig_extension() == 1

    def test_fig1_1_with_services(self) -> None:
        """Test FIG 1/1 with service labels."""
        ensemble = DabEnsemble()

        service = DabService(uid="radio1", id=0x1234)
        service.label = DabLabel(text="Radio One", short_text="Radio1")
        ensemble.services.append(service)

        fig = FIG1_1(ensemble)
        buf = bytearray(64)

        status = fig.fill(buf, 64)
        assert status.num_bytes_written > 0
        assert status.complete_fig_transmitted is True


class TestFIGCarousel:
    """Test FIG carousel."""

    def test_create_carousel(self) -> None:
        """Test creating carousel."""
        carousel = FIGCarousel()
        assert carousel.get_fig_count() == 0

    def test_add_fig(self) -> None:
        """Test adding FIG to carousel."""
        carousel = FIGCarousel()
        ensemble = DabEnsemble()

        fig = FIG0_0(ensemble)
        carousel.add_fig(fig)

        assert carousel.get_fig_count() == 1

    def test_clear_carousel(self) -> None:
        """Test clearing carousel."""
        carousel = FIGCarousel()
        ensemble = DabEnsemble()

        carousel.add_fig(FIG0_0(ensemble))
        carousel.add_fig(FIG1_0(ensemble))

        assert carousel.get_fig_count() == 2

        carousel.clear()
        assert carousel.get_fig_count() == 0

    def test_fill_fib(self) -> None:
        """Test filling a FIB."""
        carousel = FIGCarousel()
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.label = DabLabel(text="Test")

        carousel.add_fig(FIG0_0(ensemble))
        carousel.add_fig(FIG1_0(ensemble))

        fib_data = bytearray(30)
        bytes_written = carousel.fill_fib(fib_data, max_size=30)

        # Should have written at least FIG 0/0
        assert bytes_written > 0
        assert bytes_written <= 30


class TestFICEncoder:
    """Test FIC encoder."""

    def test_create_fic_encoder(self) -> None:
        """Test creating FIC encoder."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.label = DabLabel(text="Test")

        encoder = FICEncoder(ensemble)
        assert encoder.carousel.get_fig_count() > 0

    def test_encode_fic_mode_i(self) -> None:
        """Test encoding FIC for Mode I."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.label = DabLabel(text="Test Ensemble")
        ensemble.transmission_mode = TransmissionMode.TM_I

        encoder = FICEncoder(ensemble)
        fic_data = encoder.encode_fic(frame_number=0)

        # Mode I FIC is 96 bytes
        assert len(fic_data) == 96

    def test_fic_includes_mandatory_figs(self) -> None:
        """Test that FIC includes mandatory FIGs."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.label = DabLabel(text="Test")

        # Add subchannel
        sub = DabSubchannel(uid="audio1", id=1, bitrate=128)
        ensemble.subchannels.append(sub)

        # Add service
        service = DabService(uid="radio1", id=0x1234)
        service.label = DabLabel(text="Radio One")
        ensemble.services.append(service)

        encoder = FICEncoder(ensemble)

        # Should have FIG 0/0, 0/1, 0/2, 1/0, 1/1
        assert encoder.carousel.get_fig_count() >= 4

    def test_update_ensemble(self) -> None:
        """Test updating ensemble configuration."""
        ensemble1 = DabEnsemble()
        ensemble1.id = 0x4FFF
        ensemble1.label = DabLabel(text="First")

        encoder = FICEncoder(ensemble1)
        initial_count = encoder.carousel.get_fig_count()

        # Update with new ensemble
        ensemble2 = DabEnsemble()
        ensemble2.id = 0x5000
        ensemble2.label = DabLabel(text="Second")

        encoder.update_ensemble(ensemble2)

        # Should still have FIGs (possibly different count)
        assert encoder.carousel.get_fig_count() >= initial_count - 1


class TestFICIntegration:
    """Integration tests for FIC generation."""

    def test_complete_fic_generation(self) -> None:
        """Test complete FIC generation with full ensemble."""
        ensemble = DabEnsemble()
        ensemble.id = 0x4FFF
        ensemble.ecc = 0xE1
        ensemble.label = DabLabel(text="Integration Test")

        # Add service
        service = DabService(uid="radio1", id=0x1234)
        service.label = DabLabel(text="Test Radio")
        ensemble.services.append(service)

        # Add subchannel
        sub = DabSubchannel(uid="audio1", id=1, bitrate=128)
        sub.start_address = 0
        ensemble.subchannels.append(sub)

        # Add component
        comp = DabComponent(uid="comp1")
        comp.service_id = service.id
        comp.subchannel_id = sub.id
        ensemble.components.append(comp)

        # Create encoder
        encoder = FICEncoder(ensemble)

        # Generate FIC for multiple frames
        for frame_num in range(10):
            fic_data = encoder.encode_fic(frame_num)
            assert len(fic_data) == 96
            assert fic_data != bytes(96)  # Should not be all zeros
