"""
CRC calculation for PAD data groups.

Implements CRC-16-CCITT as specified in ETSI EN 300 401 Section 7.4.2.2
"""


def crc16_ccitt_pad(data: bytes) -> int:
    """
    Calculate CRC-16-CCITT for PAD data groups.

    Polynomial: 0x1021
    Initial value: 0xFFFF
    No final XOR (unlike FIB/EOH/EOF CRC which requires 0xFFFF XOR)

    Per ETSI EN 300 401 Section 7.4.2.2, PAD data group CRC uses
    the standard CRC-16-CCITT without inversion.

    Args:
        data: Data bytes to calculate CRC over

    Returns:
        16-bit CRC value

    Example:
        >>> crc16_ccitt_pad(b'\\x00\\x00')
        7439
        >>> hex(crc16_ccitt_pad(b'\\x00\\x00'))
        '0x1d0f'
    """
    crc = 0xFFFF

    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF

    return crc
