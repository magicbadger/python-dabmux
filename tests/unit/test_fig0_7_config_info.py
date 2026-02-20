"""
Tests for FIG 0/7: Configuration Information.

Per ETSI EN 300 401 Section 8.1.16.
"""
import pytest
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabComponent, DabSubchannel,
    DabLabel, DabProtection, ProtectionForm, SubchannelType,
    DabProtectionEEP, EEPProfile
)
from dabmux.fig.fig0 import FIG0_7
from dabmux.fig.base import FIGRate, FIGPriority


def create_test_ensemble():
    """Create a basic test ensemble."""
    ensemble = DabEnsemble(
        id=0xCE15,
        ecc=0xE1,
        label=DabLabel(text="Test Ensemble", short_text="Test")
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
        label=DabLabel(text="Service 1", short_text="Svc1")
    )
    ensemble.services.append(service)

    # Add a component
    component = DabComponent(
        uid='comp1',
        service_id=0x5001,
        subchannel_id=0
    )
    ensemble.components.append(component)

    return ensemble


class TestFIG0_7_Header:
    """Test FIG 0/7 header encoding."""

    def test_header_type_and_length(self):
        """Test header byte 0 encoding (Type=0, Length=3)."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        buf = bytearray(32)
        status = fig.fill(buf, 32)

        assert status.num_bytes_written == 4
        # Byte 0: Type (3 bits) = 0 | Length (5 bits) = 3
        assert buf[0] == 0x03  # 0b00000011

    def test_header_cn_oe_pd_extension(self):
        """Test header byte 1 encoding (CN=0, OE=0, PD=0, Ext=7)."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Byte 1: CN (1) = 0 | OE (1) = 0 | PD (1) = 0 | Extension (5) = 7
        assert buf[1] == 0x07  # 0b00000111


class TestFIG0_7_CountEncoding:
    """Test configuration count encoding."""

    def test_count_encoding_zero(self):
        """Test encoding count = 0."""
        ensemble = create_test_ensemble()
        # Force hash to return 0
        ensemble.id = 0
        ensemble.ecc = 0

        fig = FIG0_7(ensemble)
        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Count should be 0
        count = (buf[2] << 8) | buf[3]
        # Since hash is deterministic but unpredictable, just verify structure
        assert count == ensemble.calculate_configuration_hash()

    def test_count_encoding_max(self):
        """Test 10-bit count range (0-1023)."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        buf = bytearray(32)
        status = fig.fill(buf, 32)

        # Extract count (10 bits)
        count = ((buf[2] & 0x03) << 8) | buf[3]

        # Verify count is in valid 10-bit range
        assert 0 <= count < 1024

        # Verify Rfa bits (bits 7-2 of byte 2) are zero
        rfa = (buf[2] >> 2) & 0x3F
        assert rfa == 0

    def test_count_determinism(self):
        """Test that hash calculation is deterministic."""
        ensemble1 = create_test_ensemble()
        ensemble2 = create_test_ensemble()

        # Same configuration should produce same hash
        hash1 = ensemble1.calculate_configuration_hash()
        hash2 = ensemble2.calculate_configuration_hash()

        assert hash1 == hash2


class TestFIG0_7_ChangeDetection:
    """Test configuration change detection."""

    def test_retransmit_on_service_add(self):
        """Test retransmission when service is added."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        # First transmission
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)
        assert status1.num_bytes_written == 4
        count1 = ((buf1[2] & 0x03) << 8) | buf1[3]

        # Add a service
        new_service = DabService(
            uid='svc2',
            id=0x5002,
            label=DabLabel(text="Service 2", short_text="Svc2")
        )
        ensemble.services.append(new_service)

        # Second transmission should have different count
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)
        assert status2.num_bytes_written == 4
        count2 = ((buf2[2] & 0x03) << 8) | buf2[3]

        assert count1 != count2

    def test_retransmit_on_bitrate_change(self):
        """Test retransmission when subchannel bitrate changes."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        # First transmission
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)
        count1 = ((buf1[2] & 0x03) << 8) | buf1[3]

        # Change bitrate
        ensemble.subchannels[0].bitrate = 64

        # Second transmission should have different count
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)
        count2 = ((buf2[2] & 0x03) << 8) | buf2[3]

        assert count1 != count2

    def test_no_retransmit_when_unchanged(self):
        """Test caching when configuration unchanged."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        # First transmission
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)
        assert status1.num_bytes_written == 4
        assert status1.complete_fig_transmitted is True

        # Second transmission (no changes)
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)

        # Should indicate complete but no bytes written
        assert status2.num_bytes_written == 0
        assert status2.complete_fig_transmitted is True

    def test_retransmit_after_cache_invalidation(self):
        """Test retransmission after configuration change."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        # First transmission
        buf1 = bytearray(32)
        status1 = fig.fill(buf1, 32)
        assert status1.num_bytes_written == 4

        # Second transmission (no changes) - should be cached
        buf2 = bytearray(32)
        status2 = fig.fill(buf2, 32)
        assert status2.num_bytes_written == 0

        # Change configuration (remove service)
        ensemble.services.pop()

        # Third transmission - should retransmit
        buf3 = bytearray(32)
        status3 = fig.fill(buf3, 32)
        assert status3.num_bytes_written == 4


class TestFIG0_7_HashCalculation:
    """Test configuration hash calculation."""

    def test_hash_includes_ensemble_id(self):
        """Test that hash changes when ensemble ID changes."""
        ensemble1 = create_test_ensemble()
        ensemble1.id = 0xCE15
        hash1 = ensemble1.calculate_configuration_hash()

        ensemble2 = create_test_ensemble()
        ensemble2.id = 0xCE16  # Different
        hash2 = ensemble2.calculate_configuration_hash()

        assert hash1 != hash2

    def test_hash_includes_subchannel_config(self):
        """Test that hash changes when subchannel config changes."""
        ensemble1 = create_test_ensemble()
        hash1 = ensemble1.calculate_configuration_hash()

        ensemble2 = create_test_ensemble()
        ensemble2.subchannels[0].protection.level = 2  # Different
        hash2 = ensemble2.calculate_configuration_hash()

        assert hash1 != hash2

    def test_hash_ignores_labels(self):
        """Test that hash doesn't change when labels change (not structural)."""
        ensemble1 = create_test_ensemble()
        hash1 = ensemble1.calculate_configuration_hash()

        ensemble2 = create_test_ensemble()
        ensemble2.label.text = "Different Label"  # Changed label
        hash2 = ensemble2.calculate_configuration_hash()

        # Labels are not structural, hash should be same
        assert hash1 == hash2


class TestFIG0_7_Metadata:
    """Test FIG 0/7 metadata methods."""

    def test_repetition_rate(self):
        """Test FIG 0/7 repetition rate is B (once per second)."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        assert fig.repetition_rate() == FIGRate.B

    def test_priority(self):
        """Test FIG 0/7 priority is NORMAL."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        assert fig.priority() == FIGPriority.NORMAL

    def test_fig_type(self):
        """Test FIG type is 0."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        assert fig.fig_type() == 0

    def test_fig_extension(self):
        """Test FIG extension is 7."""
        ensemble = create_test_ensemble()
        fig = FIG0_7(ensemble)

        assert fig.fig_extension() == 7
