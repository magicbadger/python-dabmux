"""
DAB+ (HE-AAC v2) support.

This module provides infrastructure for DAB+ subchannels, including
superframe handling and configuration. Full HE-AAC encoding is not
implemented (would require external encoder like fdk-aac).
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DabPlusProfile(Enum):
    """DAB+ audio profile."""
    HE_AAC = "he-aac"      # HE-AAC (AAC+SBR)
    HE_AAC_V2 = "he-aac-v2"  # HE-AAC v2 (AAC+SBR+PS)


@dataclass
class DabPlusSuperframe:
    """
    DAB+ Superframe structure.

    A DAB+ superframe consists of:
    - 5 logical frames (AU - Access Units)
    - Each AU contains AAC audio data
    - FireCode CRC for error detection
    - Reed-Solomon error correction (RS(110, 100) or RS(120, 110))
    """
    num_aus: int = 5          # Number of Access Units (typically 5)
    au_size: int = 0          # Size of each AU in bytes
    rs_enabled: bool = True   # Reed-Solomon enabled
    data: bytes = b""         # Superframe data

    def get_total_size(self) -> int:
        """
        Get total superframe size.

        Returns:
            Total size in bytes
        """
        # Base size: AU data
        base_size = self.num_aus * self.au_size

        # Add RS parity if enabled
        if self.rs_enabled:
            # RS adds 10 parity bytes per 110 bytes (or 120 bytes)
            # Simplified calculation
            rs_overhead = (base_size // 110) * 10
            return base_size + rs_overhead

        return base_size


@dataclass
class DabPlusConfig:
    """
    DAB+ subchannel configuration.
    """
    bitrate: int                     # Bitrate in kbps (e.g., 32, 48, 64, 80, 96)
    profile: DabPlusProfile          # Audio profile
    sample_rate: int = 48000         # Sample rate in Hz
    channels: int = 2                # Number of channels (1=mono, 2=stereo)
    sbr: bool = True                 # SBR (Spectral Band Replication) enabled
    ps: bool = False                 # PS (Parametric Stereo) enabled
    drc: int = 0                     # Dynamic Range Control (0=off)

    def get_au_size(self) -> int:
        """
        Calculate Access Unit size based on bitrate.

        For DAB+, each AU represents 24ms of audio (one DAB frame).

        Returns:
            AU size in bytes
        """
        # AU size = (bitrate * 24ms) / 8 bits per byte / 1000 ms per second
        # Simplified: bitrate * 3
        return self.bitrate * 3

    def get_superframe_size(self) -> int:
        """
        Calculate superframe size.

        Returns:
            Superframe size in bytes
        """
        superframe = DabPlusSuperframe(
            num_aus=5,
            au_size=self.get_au_size(),
            rs_enabled=True
        )
        return superframe.get_total_size()

    def requires_enhanced_packet_mode(self) -> bool:
        """
        Check if enhanced packet mode is required.

        DAB+ always uses enhanced packet mode (not stream mode).

        Returns:
            True (always for DAB+)
        """
        return True


def calculate_dabplus_subchannel_size(bitrate: int) -> int:
    """
    Calculate DAB+ subchannel size in CUs (Capacity Units).

    Args:
        bitrate: Bitrate in kbps

    Returns:
        Subchannel size in CUs

    Note:
        This is a simplified calculation. Real DAB+ uses protection
        profiles that determine exact CU allocation.
    """
    # Rough approximation: 8 CUs per 8 kbps
    # (1 CU = 64 bits per DAB frame = 8 bytes per 24ms)
    return (bitrate * 8) // 8


def create_dummy_superframe(config: DabPlusConfig) -> bytes:
    """
    Create a dummy DAB+ superframe (for testing).

    This creates a placeholder superframe with correct size but
    no actual AAC audio data. Real implementation would require
    an external AAC encoder (e.g., fdk-aac-dabplus).

    Args:
        config: DAB+ configuration

    Returns:
        Dummy superframe bytes
    """
    size = config.get_superframe_size()
    # Return zero-filled data (would be real AAC data in production)
    return b'\x00' * size


def parse_dabplus_bitrate(bitrate_str: str) -> int:
    """
    Parse DAB+ bitrate string.

    Args:
        bitrate_str: Bitrate string (e.g., "32k", "48", "64kbps")

    Returns:
        Bitrate in kbps

    Raises:
        ValueError: If bitrate string is invalid
    """
    # Remove common suffixes
    bitrate_str = bitrate_str.lower().replace('kbps', '').replace('k', '').strip()

    try:
        bitrate = int(bitrate_str)
    except ValueError:
        raise ValueError(f"Invalid bitrate string: {bitrate_str}")

    # Validate common DAB+ bitrates
    valid_bitrates = [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 112, 128, 144, 160, 192]
    if bitrate not in valid_bitrates:
        raise ValueError(f"Unsupported DAB+ bitrate: {bitrate} kbps")

    return bitrate


# DAB+ bitrate recommendations
DABPLUS_RECOMMENDED_BITRATES = {
    'speech_mono': 32,      # Speech, mono
    'music_mono': 48,       # Music, mono
    'music_stereo': 80,     # Music, stereo (good quality)
    'music_stereo_hq': 96,  # Music, stereo (high quality)
}


def get_recommended_bitrate(content_type: str) -> int:
    """
    Get recommended DAB+ bitrate for content type.

    Args:
        content_type: Content type ('speech_mono', 'music_mono', 'music_stereo', 'music_stereo_hq')

    Returns:
        Recommended bitrate in kbps
    """
    return DABPLUS_RECOMMENDED_BITRATES.get(content_type, 80)
