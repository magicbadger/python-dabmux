"""
AAC Superframe Buffer for DAB+.

This module implements superframe handling for DAB+ audio streams.
AAC frames are buffered and distributed across 5 Access Units (AUs)
per ETSI TS 102 563 requirements.

Key Concepts:
- AAC frame: 1024 samples = ~21.33ms at 48 kHz
- DAB+ AU: 24ms fixed timing, size = bitrate * 3 bytes
- Superframe: 5 AUs = 120ms total
- AAC frames don't align with AU boundaries (by design)
"""

import structlog
from typing import List, Optional

logger = structlog.get_logger(__name__)


class AacSuperframeBuffer:
    """
    Buffer for building DAB+ superframes from AAC frames.

    Strategy:
    - Accumulate complete AAC frames in a buffer
    - When enough data is available (~superframe_size), build superframe
    - Distribute concatenated AAC data evenly across 5 AUs (24ms each)
    - Keep remainder bytes for next superframe
    - Return one AU per ETI frame request

    This approach works because:
    - DAB+ is a transport layer (byte stream)
    - AAC frames are application layer (parsed by receiver)
    - AU boundaries can fall mid-AAC-frame (no alignment needed)
    """

    def __init__(self, bitrate: int, enable_fec: bool = True):
        """
        Initialize superframe buffer.

        Args:
            bitrate: Configured bitrate in kbps (e.g., 48)
            enable_fec: Enable FEC encoding (default: True)
        """
        self.bitrate = bitrate
        self.au_size = bitrate * 3  # Bytes per AU (24ms at given bitrate)
        self.superframe_size = self.au_size * 5  # 120ms total (5 AUs)
        self.enable_fec = enable_fec

        # Initialize FEC encoder if enabled
        if self.enable_fec:
            from dabmux.audio.dabplus_encoder import DabPlusSuperframeEncoder
            self.fec_encoder = DabPlusSuperframeEncoder(bitrate)
            self.protected_au_size = self.fec_encoder.get_protected_au_size()
        else:
            self.fec_encoder = None
            self.protected_au_size = self.au_size

        # Frame accumulation buffer
        self.frame_buffer: List[bytes] = []
        self.buffer_bytes: int = 0

        # Current superframe (5 AUs)
        self.aus: List[bytes] = [b""] * 5
        self.superframe_ready: bool = False

        # Statistics
        self.frame_count: int = 0
        self.superframe_count: int = 0
        self.underruns: int = 0

        logger.info(
            "AAC superframe buffer initialized",
            bitrate=bitrate,
            au_size=self.au_size,
            superframe_size=self.superframe_size,
            fec_enabled=self.enable_fec,
            protected_au_size=self.protected_au_size,
        )

    def add_frame(self, frame: bytes) -> None:
        """
        Add complete AAC frame to buffer.

        Args:
            frame: Complete AAC frame (including ADTS header)
        """
        self.frame_buffer.append(frame)
        self.buffer_bytes += len(frame)
        self.frame_count += 1

    def needs_frames(self) -> bool:
        """
        Check if buffer needs more frames.

        Returns:
            True if more frames should be added before building superframe
        """
        # Need enough bytes for a full superframe
        # Also ensure we have at least a few frames for proper distribution
        return self.buffer_bytes < self.superframe_size or len(self.frame_buffer) < 5

    def build_superframe(self) -> None:
        """
        Build superframe from accumulated frames.

        Process:
        1. Concatenate all buffered AAC frames into byte stream
        2. Split into 5 equal AUs (au_size bytes each)
        3. Pad with zeros if underrun
        4. Keep remainder for next superframe

        Note: AU boundaries will typically fall mid-AAC-frame.
        This is expected and correct per DAB+ specification.
        """
        if not self.frame_buffer:
            # No frames available, build silent superframe
            logger.warning("Building superframe with no frames (silence)")
            silent_superframe = bytes(self.superframe_size)

            # Apply FEC if enabled
            if self.enable_fec and self.fec_encoder:
                protected = self.fec_encoder.encode(silent_superframe)
                for i in range(5):
                    start = i * self.protected_au_size
                    end = start + self.protected_au_size
                    self.aus[i] = protected[start:end]
            else:
                for i in range(5):
                    self.aus[i] = bytes(self.au_size)

            self.superframe_ready = True
            self.underruns += 1
            return

        # Concatenate all frames into continuous byte stream
        data = b"".join(self.frame_buffer)

        # Check for underrun
        if len(data) < self.superframe_size:
            logger.warning(
                "Superframe underrun - padding with zeros",
                available=len(data),
                needed=self.superframe_size,
                deficit=self.superframe_size - len(data),
            )
            self.underruns += 1
            # Pad to full size
            data += b"\x00" * (self.superframe_size - len(data))

        # Split into 5 equal AUs
        for i in range(5):
            start = i * self.au_size
            end = start + self.au_size
            self.aus[i] = data[start:end]

        # Apply FEC encoding if enabled
        if self.enable_fec and self.fec_encoder:
            # Concatenate 5 AUs into superframe
            superframe_data = b"".join(self.aus)

            # Encode with FireCode CRC + RS
            protected_superframe = self.fec_encoder.encode(superframe_data)

            # Split protected superframe back into 5 AUs
            for i in range(5):
                start = i * self.protected_au_size
                end = start + self.protected_au_size
                self.aus[i] = protected_superframe[start:end]

        # Keep remainder for next superframe
        remainder = data[self.superframe_size :]
        if remainder:
            # Start next buffer with leftover bytes
            self.frame_buffer = [remainder]
            self.buffer_bytes = len(remainder)
        else:
            # Clean slate for next superframe
            self.frame_buffer = []
            self.buffer_bytes = 0

        self.superframe_ready = True
        self.superframe_count += 1

        # Log progress periodically
        if self.superframe_count % 100 == 0:
            logger.debug(
                "Superframe built",
                count=self.superframe_count,
                frames_used=self.frame_count,
                underruns=self.underruns,
            )

    def get_au(self, au_index: int) -> bytes:
        """
        Get specific AU from current superframe.

        Args:
            au_index: AU index (0-4)

        Returns:
            AU data (protected_au_size bytes if FEC enabled, au_size otherwise)

        Raises:
            ValueError: If au_index is out of range
        """
        if au_index < 0 or au_index >= 5:
            raise ValueError(f"Invalid AU index: {au_index} (must be 0-4)")

        if not self.superframe_ready:
            # Superframe not ready, return silence
            logger.warning("Superframe not ready, returning silence", au_index=au_index)
            return bytes(self.protected_au_size)

        return self.aus[au_index]

    def reset(self) -> None:
        """
        Reset buffer state.

        Clears all accumulated frames and resets counters.
        """
        self.frame_buffer = []
        self.buffer_bytes = 0
        self.aus = [b""] * 5
        self.superframe_ready = False
        self.frame_count = 0
        self.superframe_count = 0
        self.underruns = 0
        logger.info("Superframe buffer reset")

    def get_stats(self) -> dict:
        """
        Get buffer statistics.

        Returns:
            Dictionary with buffer statistics
        """
        return {
            "bitrate": self.bitrate,
            "au_size": self.au_size,
            "superframe_size": self.superframe_size,
            "frames_buffered": len(self.frame_buffer),
            "buffer_bytes": self.buffer_bytes,
            "superframe_ready": self.superframe_ready,
            "total_frames": self.frame_count,
            "total_superframes": self.superframe_count,
            "underruns": self.underruns,
        }
