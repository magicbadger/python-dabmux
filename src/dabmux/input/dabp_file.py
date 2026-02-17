"""
DAB+ file input (.dabp format from odr-audioenc).

Reads pre-encoded DAB+ audio data with RS(120,110) FEC already applied.
"""

import structlog
from typing import Optional

from dabmux.input.base import InputBase

logger = structlog.get_logger(__name__)


class DABPFileInput(InputBase):
    """
    DAB+ file input for .dabp files from odr-audioenc.

    The .dabp format contains RS-encoded DAB+ audio:
    - Each RS codeword: 120 bytes
    - One superframe: (bitrate/8) codewords = (bitrate/8)*120 bytes
    - For 48 kbps: 6 codewords = 720 bytes
    - Covers 5 ETI frames (5 × 144 bytes per frame for 48 kbps)
    """

    def __init__(self) -> None:
        """Initialize DAB+ file input."""
        super().__init__()
        self._file = None
        self._file_path: str = ""
        self._bitrate: int = 0

        # Superframe buffer: read 720 bytes (6 × 120), split into 5 AUs
        self._superframe_buffer: bytes = b""
        self._current_au_index: int = 0
        self._au_size: int = 144  # Default for 48 kbps (FIX #1)

    def open(self, name: str) -> None:
        """
        Open DAB+ file.

        Args:
            name: Path to .dabp file

        Raises:
            RuntimeError: If file cannot be opened
        """
        try:
            self._file = open(name, 'rb')
            self._file_path = name
            self._is_open = True

            # FIX #2: .dabp files start at superframe boundary (no skip needed)
            logger.info("Opened DAB+ file", path=name)
        except Exception as e:
            raise RuntimeError(f"Cannot open DAB+ file: {e}")

    def set_bitrate(self, bitrate: int) -> int:
        """
        Set bitrate and calculate AU size.

        Args:
            bitrate: Bitrate in kbps

        Returns:
            Effective bitrate used
        """
        self._bitrate = bitrate

        # FIX #3: Correct formula from odr-audioenc source
        # superframe_size = (bitrate / 8) * 120 bytes
        # au_size = superframe_size / 5
        subchannel_index = bitrate // 8
        superframe_size = subchannel_index * 120
        self._au_size = superframe_size // 5

        logger.info(
            "DAB+ file input configured",
            bitrate=bitrate,
            au_size=self._au_size,
            superframe_size=superframe_size
        )
        return bitrate

    def get_frame_size(self) -> int:
        """
        Get the actual frame size (protected AU size).

        For .dabp files, FEC is already applied by odr-audioenc,
        so we return the protected AU size directly.

        Returns:
            Protected AU size in bytes (144 for 48 kbps)
        """
        return self._au_size

    def read_frame(self, size: int) -> bytes:
        """
        Read one AU from the superframe buffer.

        The .dabp format from odr-audioenc contains complete superframes
        (not individual AUs). Each superframe is 5 * au_size bytes and
        must be split into 5 AUs for the ETI frames.

        Args:
            size: Requested size (ignored, uses au_size)

        Returns:
            AU data (au_size bytes)
        """
        if not self._is_open or not self._file:
            return bytes(self._au_size)

        # Read new superframe when starting new cycle
        if self._current_au_index == 0:
            superframe_size = self._au_size * 5  # 720 bytes for 48 kbps
            self._superframe_buffer = self._file.read(superframe_size)

            # Handle EOF - rewind and loop
            if len(self._superframe_buffer) < superframe_size:
                logger.debug("DAB+ file EOF, rewinding")
                self._file.seek(0)
                self._superframe_buffer = self._file.read(superframe_size)

                # If still not enough, pad
                if len(self._superframe_buffer) < superframe_size:
                    logger.warning("DAB+ file too short, padding")
                    self._superframe_buffer += bytes(
                        superframe_size - len(self._superframe_buffer)
                    )

        # Extract current AU from superframe
        start = self._current_au_index * self._au_size
        end = start + self._au_size
        au_data = self._superframe_buffer[start:end]

        # Advance AU index (0→1→2→3→4→0)
        self._current_au_index = (self._current_au_index + 1) % 5

        return au_data

    def close(self) -> None:
        """Close the DAB+ file."""
        if self._file:
            self._file.close()
            self._file = None
            self._is_open = False
            logger.info("Closed DAB+ file", path=self._file_path)
