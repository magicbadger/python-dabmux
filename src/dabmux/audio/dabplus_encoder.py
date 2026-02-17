"""
DAB+ superframe encoder with FEC.

Implements ETSI TS 102 563 superframe encoding with FireCode CRC and Reed-Solomon FEC.
"""

import struct
import structlog
from typing import Dict

from dabmux.audio.firecode import FireCodeCRC
from dabmux.fec.reed_solomon import ReedSolomonEncoder

logger = structlog.get_logger(__name__)


class DabPlusSuperframeEncoder:
    """
    DAB+ superframe encoder with FEC protection.

    Encoding process:
    1. Take 5 AUs of AAC data (e.g., 720 bytes for 48 kbps)
    2. Add FireCode CRC (2 bytes)
    3. Pad to multiple of RS data size
    4. Apply Reed-Solomon RS(120, 110) encoding
    5. Return protected superframe
    """

    def __init__(self, bitrate: int, rs_mode: str = 'rs120'):
        """
        Initialize superframe encoder.

        Args:
            bitrate: DAB+ bitrate in kbps (24, 32, 48, 64, 80)
            rs_mode: Reed-Solomon mode ('rs120' or 'rs110')
        """
        self.bitrate = bitrate
        self.rs_mode = rs_mode
        self.au_size = bitrate * 3
        self.superframe_size = self.au_size * 5

        # FireCode CRC calculator
        self.firecode = FireCodeCRC()

        # Reed-Solomon encoder
        if rs_mode == 'rs120':
            self.rs_encoder = ReedSolomonEncoder(n=120, k=110)
            self.rs_data_size = 110
            self.rs_block_size = 120
        elif rs_mode == 'rs110':
            self.rs_encoder = ReedSolomonEncoder(n=110, k=100)
            self.rs_data_size = 100
            self.rs_block_size = 110
        else:
            raise ValueError(f"Invalid RS mode: {rs_mode}")

        # Calculate sizes
        self._calculate_protected_size()

        logger.info(
            "DAB+ encoder initialized",
            bitrate=bitrate,
            rs_mode=rs_mode,
            superframe_size=self.superframe_size,
            protected_size=self.protected_size,
        )

    def _calculate_protected_size(self) -> None:
        """Calculate size of protected superframe."""
        # Superframe structure: 11-byte header + AAC payload
        # Header contains: FireCode CRC (2) + Format (1) + AU pointers (8) = 11 bytes
        superframe_with_header = self.superframe_size + 11

        # Number of RS blocks needed
        self.num_rs_blocks = (superframe_with_header + self.rs_data_size - 1) // self.rs_data_size

        # Total protected size
        self.protected_size = self.num_rs_blocks * self.rs_block_size

    def encode(self, superframe_data: bytes) -> bytes:
        """
        Encode superframe with FEC protection.

        Builds proper DAB+ superframe structure per ETSI TS 102 563:
        [FireCode CRC: 2 bytes] [Format byte: 1 byte] [AU pointers: N bytes] [AAC payload]

        Args:
            superframe_data: 5 AUs of AAC data (raw AAC frames concatenated)

        Returns:
            Protected superframe with RS encoding
        """
        if len(superframe_data) != self.superframe_size:
            raise ValueError(
                f"Expected {self.superframe_size} bytes, got {len(superframe_data)}"
            )

        # Step 1: Build superframe header (11 bytes total for HE-AAC v2 @ 48kHz)
        header = bytearray(11)

        # Byte 2: Format byte for HE-AAC v2 at 48 kHz
        # Bit 6 (dac_rate): 0 = 48 kHz
        # Bit 5 (sbr_flag): 1 = SBR present (HE-AAC)
        # Bit 4 (aac_channel_mode): 0 = stereo
        # Bit 3 (ps_flag): 1 = PS present (HE-AAC v2)
        # Bits 0-2 (mpeg_surround): 0 = none
        header[2] = 0x28  # 0b00101000 = 48kHz, SBR, stereo, PS

        # Bytes 3-10: AU start pointers
        # For HE-AAC v2 @ 48kHz: 2 AAC AUs per superframe
        # au_start[0] = 5 (first AAC AU starts at byte 5 after header)
        # au_start[1] calculated based on actual AAC frame sizes
        # For simplicity, assume equal distribution
        au_start_1 = 11 + (self.superframe_size // 2)  # Midpoint
        header[3] = (au_start_1 >> 4) & 0xFF
        header[4] = ((au_start_1 & 0x0F) << 4) | 0x00

        # Remaining bytes of header are padding/reserved
        # (filled with 0x00 by bytearray initialization)

        # Step 2: Calculate FireCode CRC over bytes 2-10 (9 bytes)
        crc = self.firecode.calculate(bytes(header[2:11]))
        header[0] = (crc >> 8) & 0xFF
        header[1] = crc & 0xFF

        # Step 3: Combine header + AAC payload
        superframe_with_header = bytes(header) + superframe_data

        # Step 4: Pad to multiple of rs_data_size
        padded_data = self._pad_to_rs_blocks(superframe_with_header)

        # Step 5: Apply Reed-Solomon encoding with column-wise interleaving
        # Per ETSI TS 102 563: Virtual interleaver array (num_rs_blocks rows × 120 columns)
        # - Fill first 110 columns with data (column-wise, top-to-bottom)
        # - RS encode each row to generate 10 parity bytes
        # - Read out all 120 columns (column-wise, top-to-bottom)

        # Create interleaver array: num_rs_blocks rows × 120 columns
        interleaver = [[0 for _ in range(120)] for _ in range(self.num_rs_blocks)]

        # Fill data columns (0-109) column-by-column, top-to-bottom
        data_idx = 0
        for col in range(self.rs_data_size):  # 110 columns
            for row in range(self.num_rs_blocks):  # 7 rows
                if data_idx < len(padded_data):
                    interleaver[row][col] = padded_data[data_idx]
                    data_idx += 1

        # RS encode each row (generates 10 parity bytes per row)
        for row in range(self.num_rs_blocks):
            row_data = bytes(interleaver[row][:self.rs_data_size])  # First 110 bytes
            parity = self.rs_encoder.encode(row_data)  # 10 parity bytes

            # Store parity in columns 110-119
            for col in range(10):
                interleaver[row][self.rs_data_size + col] = parity[col]

        # Read out row-by-row (all 120 bytes per row, 7 rows total)
        # Each row contains: [110 data bytes] [10 parity bytes] = 120 bytes
        # This creates the protected superframe
        protected = bytearray()
        for row in range(self.num_rs_blocks):  # 7 rows
            for col in range(self.rs_block_size):  # 120 columns
                protected.append(interleaver[row][col])

        return bytes(protected)

    def _pad_to_rs_blocks(self, data: bytes) -> bytes:
        """
        Pad data to multiple of RS data size.

        Args:
            data: Data with FireCode CRC

        Returns:
            Padded data
        """
        target_size = self.num_rs_blocks * self.rs_data_size
        padding_needed = target_size - len(data)

        if padding_needed > 0:
            return data + bytes(padding_needed)
        return data

    def get_protected_size(self) -> int:
        """Get size of protected superframe in bytes."""
        return self.protected_size

    def get_protected_au_size(self) -> int:
        """Get size of one protected AU in bytes."""
        return self.protected_size // 5


# Bitrate configurations
DABPLUS_BITRATE_CONFIGS: Dict[int, Dict[str, int]] = {
    24: {'au_size': 72, 'superframe': 360, 'rs_blocks': 4},
    32: {'au_size': 96, 'superframe': 480, 'rs_blocks': 5},
    48: {'au_size': 144, 'superframe': 720, 'rs_blocks': 7},
    64: {'au_size': 192, 'superframe': 960, 'rs_blocks': 9},
    80: {'au_size': 240, 'superframe': 1200, 'rs_blocks': 11},
}
