"""
Unit tests for ETI metadata.

Tests Phase 3 of Enhanced ETI Output (Priority 5.5).
"""
import pytest
from datetime import datetime
from dabmux.core.eti_metadata import EtiMetadata
from dabmux.core.mux_elements import DabEnsemble, DabLabel, TransmissionMode


class TestEtiMetadata:
    """Tests for EtiMetadata class."""

    def test_default_metadata(self):
        """Test default metadata values."""
        metadata = EtiMetadata()

        assert metadata.generator == "python-dabmux"
        assert metadata.version == "0.7.0"
        assert metadata.ensemble_id == 0
        assert metadata.ensemble_label == ""
        assert metadata.ensemble_ecc == 0
        assert metadata.transmission_mode == 1
        assert metadata.source == ""
        assert metadata.format == "standard"
        assert metadata.tist_enabled is False
        assert metadata.frame_count is None
        assert isinstance(metadata.creation_time, datetime)

    def test_metadata_with_values(self):
        """Test metadata with custom values."""
        creation_time = datetime(2026, 2, 20, 12, 0, 0)

        metadata = EtiMetadata(
            creation_time=creation_time,
            ensemble_id=0xCE15,
            ensemble_label="Test Ensemble",
            ensemble_ecc=0xE1,
            transmission_mode=1,
            source="file",
            format="ni",
            tist_enabled=True,
            frame_count=1000
        )

        assert metadata.ensemble_id == 0xCE15
        assert metadata.ensemble_label == "Test Ensemble"
        assert metadata.ensemble_ecc == 0xE1
        assert metadata.transmission_mode == 1
        assert metadata.source == "file"
        assert metadata.format == "ni"
        assert metadata.tist_enabled is True
        assert metadata.frame_count == 1000
        assert metadata.creation_time == creation_time

    def test_to_comment(self):
        """Test comment string generation."""
        metadata = EtiMetadata(
            ensemble_id=0xCE15,
            ensemble_label="Test",
            ensemble_ecc=0xE1,
            transmission_mode=1,
            tist_enabled=True,
            frame_count=100
        )

        comment = metadata.to_comment()

        assert "python-dabmux" in comment
        assert "Test" in comment
        assert "0xCE15" in comment
        assert "0xE1" in comment
        assert "Mode: 1" in comment
        assert "TIST: Enabled" in comment
        assert "Frames: 100" in comment

    def test_to_dict(self):
        """Test dictionary conversion."""
        metadata = EtiMetadata(
            ensemble_id=0xCE15,
            ensemble_label="Test",
            ensemble_ecc=0xE1,
            transmission_mode=1,
            format="ni",
            tist_enabled=True,
            source="udp",
            frame_count=500
        )

        data = metadata.to_dict()

        assert isinstance(data, dict)
        assert data['generator'] == "python-dabmux"
        assert data['version'] == "0.7.0"
        assert data['ensemble']['id'] == "0xCE15"
        assert data['ensemble']['label'] == "Test"
        assert data['ensemble']['ecc'] == "0xE1"
        assert data['ensemble']['mode'] == 1
        assert data['format'] == "ni"
        assert data['tist_enabled'] is True
        assert data['source'] == "udp"
        assert data['frame_count'] == 500

    def test_from_ensemble(self):
        """Test metadata creation from ensemble."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble", short_text="Test"),
            transmission_mode=TransmissionMode.TM_I,
            enable_tist=True
        )

        metadata = EtiMetadata.from_ensemble(ensemble, frame_count=1000)

        assert metadata.ensemble_id == 0xCE15
        assert metadata.ensemble_label == "Test Ensemble"
        assert metadata.ensemble_ecc == 0xE1
        assert metadata.transmission_mode == 1
        assert metadata.tist_enabled is True
        assert metadata.frame_count == 1000
        assert metadata.format == "standard"

    def test_from_ensemble_without_frame_count(self):
        """Test metadata creation without frame count."""
        ensemble = DabEnsemble(
            id=0x1234,
            ecc=0x56,
            label=DabLabel(text="Test", short_text="Test"),
            transmission_mode=TransmissionMode.TM_II
        )

        metadata = EtiMetadata.from_ensemble(ensemble)

        assert metadata.ensemble_id == 0x1234
        assert metadata.ensemble_ecc == 0x56
        assert metadata.transmission_mode == 2
        assert metadata.tist_enabled is False
        assert metadata.frame_count is None
