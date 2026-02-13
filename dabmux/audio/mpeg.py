"""
MPEG audio frame parsing and validation.

This module implements MPEG Layer I/II audio frame header parsing,
validation, and frame length calculation.
"""
import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger()


class MpegLayer(IntEnum):
    """MPEG audio layer."""
    RESERVED = 0
    LAYER_III = 1  # MP3
    LAYER_II = 2   # MP2 (used in DAB)
    LAYER_I = 3


class MpegSamplingRate(IntEnum):
    """MPEG sampling rates (Hz)."""
    RATE_48000 = 48000
    RATE_24000 = 24000
    RATE_16000 = 16000


@dataclass
class MpegHeader:
    """
    MPEG audio frame header.

    Parsed from 4-byte MPEG frame header according to ISO/IEC 11172-3.
    """
    sync: int = 0            # Sync word (11 bits, should be 0x7FF)
    version: int = 0         # MPEG version (2 bits)
    layer: MpegLayer = MpegLayer.LAYER_II  # Layer (2 bits)
    protection: int = 0      # CRC protection (1 bit, 0=protected)
    bitrate_index: int = 0   # Bitrate index (4 bits)
    sampling_rate_index: int = 0  # Sampling rate index (2 bits)
    padding: int = 0         # Padding bit (1 bit)
    private: int = 0         # Private bit (1 bit)
    mode: int = 0            # Channel mode (2 bits)
    mode_ext: int = 0        # Mode extension (2 bits)
    copyright: int = 0       # Copyright bit (1 bit)
    original: int = 0        # Original bit (1 bit)
    emphasis: int = 0        # Emphasis (2 bits)

    def is_valid(self) -> bool:
        """
        Check if header is valid for DAB.

        Returns:
            True if header is valid
        """
        # Check sync word
        if self.sync != 0x7FF:
            return False

        # Check version (MPEG-1 = 3, MPEG-2 = 2)
        if self.version not in (2, 3):
            return False

        # Check layer (Layer II for DAB)
        if self.layer == MpegLayer.RESERVED:
            return False

        # Check bitrate index (0 = free, 15 = bad)
        if self.bitrate_index == 0 or self.bitrate_index == 15:
            return False

        # Check sampling rate index (3 = reserved)
        if self.sampling_rate_index == 3:
            return False

        return True

    def get_bitrate(self) -> int:
        """
        Get bitrate in kbps.

        Returns:
            Bitrate in kbps, or 0 if invalid
        """
        # MPEG-1 Layer II bitrate table
        mpeg1_layer2_bitrates = [
            0, 32, 48, 56, 64, 80, 96, 112,
            128, 160, 192, 224, 256, 320, 384, 0
        ]

        # MPEG-2 Layer II bitrate table
        mpeg2_layer2_bitrates = [
            0, 8, 16, 24, 32, 40, 48, 56,
            64, 80, 96, 112, 128, 144, 160, 0
        ]

        if self.layer == MpegLayer.LAYER_II:
            if self.version == 3:  # MPEG-1
                return mpeg1_layer2_bitrates[self.bitrate_index]
            else:  # MPEG-2
                return mpeg2_layer2_bitrates[self.bitrate_index]

        return 0

    def get_sampling_rate(self) -> int:
        """
        Get sampling rate in Hz.

        Returns:
            Sampling rate in Hz, or 0 if invalid
        """
        # MPEG-1 sampling rates
        mpeg1_rates = [44100, 48000, 32000, 0]

        # MPEG-2 sampling rates (half of MPEG-1)
        mpeg2_rates = [22050, 24000, 16000, 0]

        if self.version == 3:  # MPEG-1
            return mpeg1_rates[self.sampling_rate_index]
        else:  # MPEG-2
            return mpeg2_rates[self.sampling_rate_index]

    def get_frame_length(self) -> int:
        """
        Calculate frame length in bytes.

        For Layer II:
        FrameLength = 144 * BitRate / SampleRate + Padding

        Returns:
            Frame length in bytes
        """
        bitrate = self.get_bitrate()
        sampling_rate = self.get_sampling_rate()

        if bitrate == 0 or sampling_rate == 0:
            return 0

        if self.layer == MpegLayer.LAYER_II:
            # Layer II: 144 * bitrate / sampling_rate + padding
            frame_length = (144 * bitrate * 1000) // sampling_rate
            if self.padding:
                frame_length += 1
            return frame_length

        return 0


