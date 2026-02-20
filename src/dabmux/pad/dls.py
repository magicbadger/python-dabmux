"""
DLS (Dynamic Label Segment) encoder.

Implements text segmentation and encoding for DAB Dynamic Label as specified
in ETSI EN 300 401 Section 7.4.3
"""

import structlog
from typing import List, Optional

logger = structlog.get_logger(__name__)


class DLSEncoder:
    """
    DLS (Dynamic Label Segment) encoder.

    Segments text into PAD data groups per ETSI EN 300 401.
    Each segment contains a prefix byte with charset, segment number,
    and toggle bit, followed by up to 16 bytes of text data.
    """

    MAX_DLS_LENGTH = 128  # Maximum DLS text length in characters
    MAX_SEGMENT_DATA = 16  # Maximum data bytes per segment (after prefix)

    def __init__(self, charset: str = 'utf8'):
        """
        Initialize DLS encoder.

        Args:
            charset: Character encoding ('utf8' or 'ebu-latin')
        """
        self.charset = charset
        self.current_label = ""
        self.segments: List[bytes] = []
        self.segment_index = 0
        self.toggle = False  # Toggle bit alternates on label change

        logger.info("DLS encoder initialized", charset=charset)

    def set_label(self, text: str) -> None:
        """
        Set new DLS label and generate segments.

        Args:
            text: DLS text (max 128 characters, will be truncated if longer)
        """
        # Truncate to max length
        text = text[:self.MAX_DLS_LENGTH]

        # Check if label actually changed (but allow first-time empty label)
        if text == self.current_label and len(self.segments) > 0:
            return  # No change

        # Toggle bit changes on label change (BEFORE creating segments)
        self.toggle = not self.toggle

        # Encode to bytes
        if self.charset == 'utf8':
            try:
                encoded = text.encode('utf-8')
            except UnicodeEncodeError as e:
                logger.error("UTF-8 encoding error", text=text, error=str(e))
                return
        else:
            encoded = self._encode_ebu_latin(text)

        # Generate segments
        self.segments = self._create_segments(encoded)
        self.current_label = text
        self.segment_index = 0

        logger.info("DLS label updated",
                   text=text[:50],  # Log first 50 chars
                   bytes_len=len(encoded),
                   num_segments=len(self.segments),
                   toggle=self.toggle)

    def _create_segments(self, data: bytes) -> List[bytes]:
        """
        Split DLS data into segments.

        Each segment structure:
        - Prefix byte (1 byte):
          - Bit 7: Toggle (alternates on label change)
          - Bit 6-4: Charset (0=Complete EBU Latin, 1=UTF-8, 15=UTF-8 with last segment)
          - Bit 3-0: Segment number (0-15)
        - Data (up to 16 bytes)

        The last segment has bit 4 set in charset field to indicate end.

        Args:
            data: Encoded text bytes

        Returns:
            List of segment bytes (prefix + data)
        """
        segments = []

        if len(data) == 0:
            # Empty label - create single empty segment
            prefix = self._build_prefix(
                toggle=self.toggle,
                charset_code=self._get_charset_code(),
                segment_num=0,
                is_last=True
            )
            segments.append(bytes([prefix]))
            return segments

        # Calculate number of segments needed
        num_segments = (len(data) + self.MAX_SEGMENT_DATA - 1) // self.MAX_SEGMENT_DATA
        num_segments = min(num_segments, 16)  # Max 16 segments (4-bit field)

        for seg_num in range(num_segments):
            start = seg_num * self.MAX_SEGMENT_DATA
            end = min(start + self.MAX_SEGMENT_DATA, len(data))
            seg_data = data[start:end]

            is_last = (seg_num == num_segments - 1)

            # Build prefix byte
            prefix = self._build_prefix(
                toggle=self.toggle,
                charset_code=self._get_charset_code(),
                segment_num=seg_num,
                is_last=is_last
            )

            # Segment = prefix + data
            segment = bytes([prefix]) + seg_data
            segments.append(segment)

        return segments

    def _build_prefix(self, toggle: bool, charset_code: int, segment_num: int, is_last: bool) -> int:
        """
        Build DLS segment prefix byte.

        Prefix byte structure:
        - Bit 7: Toggle (alternates on label change)
        - Bits 6-4: Charset (3 bits: 0=EBU, 1=UTF-8)
        - Bit 3: Last segment flag (1=last segment)
        - Bits 2-0: Segment number (3 bits: 0-7)

        Args:
            toggle: Toggle bit value
            charset_code: Charset code (0=EBU Latin, 1=UTF-8)
            segment_num: Segment number (0-7)
            is_last: True if this is the last segment

        Returns:
            Prefix byte value
        """
        prefix = 0

        # Bit 7: Toggle
        if toggle:
            prefix |= 0x80

        # Bits 6-4: Charset (only lower 3 bits)
        prefix |= (charset_code & 0x07) << 4

        # Bit 3: Last segment flag
        if is_last:
            prefix |= 0x08

        # Bits 2-0: Segment number (only lower 3 bits)
        prefix |= (segment_num & 0x07)

        return prefix

    def _get_charset_code(self) -> int:
        """
        Get charset code for DLS prefix.

        Returns:
            Charset code (0=EBU Latin, 1=UTF-8)
        """
        if self.charset == 'utf8':
            return 0x01  # UTF-8 charset
        else:
            return 0x00  # Complete EBU Latin (default)

    def get_next_segment(self) -> Optional[bytes]:
        """
        Get next DLS segment for transmission.

        Segments are cycled in order (0, 1, 2, ..., N-1, 0, 1, ...)
        to ensure complete label is transmitted even if receiver
        misses some frames.

        Returns:
            Segment bytes (prefix + data), or None if no label set
        """
        if not self.segments:
            return None

        segment = self.segments[self.segment_index]

        # Advance to next segment (circular)
        self.segment_index = (self.segment_index + 1) % len(self.segments)

        return segment

    def _encode_ebu_latin(self, text: str) -> bytes:
        """
        Encode text as EBU Latin (ISO-8859-1 with DAB extensions).

        Basic implementation using ISO-8859-1. Full EBU Latin includes
        additional characters defined in ETSI EN 300 401 Annex C.

        Args:
            text: Text to encode

        Returns:
            Encoded bytes
        """
        try:
            # Basic implementation: ISO-8859-1
            # TODO: Add DAB extended character set support
            return text.encode('iso-8859-1', errors='replace')
        except Exception as e:
            logger.error("EBU Latin encoding error", text=text, error=str(e))
            return b''

    def get_current_label(self) -> str:
        """
        Get current DLS label text.

        Returns:
            Current label string
        """
        return self.current_label

    def get_num_segments(self) -> int:
        """
        Get number of segments for current label.

        Returns:
            Number of segments
        """
        return len(self.segments)
