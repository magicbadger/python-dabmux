"""
FIC (Fast Information Channel) Encoder.

The FIC carries FIGs that provide configuration information to receivers.
In DAB Mode I, the FIC is 96 bytes and consists of 3 FIBs (Fast Information Blocks)
of 30 bytes each, plus padding.
"""
import structlog
from dabmux.fig.carousel import FIGCarousel
from dabmux.core.mux_elements import DabEnsemble, TransmissionMode
from dabmux.fig.fig0 import FIG0_0, FIG0_1, FIG0_2, FIG0_9, FIG0_10, FIG0_18, FIG0_19
from dabmux.fig.fig1 import FIG1_0, FIG1_1
from dabmux.utils.crc import crc16

logger = structlog.get_logger()


class FICEncoder:
    """
    FIC (Fast Information Channel) Encoder.

    Manages FIG carousel and encodes FIGs into the FIC for ETI frames.
    The FIC structure depends on the transmission mode:
    - Mode I: 3 FIBs of 30 bytes each = 90 bytes + 6 bytes padding = 96 bytes
    - Mode II-IV: Different structures (not implemented in Phase 2)
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIC encoder.

        Args:
            ensemble: Ensemble configuration
        """
        self.ensemble = ensemble
        self.carousel = FIGCarousel()
        self.current_frame = 0

        # Setup standard FIGs
        self._setup_figs()

    def _setup_figs(self) -> None:
        """Setup standard FIGs for the carousel."""
        # FIG 0/0: Ensemble information (mandatory)
        fig0_0 = FIG0_0(self.ensemble, self.current_frame)
        self.carousel.add_fig(fig0_0)

        # FIG 0/1: Sub-channel organization (mandatory if subchannels exist)
        if self.ensemble.subchannels:
            fig0_1 = FIG0_1(self.ensemble)
            self.carousel.add_fig(fig0_1)

        # FIG 0/2: Service organization (mandatory if services exist)
        if self.ensemble.services:
            fig0_2 = FIG0_2(self.ensemble)
            self.carousel.add_fig(fig0_2)

        # FIG 1/0: Ensemble label (mandatory if label exists)
        if self.ensemble.label.text:
            fig1_0 = FIG1_0(self.ensemble)
            self.carousel.add_fig(fig1_0)

        # FIG 1/1: Service labels (if services with labels exist)
        if any(s.label.text for s in self.ensemble.services):
            fig1_1 = FIG1_1(self.ensemble)
            self.carousel.add_fig(fig1_1)

        # FIG 0/9: Extended Country Code (if ECC is set and services exist)
        if self.ensemble.services and self.ensemble.ecc != 0:
            fig0_9 = FIG0_9(self.ensemble)
            self.carousel.add_fig(fig0_9)

        # FIG 0/10: Date and Time (if enabled)
        if self.ensemble.datetime.enabled:
            fig0_10 = FIG0_10(self.ensemble)
            self.carousel.add_fig(fig0_10)

        # FIG 0/18: Announcement Support (if any service has announcements)
        if any(s.announcements.enabled for s in self.ensemble.services):
            fig0_18 = FIG0_18(self.ensemble)
            self.carousel.add_fig(fig0_18)

        # FIG 0/19: Announcement Switching (always register, skips if no active)
        fig0_19 = FIG0_19(self.ensemble)
        self.carousel.add_fig(fig0_19)

        logger.info(
            "FIC encoder initialized",
            num_figs=self.carousel.get_fig_count(),
            ensemble_id=f"0x{self.ensemble.id:04X}"
        )

    def encode_fic(self, frame_number: int) -> bytes:
        """
        Encode FIC for a given frame.

        Args:
            frame_number: Current frame number

        Returns:
            FIC data (96 bytes for Mode I)
        """
        self.current_frame = frame_number

        # Update FIG 0/0 with current frame
        for fig in self.carousel.figs:
            if fig.name() == "0/0":
                fig.current_frame = frame_number
                break

        # For Mode I: 3 FIBs of 32 bytes each (30 data + 2 CRC)
        mode = self.ensemble.transmission_mode

        if mode == TransmissionMode.TM_I:
            return self._encode_fic_mode_i()
        else:
            # Other modes not implemented yet
            logger.warning("FIC encoding for non-Mode I not implemented", mode=mode.name)
            return bytes(96)

    def _encode_fic_mode_i(self) -> bytes:
        """
        Encode FIC for Mode I.

        Mode I FIC structure:
        - 3 FIBs of 32 bytes each
        - Each FIB: 30 bytes data + 2 bytes CRC
        - Total: 96 bytes

        Returns:
            FIC data (96 bytes)
        """
        fic_data = bytearray(96)
        pos = 0

        # Fill 3 FIBs
        for fib_num in range(3):
            fib_data = bytearray(32)

            # Fill FIB with FIGs (30 bytes available)
            bytes_written = self.carousel.fill_fib(fib_data, max_size=30)

            # Calculate CRC for FIB (CRC-16 over 30 bytes of data)
            # Note: DAB standard requires XOR with 0xFFFF (inversion) after CRC
            crc = crc16(bytes(fib_data[:30])) ^ 0xFFFF

            # Append CRC (big-endian)
            fib_data[30] = (crc >> 8) & 0xFF
            fib_data[31] = crc & 0xFF

            # Copy to FIC
            fic_data[pos:pos+32] = fib_data
            pos += 32

        return bytes(fic_data)

    def update_ensemble(self, ensemble: DabEnsemble) -> None:
        """
        Update ensemble configuration.

        This rebuilds the FIG carousel with the new configuration.

        Args:
            ensemble: New ensemble configuration
        """
        self.ensemble = ensemble
        self.carousel.clear()
        self._setup_figs()
        logger.info("FIC encoder updated with new ensemble configuration")
