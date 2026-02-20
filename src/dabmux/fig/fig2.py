"""
FIG Type 2 implementations.

FIG Type 2 contains dynamic labels with character set support.
This module implements FIG 2/1 (Service Component Dynamic Label).
"""
import struct
import structlog
from typing import List, Optional
from dabmux.fig.base import FIGBase, FIGRate, FillStatus, FIGPriority
from dabmux.core.mux_elements import DabEnsemble

logger = structlog.get_logger()


class FIG2_1(FIGBase):
    """
    FIG 2/1: Service Component Dynamic Label.

    Provides dynamic "now playing" text for service components.
    Supports UTF-8, UCS-2, and EBU Latin charsets.

    Per ETSI EN 300 401 Section 8.1.13.2.

    Byte Structure:
    - Header (2 bytes): Type/Length + Charset/OE/Ext
    - Per Segment:
      - Toggle (1) | Seg# (3) | Last (1) | Rfa (3)  [1 byte]
      - Character Flag (8 bits)                      [1 byte]
      - Text Data (0-16 bytes)                       [variable]
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 2/1.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble
        self.component_index = 0  # Round-robin through components

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 2/1 data.

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        # Find components with dynamic labels
        components_with_dls = [
            c for c in self.ensemble.components
            if c.dynamic_label and c.dynamic_label.text
        ]

        if not components_with_dls:
            status.complete_fig_transmitted = True
            return status

        if max_size < 4:  # Minimum: header(2) + segment header(2)
            return status

        # Round-robin: transmit one segment from one component
        component = components_with_dls[self.component_index % len(components_with_dls)]

        # Get next segment BEFORE encoding (so we have the right index)
        segment_num = component.dynamic_label._segment_index
        num_segments = len(component.dynamic_label._segments) if component.dynamic_label._segments else 1
        is_last = (segment_num == num_segments - 1)

        segment_data = component.dynamic_label.get_next_segment()

        if segment_data is None:
            self.component_index = (self.component_index + 1) % len(components_with_dls)
            return status

        # Reserve space for header
        pos = 2

        # Encode segment header
        toggle = 1 if component.dynamic_label.toggle else 0

        # Segment header byte
        buf[pos] = (toggle << 7) | ((segment_num & 0x07) << 4) | ((1 if is_last else 0) << 3)

        # Character flag (0xFF = all positions used, 0x00 = none used)
        # For simplicity, we use 0xFF if there's data, 0x00 if empty
        buf[pos + 1] = 0xFF if len(segment_data) > 0 else 0x00
        pos += 2

        # Copy segment data
        segment_len = min(len(segment_data), max_size - pos)
        buf[pos:pos + segment_len] = segment_data[:segment_len]
        pos += segment_len

        # Fill header
        fig_type = 2
        length = (pos - 2) + 1  # Data bytes + header byte 1
        charset = component.dynamic_label.charset

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (charset << 4) | 0x01  # OE=0, Rfa=0, Ext=1

        logger.debug(
            "Encoding FIG 2/1",
            component_uid=component.uid,
            segment_num=segment_num,
            is_last=is_last,
            toggle=toggle,
            segment_len=segment_len,
            total_bytes=pos
        )

        status.num_bytes_written = pos

        # Advance to next component (round-robin)
        self.component_index = (self.component_index + 1) % len(components_with_dls)

        # Complete when all components transmitted at least once
        if self.component_index == 0:
            status.complete_fig_transmitted = True

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 2/1 transmitted at rate A (100ms)."""
        return FIGRate.A

    def priority(self) -> FIGPriority:
        """FIG 2/1 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 2."""
        return 2

    def fig_extension(self) -> int:
        """Extension 1."""
        return 1
