"""
EDI encoder for converting ETI frames to EDI packets.
"""
from typing import List, Optional
from dabmux.core.eti import EtiFrame
from dabmux.core.mux_elements import DabEnsemble
from dabmux.edi.protocol import (
    TagStarPTR,
    TagDETI,
    TagESTn,
    TagTIST,
    TagPacket,
    AFPacket
)


class EdiEncoder:
    """
    Encodes ETI frames into EDI packets.

    The encoder converts ETI frame structures into EDI TAG items,
    assembles them into TAG packets, and wraps them in AF packets.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize EDI encoder.

        Args:
            ensemble: DAB ensemble configuration
        """
        self.ensemble = ensemble
        self._af_seq = 0  # AF packet sequence counter
        self._dlfc = 0    # DAB logical frame counter (modulo 5000)

    def encode_frame(self, frame: EtiFrame) -> AFPacket:
        """
        Encode an ETI frame into an AF packet.

        Args:
            frame: ETI frame to encode

        Returns:
            AF packet containing EDI TAG items
        """
        tag_items: List = []

        # 1. Add *ptr TAG (protocol identifier)
        tag_items.append(TagStarPTR(
            protocol="DETI",
            major=0,
            minor=0
        ))

        # 2. Add deti TAG (ETI management)
        tag_items.append(self._create_deti_tag(frame))

        # 3. Add TIST TAG (timestamp for synchronization)
        tag_items.append(self._create_tist_tag(frame))

        # 4. Add estN TAGs (subchannel streams)
        # Extract individual subchannel data from MST blob
        mst_offset = 0
        for idx, subchannel in enumerate(self.ensemble.subchannels):
            # Calculate subchannel size from STC header
            if idx < len(frame.stc_headers):
                stc = frame.stc_headers[idx]
                # STL (Stream Data Length) is in 8-byte units
                subchannel_size = stc.stl * 8
            else:
                # Fallback: estimate from bitrate
                subchannel_size = subchannel.bitrate * 3
                # Pad to 8-byte boundary
                subchannel_size = ((subchannel_size + 7) // 8) * 8

            # Extract this subchannel's data from MST blob
            if mst_offset + subchannel_size <= len(frame.subchannel_data):
                mst_data = frame.subchannel_data[mst_offset:mst_offset + subchannel_size]
                tag_items.append(self._create_est_tag(
                    index=idx + 1,  # 1-based
                    subchannel=subchannel,
                    mst_data=mst_data,
                    frame=frame
                ))
                mst_offset += subchannel_size

        # 5. Assemble TAG packet
        tag_packet = TagPacket(tag_items=tag_items, alignment=8)
        tag_payload = tag_packet.assemble()

        # 6. Wrap in AF packet
        af_packet = AFPacket(
            seq=self._af_seq,
            payload=tag_payload
        )

        # Update counters
        self._af_seq = (self._af_seq + 1) & 0xFFFF
        self._dlfc = (self._dlfc + 1) % 5000

        return af_packet

    def _create_deti_tag(self, frame: EtiFrame) -> TagDETI:
        """
        Create deti TAG from ETI frame.

        Args:
            frame: ETI frame

        Returns:
            TagDETI instance
        """
        # Check if we have timestamp
        has_timestamp = frame.tist is not None and frame.tist.tsta != 0xFFFFFF

        # Check if we have FIC data
        has_fic = len(frame.fic_data) > 0

        tag = TagDETI(
            dlfc=self._dlfc,
            stat=0xFF,  # No error
            mid=frame.fc.mid,
            fp=frame.fc.fp,
            mnsc=frame.eoh.mnsc,  # MNSC is in EOH, not FC
            atstf=has_timestamp,
            ficf=has_fic,
            rfudf=False
        )

        # Add timestamp if present
        if has_timestamp and frame.tist:
            tag.utco = frame.tist.utco - 32  # EDI uses offset-32
            tag.seconds = frame.tist.seconds
            tag.tsta = frame.tist.tsta

        # Add FIC data if present
        if has_fic:
            tag.fic_data = frame.fic_data

        return tag

    def _create_tist_tag(self, frame: EtiFrame) -> TagTIST:
        """
        Create TIST TAG for transmitter synchronization.

        Args:
            frame: ETI frame

        Returns:
            TagTIST instance with current timestamp
        """
        # Generate timestamp from current time
        # In a real implementation, this should use precise timing (PTP/NTP)
        import time
        return TagTIST.from_unix_timestamp(time.time())

    def _create_est_tag(
        self,
        index: int,
        subchannel,
        mst_data: bytes,
        frame: EtiFrame
    ) -> TagESTn:
        """
        Create estN TAG for a subchannel.

        Args:
            index: Subchannel index (1-based)
            subchannel: DabSubchannel instance
            mst_data: MST payload data
            frame: ETI frame

        Returns:
            TagESTn instance
        """
        # Get STC for this subchannel from frame
        stc = None
        if index - 1 < len(frame.stc_headers):
            stc = frame.stc_headers[index - 1]

        # Calculate TPL (Time Profile Level)
        # TPL is related to protection level and subchannel size
        # For simplicity, use 0 (can be enhanced later)
        tpl = 0

        # Get start address and scid from STC if available
        if stc:
            sad = stc.start_address
            scid = stc.scid
        else:
            sad = subchannel.start_address
            scid = subchannel.id

        return TagESTn(
            id=index,
            scid=scid,
            sad=sad,
            tpl=tpl,
            mst_data=mst_data
        )

    def reset_counters(self) -> None:
        """Reset sequence counters (for testing)."""
        self._af_seq = 0
        self._dlfc = 0
