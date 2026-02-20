"""
Tests for FIG 0/14: FEC Sub-channel Organization.

Per ETSI EN 300 401 Section 8.1.5.
"""
import pytest
from dabmux.fig.fig0 import FIG0_14
from dabmux.fig.base import FIGRate, FIGPriority
from dabmux.core.mux_elements import (
    DabEnsemble,
    DabSubchannel,
    DabLabel,
    DabProtection,
    SubchannelType,
    ProtectionForm,
    DabProtectionEEP,
    EEPProfile,
)


def create_test_ensemble() -> DabEnsemble:
    """Create a test ensemble with various subchannels."""
    ensemble = DabEnsemble(
        id=0xCE15,
        label=DabLabel(text="Test Ensemble"),
        ecc=0xE1,
    )
    return ensemble


def create_subchannel(subchan_id: int, fec_scheme: int = 0) -> DabSubchannel:
    """Create a test subchannel with optional FEC."""
    protection = DabProtection(
        form=ProtectionForm.EEP,
        level=2,  # EEP 3-A
        eep=DabProtectionEEP(profile=EEPProfile.EEP_A)
    )
    return DabSubchannel(
        uid=f'subchan_{subchan_id}',
        id=subchan_id,
        type=SubchannelType.Packet,
        start_address=0,
        bitrate=64,
        protection=protection,
        input_uri='file://test.bin',
        fec_scheme=fec_scheme
    )


