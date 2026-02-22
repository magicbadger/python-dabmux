#!/usr/bin/env python3
"""
ETI File Validator.

Validates ETI (Ensemble Transport Interface) files for compliance with
ETSI EN 300 799 specification.

Checks:
- FSYNC alternation
- CRC verification (FIB, EOH, EOF)
- Frame length (FL) calculation
- FIC structure
- MST structure
- Compliance with ETSI standards

Usage:
    python validate_eti.py -i input.eti [--verbose] [--report output.txt]
"""
import argparse
import struct
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check: str
    status: str  # 'OK', 'WARNING', 'ERROR'
    message: str
    frame_number: Optional[int] = None


class ETIValidator:
    """Validates ETI files against ETSI EN 300 799."""

    FRAME_SIZE = 6144  # ETI frame size (padded)
    FSYNC_1 = 0x073AB6
    FSYNC_2 = 0xF8C549

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[ValidationResult] = []

    def log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            print(f"[DEBUG] {message}")

    def add_result(self, check: str, status: str, message: str, frame: Optional[int] = None):
        """Add validation result."""
        result = ValidationResult(check, status, message, frame)
        self.results.append(result)

        # Print immediately if verbose
        if self.verbose:
            frame_str = f" (frame {frame})" if frame is not None else ""
            print(f"[{status}] {check}{frame_str}: {message}")

    def crc16(self, data: bytes) -> int:
        """Calculate CRC-16-CCITT with inversion."""
        crc = 0xFFFF
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc ^ 0xFFFF  # Invert per DAB standard

    def validate_sync(self, data: bytes, frame_num: int, prev_fsync: Optional[int]) -> int:
        """Validate SYNC field."""
        err = data[0]
        fsync = struct.unpack('>I', data[0:4])[0] & 0xFFFFFF

        # Check ERR byte
        if err != 0xFF:
            self.add_result('SYNC.ERR', 'WARNING',
                          f"ERR byte is 0x{err:02X} (expected 0xFF)", frame_num)

        # Check FSYNC values
        if fsync not in [self.FSYNC_1, self.FSYNC_2]:
            self.add_result('SYNC.FSYNC', 'ERROR',
                          f"Invalid FSYNC: 0x{fsync:06X}", frame_num)
            return fsync

        # Check FSYNC alternation
        if prev_fsync is not None and fsync == prev_fsync:
            self.add_result('SYNC.FSYNC', 'ERROR',
                          f"FSYNC not alternating (same as previous: 0x{fsync:06X})", frame_num)

        self.log(f"Frame {frame_num}: FSYNC = 0x{fsync:06X}")
        return fsync

    def validate_fc(self, data: bytes, frame_num: int) -> Tuple[int, int, int]:
        """Validate Frame Characterization (FC) field."""
        fct = data[4]
        nst = data[5] & 0x7F
        fl = struct.unpack('>H', data[6:8])[0] & 0x07FF

        self.log(f"Frame {frame_num}: FCT={fct}, NST={nst}, FL={fl}")

        # Check FCT range (0-249)
        if fct > 249:
            self.add_result('FC.FCT', 'WARNING',
                          f"FCT = {fct} (should be 0-249)", frame_num)

        # Check NST range (0-64)
        if nst > 64:
            self.add_result('FC.NST', 'ERROR',
                          f"NST = {nst} (maximum is 64)", frame_num)

        return fct, nst, fl

    def validate_eoh(self, data: bytes, frame_num: int, nst: int) -> bool:
        """Validate End of Header (EOH) CRC."""
        # EOH is after FC (4 bytes) + STC (NST * 4 bytes)
        eoh_offset = 8 + (nst * 4)
        eoh_data = data[4:eoh_offset]  # FC + STC
        eoh_crc_offset = eoh_offset

        # Read EOH CRC
        eoh_crc_actual = struct.unpack('>H', data[eoh_crc_offset:eoh_crc_offset + 2])[0]

        # Calculate expected CRC
        eoh_crc_expected = self.crc16(eoh_data)

        if eoh_crc_actual != eoh_crc_expected:
            self.add_result('EOH.CRC', 'ERROR',
                          f"CRC mismatch: expected 0x{eoh_crc_expected:04X}, got 0x{eoh_crc_actual:04X}",
                          frame_num)
            return False

        self.log(f"Frame {frame_num}: EOH CRC = 0x{eoh_crc_actual:04X} (OK)")
        return True

    def validate_fic(self, data: bytes, frame_num: int, nst: int) -> bool:
        """Validate Fast Information Channel (FIC)."""
        # FIC starts after EOH
        fic_offset = 8 + (nst * 4) + 4
        fic_data = data[fic_offset:fic_offset + 96]

        if len(fic_data) != 96:
            self.add_result('FIC.SIZE', 'ERROR',
                          f"FIC size is {len(fic_data)} (expected 96)", frame_num)
            return False

        # Validate FIBs (3 FIBs of 32 bytes each)
        for fib_num in range(3):
            fib_offset = fib_num * 32
            fib_data = fic_data[fib_offset:fib_offset + 30]  # 30 bytes data
            fib_crc_actual = struct.unpack('>H', fic_data[30:32])[0]

            # Calculate expected CRC
            fib_crc_expected = self.crc16(fib_data)

            if fib_crc_actual != fib_crc_expected:
                self.add_result('FIC.FIB_CRC', 'ERROR',
                              f"FIB {fib_num} CRC mismatch: expected 0x{fib_crc_expected:04X}, got 0x{fib_crc_actual:04X}",
                              frame_num)
                return False

        self.log(f"Frame {frame_num}: FIC CRCs OK (3 FIBs)")
        return True

    def validate_eof(self, data: bytes, frame_num: int, nst: int, fl: int) -> bool:
        """Validate End of Frame (EOF) CRC."""
        # Calculate MST offset and size
        mst_offset = 8 + (nst * 4) + 4 + 96  # FC + STC + EOH + FIC
        fl_bytes = fl * 4  # FL is in words (32-bit)
        fic_offset = 8 + (nst * 4) + 4
        mst_size = fl_bytes - (fic_offset - 8) - 4  # FL includes STC + FIC + MST + EOF

        # Get MST data
        mst_data = data[mst_offset:mst_offset + mst_size]

        # EOF is after MST
        eof_offset = mst_offset + mst_size
        eof_crc_actual = struct.unpack('>H', data[eof_offset:eof_offset + 2])[0]

        # Calculate expected CRC
        eof_crc_expected = self.crc16(mst_data)

        if eof_crc_actual != eof_crc_expected:
            self.add_result('EOF.CRC', 'ERROR',
                          f"MST CRC mismatch: expected 0x{eof_crc_expected:04X}, got 0x{eof_crc_actual:04X}",
                          frame_num)
            self.log(f"MST offset: {mst_offset}, size: {mst_size}, EOF offset: {eof_offset}")
            return False

        self.log(f"Frame {frame_num}: EOF CRC = 0x{eof_crc_actual:04X} (OK)")
        return True

    def validate_frame(self, frame_data: bytes, frame_num: int, prev_fsync: Optional[int]) -> Optional[int]:
        """Validate a single ETI frame."""
        if len(frame_data) != self.FRAME_SIZE:
            self.add_result('FRAME.SIZE', 'ERROR',
                          f"Frame size is {len(frame_data)} (expected {self.FRAME_SIZE})", frame_num)
            return None

        # Validate SYNC
        fsync = self.validate_sync(frame_data, frame_num, prev_fsync)

        # Validate FC
        fct, nst, fl = self.validate_fc(frame_data, frame_num)

        # Validate EOH CRC
        self.validate_eoh(frame_data, frame_num, nst)

        # Validate FIC
        self.validate_fic(frame_data, frame_num, nst)

        # Validate EOF CRC
        self.validate_eof(frame_data, frame_num, nst, fl)

        return fsync

    def validate_file(self, filename: Path) -> bool:
        """Validate ETI file."""
        self.results = []
        file_size = filename.stat().st_size
        expected_frames = file_size // self.FRAME_SIZE

        self.log(f"File size: {file_size} bytes ({expected_frames} frames expected)")

        prev_fsync = None
        frame_num = 0
        errors = 0
        warnings = 0

        with open(filename, 'rb') as f:
            while True:
                frame_data = f.read(self.FRAME_SIZE)
                if len(frame_data) == 0:
                    break

                if len(frame_data) != self.FRAME_SIZE:
                    self.add_result('FILE.SIZE', 'WARNING',
                                  f"Incomplete frame at end of file ({len(frame_data)} bytes)", frame_num)
                    break

                prev_fsync = self.validate_frame(frame_data, frame_num, prev_fsync)
                frame_num += 1

        # Count results
        for result in self.results:
            if result.status == 'ERROR':
                errors += 1
            elif result.status == 'WARNING':
                warnings += 1

        # Summary
        print(f"\n=== Validation Summary ===")
        print(f"File: {filename}")
        print(f"Frames validated: {frame_num}")
        print(f"Errors: {errors}")
        print(f"Warnings: {warnings}")

        if errors == 0 and warnings == 0:
            print(f"Status: ✅ PASSED (fully compliant)")
            return True
        elif errors == 0:
            print(f"Status: ⚠️ PASSED WITH WARNINGS")
            return True
        else:
            print(f"Status: ❌ FAILED ({errors} errors)")
            return False

    def print_results(self):
        """Print all validation results."""
        if not self.results:
            return

        print(f"\n=== Validation Results ===")
        for result in self.results:
            frame_str = f" (frame {result.frame_number})" if result.frame_number is not None else ""
            print(f"[{result.status}] {result.check}{frame_str}: {result.message}")

    def save_report(self, filename: Path):
        """Save validation report to file."""
        with open(filename, 'w') as f:
            f.write("ETI Validation Report\n")
            f.write("=" * 80 + "\n\n")

            for result in self.results:
                frame_str = f" (frame {result.frame_number})" if result.frame_number is not None else ""
                f.write(f"[{result.status}] {result.check}{frame_str}: {result.message}\n")

        print(f"Report saved to: {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate ETI files for ETSI EN 300 799 compliance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic validation
  python validate_eti.py -i output.eti

  # Verbose output
  python validate_eti.py -i output.eti --verbose

  # Save report
  python validate_eti.py -i output.eti --report report.txt

  # Validate multiple files
  python validate_eti.py -i frame1.eti -i frame2.eti --verbose
        """
    )

    parser.add_argument('-i', '--input', type=Path, required=True, action='append',
                       help='Input ETI file (can be specified multiple times)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output (show detailed checks)')
    parser.add_argument('-r', '--report', type=Path,
                       help='Save validation report to file')

    args = parser.parse_args()

    validator = ETIValidator(verbose=args.verbose)
    all_passed = True

    for eti_file in args.input:
        if not eti_file.exists():
            print(f"ERROR: File not found: {eti_file}")
            all_passed = False
            continue

        print(f"\n{'=' * 80}")
        print(f"Validating: {eti_file}")
        print(f"{'=' * 80}")

        passed = validator.validate_file(eti_file)
        if not passed:
            all_passed = False

        if not args.verbose:
            validator.print_results()

        if args.report:
            report_file = args.report
            if len(args.input) > 1:
                # Add file stem to report name
                report_file = report_file.with_stem(f"{report_file.stem}_{eti_file.stem}")
            validator.save_report(report_file)

    # Exit code
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
