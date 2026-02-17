"""
DAB Multiplexer implementation.

This module provides the core multiplexer that combines audio/data streams
into ETI frames for DAB transmission.
"""
from typing import List, Dict, Optional
import structlog

from dabmux.core.eti import EtiFrame
from dabmux.core.mux_elements import DabEnsemble, DabSubchannel
from dabmux.input.base import InputBase
from dabmux.output.base import DabOutput
from dabmux.utils.crc import crc16
from dabmux.fig.fic import FICEncoder

logger = structlog.get_logger()


class DabMultiplexer:
    """
    DAB Multiplexer.

    Combines multiple audio/data streams into a single DAB multiplex,
    generating ETI frames for transmission or recording.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize the multiplexer.

        Args:
            ensemble: Ensemble configuration
        """
        self.ensemble = ensemble
        self.inputs: Dict[str, InputBase] = {}
        self.outputs: List[DabOutput] = []
        self.frame_count: int = 0
        self._running: bool = False

        # Initialize FIC encoder
        self.fic_encoder = FICEncoder(ensemble)

    def add_input(self, subchannel_uid: str, input_source: InputBase) -> None:
        """
        Add an input source for a subchannel.

        Args:
            subchannel_uid: Subchannel UID
            input_source: Input source instance

        Raises:
            ValueError: If subchannel doesn't exist or input already exists
        """
        # Verify subchannel exists
        subchannel = self.ensemble.get_subchannel(subchannel_uid)
        if subchannel is None:
            raise ValueError(f"Subchannel {subchannel_uid} not found in ensemble")

        if subchannel_uid in self.inputs:
            raise ValueError(f"Input for subchannel {subchannel_uid} already exists")

        self.inputs[subchannel_uid] = input_source
        logger.info("Added input", subchannel=subchannel_uid)

    def add_output(self, output: DabOutput) -> None:
        """
        Add an output destination.

        Args:
            output: Output instance
        """
        self.outputs.append(output)
        logger.info("Added output", info=output.get_info())

    def generate_frame(self) -> EtiFrame:
        """
        Generate a single ETI frame.

        Reads data from all inputs and constructs an ETI frame.

        Returns:
            Complete ETI frame

        Raises:
            RuntimeError: If frame generation fails
        """
        # Create frame with ensemble configuration
        mode = int(self.ensemble.transmission_mode)
        frame = EtiFrame.create_empty(mode=mode, with_tist=False)

        # Update frame count
        frame.fc.fct = self.frame_count & 0xFF
        frame.fc.nst = len(self.ensemble.subchannels)

        # Alternate FSYNC between frames (required by ETSI EN 300 799)
        # Even frames: 0x073AB6, Odd frames: 0xF8C549
        if self.frame_count % 2 == 0:
            frame.sync.fsync = 0x073AB6
        else:
            frame.sync.fsync = 0xF8C549

        # Generate FIC data using FIC encoder (Phase 2)
        fic_data = self.fic_encoder.encode_fic(self.frame_count)
        frame.fic_data = fic_data

        # Read subchannel data from inputs (Phase 3)
        mst_data = bytearray()

        # Add STC headers and read data for each subchannel
        for subchannel in self.ensemble.subchannels:
            from dabmux.core.eti import EtiSTC

            # Calculate subchannel size in bytes
            # For DAB: bitrate * 3 bytes (bitrate in kbps, 24ms frame = 3 bytes per kbps)
            # For DAB+ with FEC: use actual frame size from input (includes RS overhead)
            input_source = self.inputs.get(subchannel.uid)
            if input_source and hasattr(input_source, 'get_frame_size'):
                frame_size = input_source.get_frame_size()
                subchannel_size = frame_size if frame_size > 0 else subchannel.bitrate * 3
            else:
                subchannel_size = subchannel.bitrate * 3

            # Read data from input if available
            if input_source and input_source.is_open:
                try:
                    data = input_source.read_frame(subchannel_size)
                    if len(data) < subchannel_size:
                        # Pad with zeros if underrun
                        logger.warning(
                            "Input underrun, padding with zeros",
                            subchannel=subchannel.uid,
                            expected=subchannel_size,
                            received=len(data)
                        )
                        data += bytes(subchannel_size - len(data))
                    mst_data.extend(data[:subchannel_size])
                except Exception as e:
                    logger.error(
                        "Failed to read from input",
                        subchannel=subchannel.uid,
                        error=str(e)
                    )
                    # Use silence on error
                    mst_data.extend(bytes(subchannel_size))
            else:
                # No input configured, use silence
                mst_data.extend(bytes(subchannel_size))

            # Create STC header
            # STL is size in 64-bit words
            stl = (subchannel_size + 7) // 8  # Round up to 64-bit words

            stc = EtiSTC(
                scid=subchannel.id,
                start_address=subchannel.start_address,
                tpl=subchannel.protection.to_tpl(subchannel.bitrate),
                stl=stl
            )
            frame.stc_headers.append(stc)

        # Set subchannel data in frame
        frame.subchannel_data = bytes(mst_data)

        # Calculate frame length
        # Per ETSI EN 300 799, FL (Frame Length) includes: STC + FIC + MST + EOF
        # It does NOT include FC or EOH (these come before FL starts counting)
        # This matches dablin's formula: FIC+MST = (FL - NST - 1) * 4

        # STC headers in words
        stc_words = len(self.ensemble.subchannels)

        # FIC size in words (96 bytes = 24 words for Mode I)
        fic_words = len(fic_data) // 4

        # Subchannel data in words
        mst_words = (len(mst_data) + 3) // 4  # Round up

        # EOF is 1 word (4 bytes)
        eof_words = 1

        # FL = STC + FIC + MST + EOF
        frame_length = stc_words + fic_words + mst_words + eof_words
        frame.fc.set_frame_length(frame_length)

        # Calculate CRC for FC+STC+MNSC section
        # CRC covers: FC, all STCs, and MNSC (but not the CRC itself)
        header_data = bytearray()
        header_data.extend(frame.fc.pack())
        for stc in frame.stc_headers:
            header_data.extend(stc.pack())
        # Add MNSC (2 bytes) to CRC calculation
        header_data.extend(frame.eoh.mnsc.to_bytes(2, 'big'))

        # EOH CRC: XOR with 0xFFFF per ETSI EN 300 799
        frame.eoh.crc = crc16(bytes(header_data)) ^ 0xFFFF

        # Calculate CRC for MST (FIC + subchannel data)
        # EOF CRC: XOR with 0xFFFF per ETSI EN 300 799
        mst_crc_data = frame.fic_data + frame.subchannel_data
        frame.eof.crc = crc16(mst_crc_data) ^ 0xFFFF

        self.frame_count += 1
        return frame

    def write_frame(self, frame: EtiFrame) -> None:
        """
        Write a frame to all outputs.

        Args:
            frame: ETI frame to write

        Raises:
            RuntimeError: If write fails
        """
        frame_data = frame.pack()

        for output in self.outputs:
            try:
                output.write(frame_data)
            except Exception as e:
                logger.error("Failed to write frame", output=output.get_info(), error=str(e))
                raise RuntimeError(f"Output write failed: {e}")

    def run_once(self) -> bool:
        """
        Generate and write one frame.

        Returns:
            True if successful, False if should stop

        Raises:
            RuntimeError: On critical error
        """
        try:
            frame = self.generate_frame()
            self.write_frame(frame)
            return True
        except Exception as e:
            logger.error("Error in multiplexer loop", error=str(e))
            raise

    def run(self, num_frames: Optional[int] = None) -> None:
        """
        Run the multiplexer.

        Generates frames continuously (or for a specified count) and writes
        them to all outputs.

        Args:
            num_frames: Number of frames to generate (None = infinite)

        Raises:
            RuntimeError: On critical error
        """
        self._running = True
        frame_num = 0

        logger.info("Multiplexer starting",
                   ensemble_id=f"0x{self.ensemble.id:04X}",
                   num_subchannels=len(self.ensemble.subchannels),
                   num_outputs=len(self.outputs))

        try:
            while self._running:
                if not self.run_once():
                    break

                frame_num += 1

                if num_frames is not None and frame_num >= num_frames:
                    break

                # Log progress periodically
                if frame_num % 100 == 0:
                    logger.debug("Generated frames", count=frame_num)

        finally:
            self._running = False
            logger.info("Multiplexer stopped", total_frames=frame_num)

    def stop(self) -> None:
        """Stop the multiplexer."""
        self._running = False

    def cleanup(self) -> None:
        """Clean up resources (close inputs and outputs)."""
        # Close all inputs
        for uid, input_source in self.inputs.items():
            try:
                input_source.close()
                logger.debug("Closed input", subchannel=uid)
            except Exception as e:
                logger.warning("Error closing input", subchannel=uid, error=str(e))

        # Close all outputs
        for output in self.outputs:
            try:
                output.close()
                logger.debug("Closed output", info=output.get_info())
            except Exception as e:
                logger.warning("Error closing output", info=output.get_info(), error=str(e))