class MpegFrameParser:
    """
    MPEG audio frame parser.

    Reads and validates MPEG audio frames from binary data.
    """

    # Maximum bytes to search for sync word
    MAX_SYNC_SEARCH = 1200

    def __init__(self) -> None:
        """Initialize MPEG frame parser."""
        self.last_header: Optional[MpegHeader] = None

    @staticmethod
    def parse_header(data: bytes) -> Optional[MpegHeader]:
        """
        Parse MPEG header from 4 bytes.

        Args:
            data: 4 bytes of MPEG header

        Returns:
            Parsed header, or None if invalid
        """
        if len(data) < 4:
            return None

        # Unpack as big-endian 32-bit integer
        header_int = struct.unpack('>I', data[:4])[0]

        header = MpegHeader()

        # Parse bitfields (from MSB to LSB)
        header.sync = (header_int >> 21) & 0x7FF
        header.version = (header_int >> 19) & 0x03
        header.layer = MpegLayer((header_int >> 17) & 0x03)
        header.protection = (header_int >> 16) & 0x01
        header.bitrate_index = (header_int >> 12) & 0x0F
        header.sampling_rate_index = (header_int >> 10) & 0x03
        header.padding = (header_int >> 9) & 0x01
        header.private = (header_int >> 8) & 0x01
        header.mode = (header_int >> 6) & 0x03
        header.mode_ext = (header_int >> 4) & 0x03
        header.copyright = (header_int >> 3) & 0x01
        header.original = (header_int >> 2) & 0x01
        header.emphasis = header_int & 0x03

        return header

    def find_sync(self, data: bytes, max_search: int = MAX_SYNC_SEARCH) -> Optional[int]:
        """
        Find MPEG sync word in data.

        Searches for 0xFFE (11 bits set) at byte boundaries.

        Args:
            data: Data to search
            max_search: Maximum bytes to search (default 1200)

        Returns:
            Offset of sync word, or None if not found
        """
        search_len = min(len(data) - 3, max_search)

        for i in range(search_len):
            # Check for sync word (11 bits set)
            if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
                # Found potential sync, validate header
                header = self.parse_header(data[i:i + 4])
                if header and header.is_valid():
                    return i

        return None

    def read_frame(self, data: bytes) -> Optional[Tuple[MpegHeader, bytes]]:
        """
        Read next MPEG frame from data.

        Args:
            data: Data to read from

        Returns:
            Tuple of (header, frame_data) or None if no valid frame found
        """
        # Find sync word
        sync_offset = self.find_sync(data)
        if sync_offset is None:
            logger.debug("No MPEG sync found")
            return None

        # Parse header
        header = self.parse_header(data[sync_offset:])
        if not header or not header.is_valid():
            logger.debug("Invalid MPEG header")
            return None

        # Calculate frame length
        frame_length = header.get_frame_length()
        if frame_length == 0:
            logger.debug("Invalid frame length")
            return None

        # Check if we have enough data
        if sync_offset + frame_length > len(data):
            logger.debug(
                "Insufficient data for frame",
                needed=frame_length,
                available=len(data) - sync_offset
            )
            return None

        # Extract frame data
        frame_data = data[sync_offset:sync_offset + frame_length]

        # Validate next frame sync (if available)
        next_offset = sync_offset + frame_length
        if next_offset + 4 <= len(data):
            next_sync = self.find_sync(data[next_offset:next_offset + 4], max_search=4)
            if next_sync != 0:
                logger.warning("Next frame sync not at expected position")

        self.last_header = header
        return (header, frame_data)

    def validate_frame(self, data: bytes) -> bool:
        """
        Validate MPEG frame without extracting data.

        Args:
            data: Frame data to validate

        Returns:
            True if frame is valid
        """
        if len(data) < 4:
            return False

        header = self.parse_header(data)
        if not header or not header.is_valid():
            return False

        frame_length = header.get_frame_length()
        if frame_length != len(data):
            return False

        return True

    def get_frame_info(self, data: bytes) -> Optional[dict]:
        """
        Get frame information without extracting data.

        Args:
            data: Data containing MPEG frame

        Returns:
            Dictionary with frame info, or None if invalid
        """
        result = self.read_frame(data)
        if not result:
            return None

        header, frame_data = result

        return {
            'bitrate': header.get_bitrate(),
            'sampling_rate': header.get_sampling_rate(),
            'frame_length': len(frame_data),
            'layer': header.layer.name,
            'version': 1 if header.version == 3 else 2,
            'protected': header.protection == 0,
            'padding': header.padding == 1,
        }
