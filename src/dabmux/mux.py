"""
DAB Multiplexer implementation.

This module provides the core multiplexer that combines audio/data streams
into ETI frames for DAB transmission.
"""
from typing import List, Dict, Optional
import structlog

from dabmux.core.eti import EtiFrame
from dabmux.core.mux_elements import DabEnsemble, DabSubchannel, ActiveAnnouncement, EdiOutputConfig
from dabmux.input.base import InputBase
from dabmux.input.dabplus_input import DABPlusInput
from dabmux.output.base import DabOutput
from dabmux.utils.crc import crc16
from dabmux.fig.fic import FICEncoder
from dabmux.pad.base import PADInput
from dabmux.pad.dls import DLSEncoder
from dabmux.pad.xpad import XPADEncoder
from dabmux.pad.input.file_monitor import FileMonitorInput

# EDI support (Priority 5)
from dabmux.edi.encoder import EdiEncoder
from dabmux.output.edi import EdiOutput
from dabmux.output.edi_tcp import EdiTcpOutput
from dabmux.edi.pft import PFTConfig

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

        # PAD (Programme Associated Data) encoders and inputs
        self.pad_encoders: Dict[str, XPADEncoder] = {}
        self.pad_inputs: Dict[str, PADInput] = {}

        # EDI encoder and output (Priority 5)
        self.edi_encoder: Optional[EdiEncoder] = None
        self.edi_output: Optional[DabOutput] = None

        # Initialize EDI if configured
        if ensemble.edi_output and ensemble.edi_output.enabled:
            self._setup_edi_output(ensemble.edi_output)

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

        # Setup PAD if configured for this subchannel
        if subchannel.pad and subchannel.pad.enabled:
            self._setup_pad(subchannel)

    def add_output(self, output: DabOutput) -> None:
        """
        Add an output destination.

        Args:
            output: Output instance
        """
        self.outputs.append(output)
        logger.info("Added output", info=output.get_info())

    def _setup_pad(self, subchannel: DabSubchannel) -> None:
        """
        Setup PAD encoder for a subchannel.

        Creates DLS encoder, PAD input source, and X-PAD encoder
        for the given subchannel based on its PAD configuration.

        Args:
            subchannel: Subchannel with PAD configuration
        """
        pad_config = subchannel.pad
        if not pad_config or not pad_config.enabled:
            return

        if not pad_config.dls or not pad_config.dls.enabled:
            logger.info("PAD enabled but DLS disabled", subchannel=subchannel.uid)
            return

        # Check if input is pre-encoded DAB+ stream (.dabp file, UDP, FIFO)
        input_source = self.inputs.get(subchannel.uid)
        if input_source and isinstance(input_source, DABPlusInput):
            # Pre-encoded DAB+ streams from ODR-AudioEnc are already RS-encoded
            # PAD cannot be added after encoding
            logger.warning(
                "PAD/DLS not supported with pre-encoded DAB+ streams from ODR-AudioEnc",
                subchannel=subchannel.uid,
                note="Encode PAD during audio encoding with odr-audioenc --pad option"
            )
            return

        # Create DLS encoder
        dls_encoder = DLSEncoder(charset=pad_config.dls.charset)

        # Set default label if provided
        if pad_config.dls.default_label:
            dls_encoder.set_label(pad_config.dls.default_label)

        # Create PAD input source based on type
        pad_input: Optional[PADInput] = None

        if pad_config.dls.input_type == 'file':
            if not pad_config.dls.input_path:
                logger.warning("File input type specified but no path provided",
                             subchannel=subchannel.uid)
                return

            pad_input = FileMonitorInput(
                file_path=pad_config.dls.input_path,
                poll_interval=pad_config.dls.poll_interval
            )

        elif pad_config.dls.input_type == 'fifo':
            logger.warning("FIFO input not yet implemented", subchannel=subchannel.uid)
            return

        elif pad_config.dls.input_type == 'zeromq':
            logger.warning("ZeroMQ input not yet implemented", subchannel=subchannel.uid)
            return

        else:
            logger.error("Unknown PAD input type",
                        subchannel=subchannel.uid,
                        input_type=pad_config.dls.input_type)
            return

        # Load initial DLS text from input if available
        if pad_input:
            initial_text = pad_input.get_dls_text()
            if initial_text:
                dls_encoder.set_label(initial_text)
                logger.info("Initial DLS text loaded",
                          subchannel=subchannel.uid,
                          text=initial_text[:50])

        # Create X-PAD encoder
        xpad_encoder = XPADEncoder(
            pad_length=pad_config.length,
            dls_encoder=dls_encoder
        )

        # Store encoders
        self.pad_encoders[subchannel.uid] = xpad_encoder
        self.pad_inputs[subchannel.uid] = pad_input

        logger.info("PAD configured for subchannel",
                   subchannel=subchannel.uid,
                   pad_length=pad_config.length,
                   input_type=pad_config.dls.input_type,
                   input_path=pad_config.dls.input_path)

    def _setup_edi_output(self, config: EdiOutputConfig) -> None:
        """
        Setup EDI encoder and output.

        Args:
            config: EDI output configuration
        """
        # Create EDI encoder
        self.edi_encoder = EdiEncoder(self.ensemble)

        # Parse destination (host:port)
        parts = config.destination.split(':')
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 12000

        # Create EDI output based on protocol
        if config.protocol == "udp":
            # Create PFT config if enabled
            pft_config = None
            if config.enable_pft:
                pft_config = PFTConfig(
                    fec=config.pft_fec > 0,
                    fec_m=config.pft_fec,
                    max_fragment_size=config.pft_fragment_size
                )

            self.edi_output = EdiOutput(
                dest_addr=host,
                dest_port=port,
                source_port=config.source_port,
                enable_pft=config.enable_pft,
                pft_config=pft_config
            )

        elif config.protocol == "tcp":
            self.edi_output = EdiTcpOutput(
                mode=config.tcp_mode,
                host=host,
                port=port
            )

        else:
            raise ValueError(f"Unknown EDI protocol: {config.protocol}")

        # Open the output
        self.edi_output.open()

        logger.info(
            "EDI output configured",
            protocol=config.protocol,
            destination=config.destination,
            pft=config.enable_pft if config.protocol == "udp" else None,
            mode=config.tcp_mode if config.protocol == "tcp" else None
        )

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

        # Update PAD inputs (check for DLS text changes)
        for uid, pad_input in self.pad_inputs.items():
            if pad_input.update():
                # DLS text changed
                new_text = pad_input.get_dls_text()
                if new_text and uid in self.pad_encoders:
                    encoder = self.pad_encoders[uid]
                    encoder.dls_encoder.set_label(new_text)
                    logger.debug("DLS updated", subchannel=uid, text=new_text[:30])

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
                    # Provide PAD to input BEFORE reading (for inputs with FEC like AAC)
                    if subchannel.uid in self.pad_encoders and hasattr(input_source, 'set_pad_data'):
                        pad_encoder = self.pad_encoders[subchannel.uid]
                        pad_data = pad_encoder.encode_pad()
                        input_source.set_pad_data(pad_data)

                    # Read frame (already includes PAD if input supports set_pad_data)
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

                    # Ensure we have exactly subchannel_size bytes of audio
                    frame_data = data[:subchannel_size]

                    # For inputs without set_pad_data, append PAD after reading (MPEG pattern)
                    if subchannel.uid in self.pad_encoders and not hasattr(input_source, 'set_pad_data'):
                        pad_encoder = self.pad_encoders[subchannel.uid]
                        pad_data = pad_encoder.encode_pad()
                        frame_data += pad_data

                    # Pad to 8-byte boundary as required by ETI
                    padding_needed = (8 - (len(frame_data) % 8)) % 8
                    frame_data += bytes(padding_needed)
                    mst_data.extend(frame_data)

                except Exception as e:
                    logger.error(
                        "Failed to read from input",
                        subchannel=subchannel.uid,
                        error=str(e)
                    )
                    # Use silence on error (with PAD if configured)
                    silence = bytes(subchannel_size)
                    if subchannel.uid in self.pad_encoders and not hasattr(input_source, 'set_pad_data'):
                        pad_encoder = self.pad_encoders[subchannel.uid]
                        pad_data = pad_encoder.encode_pad()
                        silence += pad_data
                    # Pad to 8-byte boundary
                    padding_needed = (8 - (len(silence) % 8)) % 8
                    mst_data.extend(silence + bytes(padding_needed))
            else:
                # No input configured, use silence (with PAD if configured)
                silence = bytes(subchannel_size)
                if subchannel.uid in self.pad_encoders:
                    pad_encoder = self.pad_encoders[subchannel.uid]
                    pad_data = pad_encoder.encode_pad()
                    silence += pad_data
                # Pad to 8-byte boundary
                padding_needed = (8 - (len(silence) % 8)) % 8
                mst_data.extend(silence + bytes(padding_needed))

            # Create STC header
            # STL is size in 64-bit words, includes audio + PAD if configured
            actual_size = subchannel_size
            if subchannel.uid in self.pad_encoders and not hasattr(input_source, 'set_pad_data'):
                # Only add PAD size if input doesn't embed PAD (MPEG pattern)
                pad_encoder = self.pad_encoders[subchannel.uid]
                actual_size += pad_encoder.pad_length

            stl = (actual_size + 7) // 8  # Round up to 64-bit words

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

        # Send to EDI output if configured (Priority 5)
        if self.edi_encoder and self.edi_output:
            af_packet = self.edi_encoder.encode_frame(frame)
            self.edi_output.write(af_packet)

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

    def start_announcement(
        self,
        cluster_id: int,
        types: List[str],
        subchannel_id: int,
        region_id: int = 0,
        new_flag: bool = True
    ) -> None:
        """
        Start an announcement.

        Adds an active announcement to the ensemble, which will be signalled
        via FIG 0/19. Receivers will switch to the announcement subchannel.

        Args:
            cluster_id: Cluster ID (announcement group)
            types: List of announcement types (e.g., ['alarm', 'news'])
            subchannel_id: Subchannel ID carrying the announcement
            region_id: Optional region ID (default: 0)
            new_flag: New announcement flag (default: True)

        Raises:
            ValueError: If announcement types are invalid
        """
        # Validate announcement types
        from dabmux.fig.fig0 import ANNOUNCEMENT_TYPES
        for ann_type in types:
            if ann_type.lower() not in ANNOUNCEMENT_TYPES:
                raise ValueError(f"Invalid announcement type: {ann_type}")

        # Check if announcement already exists for this cluster
        for existing in self.ensemble.active_announcements:
            if existing.cluster_id == cluster_id:
                logger.warning(
                    "Announcement already active for cluster, updating",
                    cluster_id=cluster_id
                )
                existing.types = types
                existing.subchannel_id = subchannel_id
                existing.region_id = region_id
                existing.new_flag = new_flag
                return

        # Create new active announcement
        announcement = ActiveAnnouncement(
            cluster_id=cluster_id,
            types=types,
            subchannel_id=subchannel_id,
            new_flag=new_flag,
            region_flag=region_id != 0,
            region_id=region_id
        )

        self.ensemble.active_announcements.append(announcement)

        logger.info(
            "Started announcement",
            cluster_id=cluster_id,
            types=types,
            subchannel_id=subchannel_id
        )

    def stop_announcement(self, cluster_id: int) -> bool:
        """
        Stop an announcement.

        Removes the active announcement from the ensemble. FIG 0/19 will
        no longer signal this announcement.

        Args:
            cluster_id: Cluster ID of announcement to stop

        Returns:
            True if announcement was stopped, False if not found
        """
        initial_count = len(self.ensemble.active_announcements)

        self.ensemble.active_announcements = [
            a for a in self.ensemble.active_announcements
            if a.cluster_id != cluster_id
        ]

        if len(self.ensemble.active_announcements) < initial_count:
            logger.info("Stopped announcement", cluster_id=cluster_id)
            return True
        else:
            logger.warning("Announcement not found", cluster_id=cluster_id)
            return False

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
