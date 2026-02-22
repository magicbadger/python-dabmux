"""
ETI frame validation against ETSI EN 300 799.

Per Phase 3 of Enhanced ETI Output (Priority 5.5).
"""
from typing import Dict, List
import structlog
from dabmux.core.eti import EtiFrame


logger = structlog.get_logger()


class ValidationResult:
    """Result of frame validation."""

    def __init__(self):
        self.valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: Dict[str, any] = {}

    def add_error(self, message: str):
        """Add validation error."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'valid': self.valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info
        }


class EtiValidator:
    """
    Validates ETI frames for standards compliance.

    Checks frame structure against ETSI EN 300 799 specification.
    """

    def __init__(self):
        self.frame_count = 0
        self.last_fsync = None

    def validate_frame(self, frame: EtiFrame) -> ValidationResult:
        """
        Comprehensive frame validation.

        Args:
            frame: EtiFrame to validate

        Returns:
            ValidationResult with errors, warnings, and info
        """
        result = ValidationResult()

        # 1. FSYNC validation
        self._validate_fsync(frame, result)

        # 2. ERR field validation
        self._validate_err(frame, result)

        # 3. Frame length validation
        self._validate_frame_length(frame, result)

        # 4. NST validation
        self._validate_nst(frame, result)

        # 5. FIC validation
        self._validate_fic(frame, result)

        # 6. Transmission mode validation
        self._validate_mode(frame, result)

        # 7. MST size validation
        self._validate_mst(frame, result)

        # 8. TIST validation
        self._validate_tist(frame, result)

        # 9. Subchannel validation
        result.info['num_subchannels'] = len(frame.stc_headers)

        self.frame_count += 1
        return result

    def _validate_fsync(self, frame: EtiFrame, result: ValidationResult):
        """Validate FSYNC field."""
        valid_fsyncs = [0x073AB6, 0xF8C549]

        if frame.sync.fsync not in valid_fsyncs:
            result.add_error(
                f"Invalid FSYNC: 0x{frame.sync.fsync:06X} "
                f"(expected 0x073AB6 or 0xF8C549)"
            )
        else:
            result.info['fsync'] = f"0x{frame.sync.fsync:06X}"

            # Check FSYNC alternation
            if self.last_fsync is not None:
                if frame.sync.fsync == self.last_fsync:
                    result.add_warning(
                        f"FSYNC did not alternate (repeated 0x{frame.sync.fsync:06X})"
                    )

            self.last_fsync = frame.sync.fsync

    def _validate_err(self, frame: EtiFrame, result: ValidationResult):
        """Validate ERR field."""
        if frame.sync.err != 0xFF:
            result.add_warning(
                f"ERR field is 0x{frame.sync.err:02X} (expected 0xFF for no errors)"
            )
        result.info['err'] = f"0x{frame.sync.err:02X}"

    def _validate_frame_length(self, frame: EtiFrame, result: ValidationResult):
        """Validate FL (Frame Length) field."""
        expected_fl = self._calculate_expected_fl(frame)

        result.info['fl'] = frame.fc.fl
        result.info['expected_fl'] = expected_fl

        if frame.fc.fl != expected_fl:
            result.add_error(
                f"FL mismatch: {frame.fc.fl} != {expected_fl} (expected)"
            )

    def _calculate_expected_fl(self, frame: EtiFrame) -> int:
        """
        Calculate expected FL value per ETSI EN 300 799.

        FL = NST + FIC_words + MST_words + EOF_words
        where NST = number of STC headers

        Args:
            frame: EtiFrame to calculate FL for

        Returns:
            Expected FL value in 32-bit words
        """
        stc_words = frame.fc.nst  # Each STC is 1 word
        fic_words = len(frame.fic_data) // 4 if frame.fc.ficf else 0  # FIC bytes / 4
        mst_words = (len(frame.subchannel_data) + 3) // 4  # MST bytes / 4, rounded up
        eof_words = 1  # EOF is 1 word
        return stc_words + fic_words + mst_words + eof_words

    def _validate_nst(self, frame: EtiFrame, result: ValidationResult):
        """Validate NST (Number of Streams) field."""
        actual_stc_count = len(frame.stc_headers)

        result.info['nst'] = frame.fc.nst

        if frame.fc.nst != actual_stc_count:
            result.add_error(
                f"NST={frame.fc.nst} but {actual_stc_count} STC headers present"
            )

    def _validate_fic(self, frame: EtiFrame, result: ValidationResult):
        """Validate FIC field."""
        if frame.fc.ficf:
            expected_fic_size = 96  # FIC is always 96 bytes when present

            if len(frame.fic_data) != expected_fic_size:
                result.add_error(
                    f"FICF=1 but FIC data is {len(frame.fic_data)} bytes "
                    f"(expected {expected_fic_size})"
                )

            result.info['fic_present'] = True
            result.info['fic_size'] = len(frame.fic_data)
        else:
            result.info['fic_present'] = False

    def _validate_mode(self, frame: EtiFrame, result: ValidationResult):
        """Validate transmission mode (MID) field."""
        valid_modes = [1, 2, 3, 4]

        result.info['mode'] = frame.fc.mid

        if frame.fc.mid not in valid_modes:
            result.add_error(
                f"Invalid transmission mode: {frame.fc.mid} (must be 1-4)"
            )

    def _validate_mst(self, frame: EtiFrame, result: ValidationResult):
        """Validate MST (Main Service Channel) size."""
        expected_mst_size = sum(stc.stl * 8 for stc in frame.stc_headers)
        actual_mst_size = len(frame.subchannel_data)

        result.info['mst_size'] = actual_mst_size
        result.info['expected_mst_size'] = expected_mst_size

        if actual_mst_size != expected_mst_size:
            result.add_error(
                f"MST size mismatch: {actual_mst_size} != {expected_mst_size} bytes"
            )

    def _validate_tist(self, frame: EtiFrame, result: ValidationResult):
        """Validate TIST (Timestamp) field."""
        if frame.tist:
            result.info['tist_present'] = True
            result.info['tist_value'] = frame.tist.tist
            result.info['tist_hex'] = f"0x{frame.tist.tist:08X}"

            # Calculate timestamp in seconds (modulo 2^32)
            tist_seconds = frame.tist.tist / 16384000.0
            result.info['tist_seconds'] = round(tist_seconds, 6)

            # Validate TIST is within reasonable range
            if frame.tist.tist == 0:
                result.add_warning("TIST is zero (may indicate uninitialized timestamp)")

        else:
            result.info['tist_present'] = False

    def validate_crc(self, frame: EtiFrame) -> Dict:
        """
        Validate CRC fields (EOH and EOF).

        Note: Actual CRC validation would require recalculating
        the CRC from frame data and comparing with stored values.
        This is a placeholder for future implementation.

        Args:
            frame: EtiFrame to validate

        Returns:
            Dictionary with CRC validation results
        """
        return {
            'eoh_crc_valid': True,  # Placeholder
            'eof_crc_valid': True,  # Placeholder
            'note': 'CRC validation not yet implemented'
        }

    def reset(self):
        """Reset validator state for new validation session."""
        self.frame_count = 0
        self.last_fsync = None
