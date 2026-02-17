"""
FireCode CRC-16 for DAB+ superframes.

Implements ETSI TS 102 563 FireCode CRC calculation.
"""

import struct
from typing import List


class FireCodeCRC:
    """
    FireCode CRC-16 calculator for DAB+ superframes.

    Generator polynomial: x^16 + x^14 + x^13 + x^11 + x^10 + x^8 + x^6 + x^5 + x^4 + x^2 + x + 1
    Polynomial value: 0x782F
    """

    POLY = 0x782F

    def __init__(self):
        """Initialize with lookup table."""
        self._table = self._generate_table()

    def _generate_table(self) -> List[int]:
        """Generate CRC lookup table."""
        table = []
        for i in range(256):
            crc = i << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ self.POLY
                else:
                    crc = crc << 1
                crc &= 0xFFFF
            table.append(crc)
        return table

    def calculate(self, data: bytes) -> int:
        """
        Calculate FireCode CRC.

        Args:
            data: Input bytes

        Returns:
            16-bit CRC value
        """
        crc = 0xFFFF

        for byte in data:
            index = ((crc >> 8) ^ byte) & 0xFF
            crc = ((crc << 8) ^ self._table[index]) & 0xFFFF

        return crc

    def append_crc(self, data: bytes) -> bytes:
        """
        Calculate and append CRC to data.

        Args:
            data: Input bytes

        Returns:
            Data with 2-byte CRC appended (big-endian)
        """
        crc = self.calculate(data)
        return data + struct.pack('>H', crc)
