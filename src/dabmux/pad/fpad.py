"""
F-PAD (Fixed PAD) encoder.

F-PAD is a 2-byte fixed field that provides pointers to X-PAD content.
Structure defined in ETSI EN 300 401 Section 7.4.2.1
"""

import structlog

logger = structlog.get_logger(__name__)


class FPADEncoder:
    """
    F-PAD (Fixed PAD) encoder - 2 bytes.

    Structure (ETSI EN 300 401, Section 7.4.2.1):
    - Byte 1: CI flag (1 bit) + Application Type (5 bits) + reserved (2 bits)
    - Byte 2: X-PAD length indicator (L field)

    CI flag: 0 = short X-PAD, 1 = variable size X-PAD
    Application Type: Indicates content type (2 = DLS)
    L field: Maps X-PAD length to 5-bit value
    """

    def __init__(self, xpad_length: int):
        """
        Initialize F-PAD encoder.

        Args:
            xpad_length: Length of X-PAD in bytes (must be even, 4-196)
        """
        self.xpad_length = xpad_length

        if xpad_length < 0 or xpad_length > 196:
            logger.warning("X-PAD length out of range",
                         length=xpad_length,
                         valid_range="0-196")

        if xpad_length % 2 != 0:
            logger.warning("X-PAD length should be even",
                         length=xpad_length)

    def encode(self, has_xpad: bool = True, app_type: int = 2) -> bytes:
        """
        Encode F-PAD.

        Args:
            has_xpad: True if X-PAD data is present
            app_type: Application type (2 = DLS, 12 = MOT)

        Returns:
            2-byte F-PAD
        """
        if not has_xpad or self.xpad_length == 0:
            return b'\x00\x00'  # No X-PAD

        # CI flag = 1 (variable size X-PAD)
        # Application Type (5 bits)
        # Reserved = 0 (2 bits)
        byte1 = 0x80 | ((app_type & 0x1F) << 2)

        # X-PAD length indicator (L field)
        # Maps actual length to 5-bit value per ETSI EN 300 401 Table 6
        l_value = self._calculate_l_value(self.xpad_length)
        byte2 = l_value

        return bytes([byte1, byte2])

    def _calculate_l_value(self, xpad_len: int) -> int:
        """
        Calculate L field value from X-PAD length.

        Per ETSI EN 300 401 Table 6:
        L=0: 4 bytes
        L=1: 6 bytes
        L=2: 8 bytes
        ...
        L=31: 66 bytes (for short X-PAD)

        For variable X-PAD (CI=1), extended range:
        L=0: 4 bytes
        ...
        L=31: 196 bytes (max)

        Formula: L = (xpad_len - 4) / 2

        Args:
            xpad_len: X-PAD length in bytes

        Returns:
            L field value (0-31)
        """
        if xpad_len < 4:
            return 0

        # Calculate L value
        l_value = (xpad_len - 4) // 2

        # Clamp to valid range
        return min(max(l_value, 0), 31)