class TestFIG0_14:
    """Tests for FIG 0/14: FEC Sub-channel Organization."""

    def test_header_encoding(self) -> None:
        """Test FIG 0/14 header encoding."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(0, fec_scheme=1))

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 3  # 2 byte header + 1 byte data
        assert status.complete_fig_transmitted is True

        # Check header
        # Byte 0: Type (3 bits) = 0, Length (5 bits) = 2 (1 data byte + 1 header byte)
        assert buf[0] == 0x02  # (0 << 5) | 2

        # Byte 1: CN=0, OE=0, PD=0, Extension=14
        assert buf[1] == 0x0E  # (0 << 7) | (0 << 6) | (0 << 5) | 14

    def test_single_fec_subchannel(self) -> None:
        """Test encoding single subchannel with FEC."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(5, fec_scheme=1))

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 3
        assert status.complete_fig_transmitted is True

        # Byte 2: SubChId (bits 7-2) | FEC Scheme (bits 1-0)
        # SubChId=5, FEC=1 → (5 << 2) | 1 = 0x15
        assert buf[2] == 0x15

    def test_multiple_fec_subchannels(self) -> None:
        """Test encoding multiple subchannels with FEC."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(0, fec_scheme=1))
        ensemble.subchannels.append(create_subchannel(1, fec_scheme=1))
        ensemble.subchannels.append(create_subchannel(2, fec_scheme=1))

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 5  # 2 header + 3 data bytes
        assert status.complete_fig_transmitted is True

        # Check header: length = 4 (3 data bytes + 1 header byte)
        assert buf[0] == 0x04

        # Check FEC entries
        assert buf[2] == 0x01  # SubChId=0, FEC=1
        assert buf[3] == 0x05  # SubChId=1, FEC=1
        assert buf[4] == 0x09  # SubChId=2, FEC=1

    def test_fec_scheme_encoding(self) -> None:
        """Test different FEC scheme values."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(0, fec_scheme=1))  # RS(204,188)
        ensemble.subchannels.append(create_subchannel(1, fec_scheme=2))  # Reserved
        ensemble.subchannels.append(create_subchannel(2, fec_scheme=3))  # Reserved

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 5
        assert buf[2] == 0x01  # SubChId=0, FEC=1
        assert buf[3] == 0x06  # SubChId=1, FEC=2
        assert buf[4] == 0x0B  # SubChId=2, FEC=3

    def test_no_fec_subchannels(self) -> None:
        """Test behavior when no subchannels have FEC enabled."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(0, fec_scheme=0))
        ensemble.subchannels.append(create_subchannel(1, fec_scheme=0))

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should return immediately with no bytes written
        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is True

    def test_mixed_fec_no_fec_subchannels(self) -> None:
        """Test that only FEC-enabled subchannels are included."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(0, fec_scheme=0))  # No FEC
        ensemble.subchannels.append(create_subchannel(1, fec_scheme=1))  # Has FEC
        ensemble.subchannels.append(create_subchannel(2, fec_scheme=0))  # No FEC
        ensemble.subchannels.append(create_subchannel(3, fec_scheme=1))  # Has FEC

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Should only include subchannels 1 and 3
        assert status.num_bytes_written == 4  # 2 header + 2 data bytes
        assert buf[0] == 0x03  # Length = 3 (2 data + 1 header)
        assert buf[2] == 0x05  # SubChId=1, FEC=1
        assert buf[3] == 0x0D  # SubChId=3, FEC=1

    def test_iterative_transmission(self) -> None:
        """Test iterative transmission across multiple calls."""
        ensemble = create_test_ensemble()
        # Add 6 FEC subchannels (so we can split into 3 calls cleanly)
        for i in range(6):
            ensemble.subchannels.append(create_subchannel(i, fec_scheme=1))

        fig = FIG0_14(ensemble)

        # First call with limited space (header + 2 entries)
        buf = bytearray(32)
        status = fig.fill(buf, 4)  # Only space for header + 2 entries

        assert status.num_bytes_written == 4
        assert status.complete_fig_transmitted is False  # More data pending
        assert buf[0] == 0x03  # Length = 3
        assert buf[2] == 0x01  # SubChId=0
        assert buf[3] == 0x05  # SubChId=1

        # Second call should continue from subchannel 2
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 4)  # Space for header + 2 more entries

        assert status2.num_bytes_written == 4
        assert status2.complete_fig_transmitted is False  # Still more pending
        assert buf2[2] == 0x09  # SubChId=2
        assert buf2[3] == 0x0D  # SubChId=3

        # Third call should transmit remaining and complete
        buf3 = bytearray(32)
        status3 = fig.fill(buf3, 32)

        assert status3.num_bytes_written == 4  # Last 2 subchannels
        assert status3.complete_fig_transmitted is True  # All done
        assert buf3[2] == 0x11  # SubChId=4
        assert buf3[3] == 0x15  # SubChId=5

        # Fourth call should start over from beginning
        buf4 = bytearray(32)
        status4 = fig.fill(buf4, 32)

        assert status4.num_bytes_written == 8  # All 6 subchannels
        assert status4.complete_fig_transmitted is True
        assert buf4[0] == 0x07  # Length = 7 (6 data + 1 header)

    def test_insufficient_space(self) -> None:
        """Test behavior with insufficient buffer space."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(0, fec_scheme=1))

        fig = FIG0_14(ensemble)

        # Not enough space for even the header
        buf = bytearray(32)
        status = fig.fill(buf, 1)

        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is False

    def test_subchannel_id_range(self) -> None:
        """Test subchannel ID encoding (6 bits, 0-63)."""
        ensemble = create_test_ensemble()
        ensemble.subchannels.append(create_subchannel(0, fec_scheme=1))    # Min
        ensemble.subchannels.append(create_subchannel(31, fec_scheme=1))   # Mid
        ensemble.subchannels.append(create_subchannel(63, fec_scheme=1))   # Max

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 5
        assert buf[2] == 0x01   # SubChId=0, FEC=1 → (0 << 2) | 1
        assert buf[3] == 0x7D   # SubChId=31, FEC=1 → (31 << 2) | 1
        assert buf[4] == 0xFD   # SubChId=63, FEC=1 → (63 << 2) | 1

    def test_repetition_rate(self) -> None:
        """Test that FIG 0/14 has correct repetition rate."""
        ensemble = create_test_ensemble()
        fig = FIG0_14(ensemble)

        assert fig.repetition_rate() == FIGRate.B  # Once per second

    def test_priority(self) -> None:
        """Test that FIG 0/14 has correct priority."""
        ensemble = create_test_ensemble()
        fig = FIG0_14(ensemble)

        assert fig.priority() == FIGPriority.NORMAL

    def test_fig_type_extension(self) -> None:
        """Test FIG type and extension values."""
        ensemble = create_test_ensemble()
        fig = FIG0_14(ensemble)

        assert fig.fig_type() == 0
        assert fig.fig_extension() == 14

    def test_empty_ensemble(self) -> None:
        """Test with ensemble that has no subchannels."""
        ensemble = create_test_ensemble()

        fig = FIG0_14(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 0
        assert status.complete_fig_transmitted is True
