"""
AAC/ADTS frame parser for DAB+.

This module provides parsing and validation of AAC audio in ADTS format
for DAB+ transmission. Supports HE-AAC v2 (AAC-LC + SBR + PS) as required
by ETSI TS 102 563.
"""

import struct
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class AACHeader:
    """Parsed AAC/ADTS header information."""

    profile: int  # 0=Main, 1=LC, 2=SSR
    sample_rate: int  # Hz (e.g., 48000)
    channels: int  # 1=mono, 2=stereo
    frame_length: int  # Total frame size in bytes
    protection: bool  # CRC protection present

    def is_he_aac_v2(self) -> bool:
        """
        Check if this is HE-AAC v2 (AAC-LC + SBR + PS).

        HE-AAC v2 uses AAC-LC profile (1) as the base.
        Actual SBR/PS signaling is in the AAC payload.
        """
        return self.profile == 1 and self.channels == 2

    def is_dab_compatible(self) -> bool:
        """
        Check if format is compatible with DAB+.

        DAB+ requires:
        - 48 kHz sample rate (or 32/24/16 kHz)
        - HE-AAC profile (AAC-LC base)
        - Stereo for HE-AAC v2, mono for HE-AAC v1
        """
        valid_rates = [16000, 24000, 32000, 48000]
        return self.sample_rate in valid_rates and self.profile == 1  # AAC-LC


class AACFrameParser:
    """Parse AAC frames in ADTS format."""

    # Sampling frequency table (ISO/IEC 13818-7)
    SAMPLE_RATES = [
        96000,
        88200,
        64000,
        48000,
        44100,
        32000,
        24000,
        22050,
        16000,
        12000,
        11025,
        8000,
        7350,
    ]

    def find_sync(self, data: bytes, start: int = 0) -> Optional[int]:
        """
        Find ADTS sync word (0xFFF) in data.

        Args:
            data: Byte array to search
            start: Offset to start search

        Returns:
            Offset of sync word, or None if not found
        """
        for i in range(start, len(data) - 1):
            # Check for 0xFFF sync (12 bits)
            if data[i] == 0xFF and (data[i + 1] & 0xF0) == 0xF0:
                return i
        return None

    def parse_header(self, data: bytes) -> Optional[AACHeader]:
        """
        Parse ADTS header.

        ADTS Fixed Header (4 bytes):
          Bits 0-11:   Sync word (0xFFF)
          Bit 12:      MPEG version (0=MPEG-4, 1=MPEG-2)
          Bits 13-14:  Layer (always 00)
          Bit 15:      Protection absent
          Bits 16-17:  Profile (0=Main, 1=LC, 2=SSR)
          Bits 18-21:  Sampling frequency index
          Bit 22:      Private bit
          Bits 23-25:  Channel configuration

        ADTS Variable Header (3 bytes):
          Bits 0-12:   Frame length (including header)
          Bits 13-23:  Buffer fullness
          Bits 24-25:  Number of frames - 1

        Args:
            data: Byte array starting with ADTS header

        Returns:
            AACHeader if valid, None otherwise
        """
        if len(data) < 7:
            return None

        # Check sync word
        if data[0] != 0xFF or (data[1] & 0xF0) != 0xF0:
            return None

        # Parse fixed header
        protection = (data[1] & 0x01) == 0
        profile = (data[2] >> 6) & 0x3
        sr_idx = (data[2] >> 2) & 0xF

        if sr_idx >= len(self.SAMPLE_RATES):
            return None
        sample_rate = self.SAMPLE_RATES[sr_idx]

        channels = ((data[2] & 0x01) << 2) | ((data[3] >> 6) & 0x3)

        # Parse variable header
        frame_length = (
            ((data[3] & 0x03) << 11) | (data[4] << 3) | ((data[5] >> 5) & 0x7)
        )

        return AACHeader(
            profile=profile,
            sample_rate=sample_rate,
            channels=channels,
            frame_length=frame_length,
            protection=protection,
        )

    def read_frame(self, data: bytes) -> Optional[Tuple[AACHeader, bytes]]:
        """
        Read next AAC frame from data.

        Args:
            data: Byte array containing AAC frames

        Returns:
            (header, frame_data) tuple, or None if no valid frame
        """
        # Find sync
        sync_pos = self.find_sync(data)
        if sync_pos is None:
            return None

        # Parse header
        header = self.parse_header(data[sync_pos:])
        if header is None:
            return None

        # Extract frame data
        if len(data) < sync_pos + header.frame_length:
            return None  # Incomplete frame

        frame_data = data[sync_pos : sync_pos + header.frame_length]
        return (header, frame_data)

    def validate_for_dab_plus(
        self, data: bytes, expected_bitrate: int
    ) -> Tuple[bool, str]:
        """
        Validate AAC file for DAB+ compatibility.

        Args:
            data: File data to validate
            expected_bitrate: Configured bitrate in kbps

        Returns:
            (valid, error_message) tuple
        """
        # Read first frame
        result = self.read_frame(data)
        if result is None:
            return (False, "No valid AAC frame found")

        header, _ = result

        # Check format
        if not header.is_dab_compatible():
            return (
                False,
                f"Incompatible format: {header.sample_rate} Hz, "
                f"profile {header.profile}, {header.channels} channels. "
                f"DAB+ requires 48 kHz, AAC-LC profile (1), stereo for HE-AAC v2.",
            )

        # Check bitrate (approximate)
        # Frame rate = sample_rate / 1024 (for AAC)
        frame_rate = header.sample_rate / 1024
        actual_bitrate = (header.frame_length * 8 * frame_rate) / 1000

        # Allow 10% tolerance
        if abs(actual_bitrate - expected_bitrate) > expected_bitrate * 0.1:
            return (
                False,
                f"Bitrate mismatch: expected {expected_bitrate} kbps, "
                f"file is approximately {actual_bitrate:.0f} kbps",
            )

        return (True, "")
