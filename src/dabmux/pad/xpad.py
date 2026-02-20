"""
X-PAD (Extended PAD) encoder.

Assembles DLS segments and other PAD data into X-PAD format.
"""

import structlog
from dabmux.pad.dls import DLSEncoder
from dabmux.pad.fpad import FPADEncoder
from dabmux.pad.data_group import PADDataGroup

logger = structlog.get_logger(__name__)


class XPADEncoder:
    """
    X-PAD (Extended PAD) encoder.

    Assembles DLS segments into X-PAD data groups and combines
    with F-PAD to create complete PAD for audio frames.
    """

    def __init__(self, pad_length: int, dls_encoder: DLSEncoder):
        """
        Initialize X-PAD encoder.

        Args:
            pad_length: Total PAD length (F-PAD + X-PAD) in bytes
            dls_encoder: DLS encoder instance
        """
        self.pad_length = pad_length
        self.xpad_length = pad_length - 2  # Subtract 2-byte F-PAD
        self.dls_encoder = dls_encoder
        self.fpad_encoder = FPADEncoder(self.xpad_length)

        if pad_length < 2:
            logger.warning("PAD length too small", pad_length=pad_length, minimum=2)

        logger.info("X-PAD encoder initialized",
                   pad_length=pad_length,
                   xpad_length=self.xpad_length)

    def encode_pad(self) -> bytes:
        """
        Encode complete PAD (X-PAD + F-PAD).

        Returns X-PAD data (if available) followed by F-PAD.
        PAD structure in ETI: [X-PAD data][F-PAD]

        Returns:
            PAD bytes (pad_length total bytes)
        """
        # Get DLS segment
        dls_segment = self.dls_encoder.get_next_segment()

        if dls_segment is None:
            # No DLS - return zero PAD
            logger.debug("No DLS segment available, returning zero PAD")
            return bytes(self.pad_length)

        # Create PAD data group with DLS segment
        data_group = PADDataGroup(
            extension=False,    # No session header for basic DLS
            crc_flag=True,      # CRC for reliability
            segment=True,       # DLS uses segmentation
            user_access=2,      # 2 = DLS application type
            data=dls_segment
        )

        # Encode data group
        xpad_data = data_group.encode()

        # Check X-PAD size
        if len(xpad_data) > self.xpad_length:
            logger.warning("X-PAD data too large, truncating",
                         size=len(xpad_data),
                         max_size=self.xpad_length)
            xpad_data = xpad_data[:self.xpad_length]

        # Pad X-PAD to required length (pad with zeros at the beginning)
        if len(xpad_data) < self.xpad_length:
            padding_needed = self.xpad_length - len(xpad_data)
            xpad_data = bytes(padding_needed) + xpad_data

        # Encode F-PAD
        fpad_data = self.fpad_encoder.encode(has_xpad=True, app_type=2)

        # Return X-PAD + F-PAD
        # Order in ETI: X-PAD first, then F-PAD at the end
        pad = xpad_data + fpad_data

        if len(pad) != self.pad_length:
            logger.error("PAD length mismatch",
                        expected=self.pad_length,
                        actual=len(pad))

        return pad

    def get_pad_length(self) -> int:
        """
        Get total PAD length.

        Returns:
            PAD length in bytes
        """
        return self.pad_length

    def get_xpad_length(self) -> int:
        """
        Get X-PAD length (excluding F-PAD).

        Returns:
            X-PAD length in bytes
        """
        return self.xpad_length
