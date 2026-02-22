"""
Unit tests for ETI frame validator.

Tests Phase 3 of Enhanced ETI Output (Priority 5.5).
"""
import pytest
from dabmux.core.eti import EtiFrame
from dabmux.core.eti_validator import EtiValidator, ValidationResult
from dabmux.core.mux_elements import DabEnsemble, DabService, DabSubchannel, DabComponent
from dabmux.core.mux_elements import DabLabel, TransmissionMode, SubchannelType
from dabmux.mux import DabMultiplexer


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_default_result(self):
        """Test default validation result."""
        result = ValidationResult()

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.info == {}

    def test_add_error(self):
        """Test adding error to result."""
        result = ValidationResult()
        result.add_error("Test error")

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"

    def test_add_warning(self):
        """Test adding warning to result."""
        result = ValidationResult()
        result.add_warning("Test warning")

        assert result.valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_warning("Warning 1")
        result.info['test'] = 'value'

        data = result.to_dict()

        assert data['valid'] is False
        assert len(data['errors']) == 1
        assert len(data['warnings']) == 1
        assert data['info']['test'] == 'value'


class TestEtiValidator:
    """Tests for EtiValidator class."""

    def create_test_ensemble(self) -> DabEnsemble:
        """Create minimal test ensemble."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test", short_text="Test"),
            transmission_mode=TransmissionMode.TM_I
        )

        subchannel = DabSubchannel(
            uid='audio',
            id=0,
            type=SubchannelType.DABPlusAudio,
            bitrate=48
        )
        subchannel.protection.level = 3
        ensemble.subchannels.append(subchannel)

        service = DabService(
            uid='service',
            id=0x5001,
            label=DabLabel(text="Service", short_text="Svc")
        )
        ensemble.services.append(service)

        component = DabComponent(
            uid='component',
            service_id=0x5001,
            subchannel_id=0,
            label=DabLabel(text="Main", short_text="Main")
        )
        ensemble.components.append(component)

        return ensemble

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = EtiValidator()

        assert validator.frame_count == 0
        assert validator.last_fsync is None

    def test_validate_valid_frame(self):
        """Test validation of valid frame."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        frame = mux.generate_frame()
        validator = EtiValidator()

        result = validator.validate_frame(frame)

        assert result.valid is True
        assert len(result.errors) == 0
        assert 'fsync' in result.info
        assert 'mode' in result.info
        assert 'nst' in result.info

    def test_validate_fsync(self):
        """Test FSYNC validation."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)

        # Set valid FSYNC
        frame.sync.fsync = 0x073AB6

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert 'fsync' in result.info
        assert result.info['fsync'] == "0x073AB6"

    def test_validate_invalid_fsync(self):
        """Test validation with invalid FSYNC."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)

        # Set invalid FSYNC
        frame.sync.fsync = 0x123456

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert result.valid is False
        assert len(result.errors) > 0
        assert "Invalid FSYNC" in result.errors[0]

    def test_validate_fsync_alternation(self):
        """Test FSYNC alternation validation."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        validator = EtiValidator()

        # Generate first frame (should be 0x073AB6)
        frame1 = mux.generate_frame()
        result1 = validator.validate_frame(frame1)
        assert result1.valid is True

        # Generate second frame (should be 0xF8C549)
        frame2 = mux.generate_frame()
        result2 = validator.validate_frame(frame2)
        assert result2.valid is True
        assert len(result2.warnings) == 0  # No alternation warning

    def test_validate_err_field(self):
        """Test ERR field validation."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)
        frame.sync.err = 0xFF  # No errors

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert 'err' in result.info
        assert result.info['err'] == "0xFF"

    def test_validate_err_field_with_errors(self):
        """Test ERR field with error indication."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)
        frame.sync.err = 0xFE  # Some error

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert len(result.warnings) > 0
        assert "ERR field" in result.warnings[0]

    def test_validate_mode(self):
        """Test transmission mode validation."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)
        frame.fc.mid = 1  # Mode I

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert 'mode' in result.info
        assert result.info['mode'] == 1

    def test_validate_invalid_mode(self):
        """Test validation with invalid mode."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)
        frame.fc.mid = 5  # Invalid mode

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert result.valid is False
        assert any("Invalid transmission mode" in err for err in result.errors)

    def test_validate_tist_present(self):
        """Test TIST validation when present."""
        frame = EtiFrame.create_empty(mode=1, with_tist=True)
        frame.tist.tist = 0x12345678

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert result.info['tist_present'] is True
        assert result.info['tist_value'] == 0x12345678
        assert result.info['tist_hex'] == "0x12345678"
        assert 'tist_seconds' in result.info

    def test_validate_tist_absent(self):
        """Test TIST validation when absent."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert result.info['tist_present'] is False

    def test_validate_tist_zero_warning(self):
        """Test warning for zero TIST value."""
        frame = EtiFrame.create_empty(mode=1, with_tist=True)
        frame.tist.tist = 0

        validator = EtiValidator()
        result = validator.validate_frame(frame)

        assert len(result.warnings) > 0
        assert any("TIST is zero" in warn for warn in result.warnings)

    def test_calculate_expected_fl(self):
        """Test FL calculation."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        frame = mux.generate_frame()
        validator = EtiValidator()

        expected_fl = validator._calculate_expected_fl(frame)

        assert expected_fl > 0
        assert isinstance(expected_fl, int)

    def test_validate_crc(self):
        """Test CRC validation (placeholder)."""
        frame = EtiFrame.create_empty(mode=1, with_tist=False)
        validator = EtiValidator()

        result = validator.validate_crc(frame)

        assert 'eoh_crc_valid' in result
        assert 'eof_crc_valid' in result
        assert 'note' in result

    def test_validator_reset(self):
        """Test validator reset."""
        validator = EtiValidator()
        validator.frame_count = 10
        validator.last_fsync = 0x073AB6

        validator.reset()

        assert validator.frame_count == 0
        assert validator.last_fsync is None

    def test_validate_multiple_frames(self):
        """Test validating multiple frames."""
        ensemble = self.create_test_ensemble()
        mux = DabMultiplexer(ensemble)

        validator = EtiValidator()

        for i in range(5):
            frame = mux.generate_frame()
            result = validator.validate_frame(frame)

            assert result.valid is True
            assert validator.frame_count == i + 1
