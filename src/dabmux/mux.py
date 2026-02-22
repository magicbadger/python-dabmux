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

# MOT carousel support (Phase 6)
from dabmux.mot.carousel import CarouselManager

# EDI support (Priority 5)
from dabmux.edi.encoder import EdiEncoder
from dabmux.output.edi import EdiOutput
from dabmux.output.edi_tcp import EdiTcpOutput
from dabmux.edi.pft import PFTConfig

# Remote control support (Priority 6)
from dabmux.remote.zmq_server import ZmqServer
from dabmux.remote.telnet_server import TelnetServer

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

        # MOT carousel managers (Phase 6) - keyed by component UID
        self.carousel_managers: Dict[str, CarouselManager] = {}

        # EDI encoder and output (Priority 5)
        self.edi_encoder: Optional[EdiEncoder] = None
        self.edi_output: Optional[DabOutput] = None

        # Remote control (Priority 6)
        self.zmq_server: Optional[ZmqServer] = None
        self.telnet_server: Optional[TelnetServer] = None
        self.start_time: float = 0.0  # For uptime tracking

        # Remote control auth and audit (Phase 4)
        self.authenticator: Optional[Any] = None
        self.audit_logger: Optional[Any] = None
        self._setup_remote_control()

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

    def setup_carousels(self) -> None:
        """
        Setup MOT carousel managers for components with carousel enabled.

        Creates CarouselManager instances for all components that have
        carousel_enabled=True and a valid carousel_directory.
        """
        for component in self.ensemble.components:
            if not component.carousel_enabled:
                continue

            if not component.carousel_directory:
                logger.warning(
                    "Carousel enabled but no directory specified",
                    component=component.uid
                )
                continue

            # Check if component is packet mode
            if not component.is_packet_mode:
                logger.warning(
                    "Carousel enabled for non-packet-mode component",
                    component=component.uid
                )
                continue

            # Get subchannel for address and bitrate
            subchannel = self.ensemble.get_subchannel_by_id(component.subchannel_id)
            if not subchannel:
                logger.warning(
                    "Component subchannel not found",
                    component=component.uid,
                    subchannel_id=component.subchannel_id
                )
                continue

            # Create carousel manager
            # Address: use subchannel start_address (default 0)
            # Max packet size: based on subchannel bitrate (96 bytes for 96 kbps)
            address = subchannel.start_address
            max_packet_size = subchannel.bitrate  # 96 kbps → 96 bytes

            try:
                carousel = CarouselManager(
                    directory=component.carousel_directory,
                    address=address,
                    max_packet_size=max_packet_size,
                    enable_watching=True  # Enable hot-reload
                )

                self.carousel_managers[component.uid] = carousel

                logger.info(
                    "Carousel configured for component",
                    component=component.uid,
                    directory=component.carousel_directory,
                    address=address,
                    max_packet_size=max_packet_size,
                    num_objects=len(carousel.objects)
                )

            except Exception as e:
                logger.error(
                    "Failed to setup carousel",
                    component=component.uid,
                    directory=component.carousel_directory,
                    error=str(e)
                )

    def _setup_remote_control(self) -> None:
        """Setup authentication and audit logging for remote control."""
        if not self.ensemble.remote_control:
            return

        config = self.ensemble.remote_control

        # Setup authentication
        if config.auth_enabled:
            from dabmux.remote.auth import Authenticator, parse_password_hash

            password = None
            password_hash = None

            if config.auth_password_hash:
                # Use pre-hashed password
                if config.auth_password_hash.startswith("sha256:"):
                    password_hash = parse_password_hash(config.auth_password_hash)
                else:
                    password_hash = config.auth_password_hash
            elif config.auth_password:
                # Use plain text password
                password = config.auth_password

            if password or password_hash:
                self.authenticator = Authenticator(
                    password=password,
                    password_hash=password_hash
                )
                logger.info("Remote control authentication enabled")
            else:
                logger.warning("Authentication enabled but no password configured")

        # Setup audit logging
        if config.audit_enabled and config.audit_log_file:
            from dabmux.remote.audit import AuditLogger

            self.audit_logger = AuditLogger(config.audit_log_file)
            logger.info("Remote control audit logging enabled",
                       log_file=config.audit_log_file)

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

    def start_zmq_server(self, bind_address: str = "tcp://*:9000") -> None:
        """
        Start ZeroMQ remote control server.

        Args:
            bind_address: ZMQ bind address
        """
        import time
        self.start_time = time.time()

        self.zmq_server = ZmqServer(
            bind_address,
            authenticator=self.authenticator,
            audit_logger=self.audit_logger
        )

        # Register handlers
        self.zmq_server.register_handler("get_statistics", self._zmq_get_statistics)
        self.zmq_server.register_handler("get_label", self._zmq_get_label)
        self.zmq_server.register_handler("set_label", self._zmq_set_label)
        self.zmq_server.register_handler("trigger_announcement", self._zmq_trigger_announcement)
        self.zmq_server.register_handler("clear_announcement", self._zmq_clear_announcement)
        self.zmq_server.register_handler("get_service_info", self._zmq_get_service_info)
        self.zmq_server.register_handler("get_input_status", self._zmq_get_input_status)
        self.zmq_server.register_handler("reload_carousel", self._zmq_reload_carousel)
        self.zmq_server.register_handler("get_carousel_stats", self._zmq_get_carousel_stats)

        # Phase 2: Service parameter management
        self.zmq_server.register_handler("set_service_pty", self._zmq_set_service_pty)
        self.zmq_server.register_handler("set_service_language", self._zmq_set_service_language)
        self.zmq_server.register_handler("set_service_label", self._zmq_set_service_label)
        self.zmq_server.register_handler("get_all_services", self._zmq_get_all_services)
        self.zmq_server.register_handler("get_all_components", self._zmq_get_all_components)
        self.zmq_server.register_handler("get_all_subchannels", self._zmq_get_all_subchannels)

        # Utility
        self.zmq_server.register_handler("list_commands", self._zmq_list_commands)
        self.zmq_server.register_handler("get_command_info", self._zmq_get_command_info)

        # Phase 4: Logging control
        self.zmq_server.register_handler("set_log_level", self._zmq_set_log_level)
        self.zmq_server.register_handler("get_log_level", self._zmq_get_log_level)

        self.zmq_server.start()
        logger.info("ZMQ remote control enabled", address=bind_address)

    def stop_zmq_server(self) -> None:
        """Stop ZeroMQ server."""
        if self.zmq_server:
            self.zmq_server.stop()
            self.zmq_server = None

    def start_telnet_server(self, bind_address: str = "0.0.0.0", port: int = 9001) -> None:
        """
        Start telnet remote control server.

        Args:
            bind_address: Bind address (default: 0.0.0.0)
            port: Port number (default: 9001)
        """
        import time
        if self.start_time == 0:
            self.start_time = time.time()

        self.telnet_server = TelnetServer(
            bind_address,
            port,
            authenticator=self.authenticator,
            audit_logger=self.audit_logger
        )

        # Register same handlers as ZMQ server
        self.telnet_server.register_handler("get_statistics", self._zmq_get_statistics)
        self.telnet_server.register_handler("get_label", self._zmq_get_label)
        self.telnet_server.register_handler("set_label", self._zmq_set_label)
        self.telnet_server.register_handler("trigger_announcement", self._zmq_trigger_announcement)
        self.telnet_server.register_handler("clear_announcement", self._zmq_clear_announcement)
        self.telnet_server.register_handler("get_service_info", self._zmq_get_service_info)
        self.telnet_server.register_handler("get_input_status", self._zmq_get_input_status)
        self.telnet_server.register_handler("reload_carousel", self._zmq_reload_carousel)
        self.telnet_server.register_handler("get_carousel_stats", self._zmq_get_carousel_stats)

        # Phase 2: Service parameter management
        self.telnet_server.register_handler("set_service_pty", self._zmq_set_service_pty)
        self.telnet_server.register_handler("set_service_language", self._zmq_set_service_language)
        self.telnet_server.register_handler("set_service_label", self._zmq_set_service_label)
        self.telnet_server.register_handler("get_all_services", self._zmq_get_all_services)
        self.telnet_server.register_handler("get_all_components", self._zmq_get_all_components)
        self.telnet_server.register_handler("get_all_subchannels", self._zmq_get_all_subchannels)

        # Utility
        self.telnet_server.register_handler("list_commands", self._zmq_list_commands)
        self.telnet_server.register_handler("get_command_info", self._zmq_get_command_info)

        # Phase 4: Logging control
        self.telnet_server.register_handler("set_log_level", self._zmq_set_log_level)
        self.telnet_server.register_handler("get_log_level", self._zmq_get_log_level)

        self.telnet_server.start()
        logger.info("Telnet remote control enabled", address=bind_address, port=port)

    def stop_telnet_server(self) -> None:
        """Stop telnet server."""
        if self.telnet_server:
            self.telnet_server.stop()
            self.telnet_server = None

    # ZMQ command handlers

    def _zmq_get_statistics(self, args: Dict) -> Dict:
        """Get multiplexer statistics."""
        import time
        uptime = time.time() - self.start_time if self.start_time > 0 else 0

        return {
            "frame_count": self.frame_count,
            "uptime_seconds": uptime,
            "ensemble_id": f"0x{self.ensemble.id:04X}",
            "ensemble_label": self.ensemble.label.text,
            "num_services": len(self.ensemble.services),
            "num_subchannels": len(self.ensemble.subchannels),
            "num_components": len(self.ensemble.components),
        }

    def _zmq_get_label(self, args: Dict) -> Dict:
        """Get dynamic label for component."""
        component_uid = args.get("component_uid")
        if not component_uid:
            raise ValueError("Missing component_uid")

        component = self.ensemble.get_component(component_uid)
        if not component:
            raise ValueError(f"Component not found: {component_uid}")

        if not component.dynamic_label:
            raise ValueError(f"Component has no dynamic label: {component_uid}")

        return {
            "text": component.dynamic_label.text,
            "charset": component.dynamic_label.charset,
            "toggle": component.dynamic_label.toggle
        }

    def _zmq_set_label(self, args: Dict) -> Dict:
        """Set dynamic label for component."""
        component_uid = args.get("component_uid")
        text = args.get("text")

        if not component_uid or text is None:
            raise ValueError("Missing component_uid or text")

        component = self.ensemble.get_component(component_uid)
        if not component:
            raise ValueError(f"Component not found: {component_uid}")

        if not component.dynamic_label:
            # Create dynamic label if doesn't exist
            from dabmux.core.mux_elements import DynamicLabel
            component.dynamic_label = DynamicLabel(text=text)
        else:
            # Update existing label
            component.dynamic_label.update_text(text)

        logger.info("Dynamic label updated via ZMQ",
                   component=component_uid,
                   text=text[:30])

        return {"success": True}

    def _zmq_trigger_announcement(self, args: Dict) -> Dict:
        """Trigger announcement."""
        service_id = args.get("service_id")
        ann_type = args.get("type")
        subchannel_id = args.get("subchannel_id")

        if service_id is None or not ann_type or subchannel_id is None:
            raise ValueError("Missing service_id, type, or subchannel_id")

        # Create active announcement
        announcement = ActiveAnnouncement(
            service_id=service_id,
            announcement_type=ann_type,
            subchannel_id=subchannel_id,
            new_flag=True,
            region_id=0
        )

        # Add to ensemble active announcements
        self.ensemble.active_announcements.append(announcement)

        logger.info("Announcement triggered via ZMQ",
                   service_id=f"0x{service_id:04X}",
                   type=ann_type,
                   subchannel_id=subchannel_id)

        return {"success": True}

    def _zmq_clear_announcement(self, args: Dict) -> Dict:
        """Clear active announcement."""
        service_id = args.get("service_id")
        ann_type = args.get("type")

        if service_id is None or not ann_type:
            raise ValueError("Missing service_id or type")

        # Remove matching announcement
        self.ensemble.active_announcements = [
            ann for ann in self.ensemble.active_announcements
            if not (ann.service_id == service_id and ann.announcement_type == ann_type)
        ]

        logger.info("Announcement cleared via ZMQ",
                   service_id=f"0x{service_id:04X}",
                   type=ann_type)

        return {"success": True}

    def _zmq_get_service_info(self, args: Dict) -> Dict:
        """Get service information."""
        service_uid = args.get("service_uid")
        if not service_uid:
            raise ValueError("Missing service_uid")

        service = self.ensemble.get_service(service_uid)
        if not service:
            raise ValueError(f"Service not found: {service_uid}")

        return {
            "id": service.id,
            "label": service.label.text,
            "short_label": service.label.short_text,
            "pty": service.pty,
            "language": service.language
        }

    def _zmq_get_input_status(self, args: Dict) -> Dict:
        """Get input source status."""
        subchannel_uid = args.get("subchannel_uid")
        if not subchannel_uid:
            raise ValueError("Missing subchannel_uid")

        input_source = self.inputs.get(subchannel_uid)
        if not input_source:
            raise ValueError(f"Input not found: {subchannel_uid}")

        return {
            "connected": input_source.is_open,
            "input_type": type(input_source).__name__
        }

    def _zmq_reload_carousel(self, args: Dict) -> Dict:
        """Reload MOT carousel from directory."""
        component_uid = args.get("component_uid")
        if not component_uid:
            raise ValueError("Missing component_uid")

        carousel = self.carousel_managers.get(component_uid)
        if not carousel:
            raise ValueError(f"Carousel not found: {component_uid}")

        carousel.reload()

        logger.info("Carousel reloaded via ZMQ",
                   component=component_uid,
                   objects=len(carousel.objects))

        return {"objects_loaded": len(carousel.objects)}

    def _zmq_get_carousel_stats(self, args: Dict) -> Dict:
        """Get carousel statistics."""
        component_uid = args.get("component_uid")
        if not component_uid:
            raise ValueError("Missing component_uid")

        carousel = self.carousel_managers.get(component_uid)
        if not carousel:
            raise ValueError(f"Carousel not found: {component_uid}")

        stats = carousel.get_statistics()

        return {
            "num_objects": stats["num_objects"],
            "total_bytes": stats["total_bytes"],
            "packets_transmitted": stats["packets_transmitted"]
        }

    def _zmq_list_commands(self, args: Dict) -> Dict:
        """List all available commands."""
        from dabmux.remote.protocol import COMMANDS
        return {"commands": list(COMMANDS.keys())}

    def _zmq_get_command_info(self, args: Dict) -> Dict:
        """Get information about a specific command."""
        command = args.get("command")
        if not command:
            raise ValueError("Missing command")

        from dabmux.remote.protocol import COMMANDS

        if command not in COMMANDS:
            raise ValueError(f"Unknown command: {command}")

        return COMMANDS[command]

    # Phase 4: Runtime logging control handlers

    def _zmq_set_log_level(self, args: Dict) -> Dict:
        """Set logging level at runtime."""
        level_name = args.get("level", "INFO").upper()
        module = args.get("module")  # Optional

        import logging

        # Validate level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level_name not in valid_levels:
            raise ValueError(f"Invalid log level: {level_name}. Must be one of: {', '.join(valid_levels)}")

        level = getattr(logging, level_name)

        if module:
            # Set specific module
            module_logger = logging.getLogger(module)
            module_logger.setLevel(level)
            message = f"Set {module} log level to {level_name}"
            logger.info(message)
        else:
            # Set root logger
            logging.getLogger().setLevel(level)
            message = f"Set global log level to {level_name}"
            logger.info(message)

        return {
            "success": True,
            "level": level_name,
            "module": module or "global",
            "message": message
        }

    def _zmq_get_log_level(self, args: Dict) -> Dict:
        """Get current logging level."""
        import logging

        module = args.get("module")

        if module:
            module_logger = logging.getLogger(module)
            level = module_logger.getEffectiveLevel()
        else:
            level = logging.getLogger().getEffectiveLevel()

        level_name = logging.getLevelName(level)

        return {
            "level": level_name,
            "numeric_level": level,
            "module": module or "global"
        }

    # Phase 2: Service parameter management handlers

    def _zmq_set_service_pty(self, args: Dict) -> Dict:
        """Set service Programme Type."""
        service_uid = args.get("service_uid")
        pty = args.get("pty")

        if not service_uid or pty is None:
            raise ValueError("Missing service_uid or pty")

        if not (0 <= pty <= 31):
            raise ValueError("PTY must be between 0 and 31")

        service = self.ensemble.get_service(service_uid)
        if not service:
            raise ValueError(f"Service not found: {service_uid}")

        old_pty = service.pty
        service.pty = pty

        logger.info("Service PTY updated via ZMQ",
                   service=service_uid,
                   old_pty=old_pty,
                   new_pty=pty)

        return {"success": True, "old_pty": old_pty, "new_pty": pty}

    def _zmq_set_service_language(self, args: Dict) -> Dict:
        """Set service language."""
        service_uid = args.get("service_uid")
        language = args.get("language")

        if not service_uid or language is None:
            raise ValueError("Missing service_uid or language")

        if not (0 <= language <= 127):
            raise ValueError("Language must be between 0 and 127")

        service = self.ensemble.get_service(service_uid)
        if not service:
            raise ValueError(f"Service not found: {service_uid}")

        old_language = service.language
        service.language = language

        logger.info("Service language updated via ZMQ",
                   service=service_uid,
                   old_language=old_language,
                   new_language=language)

        return {"success": True, "old_language": old_language, "new_language": language}

    def _zmq_set_service_label(self, args: Dict) -> Dict:
        """Set service static label."""
        service_uid = args.get("service_uid")
        text = args.get("text")
        short_text = args.get("short_text")

        if not service_uid or not text:
            raise ValueError("Missing service_uid or text")

        if len(text) > 16:
            raise ValueError("Label text must be 16 characters or less")

        if short_text and len(short_text) > 8:
            raise ValueError("Short label must be 8 characters or less")

        service = self.ensemble.get_service(service_uid)
        if not service:
            raise ValueError(f"Service not found: {service_uid}")

        old_text = service.label.text
        old_short = service.label.short_text

        service.label.text = text
        if short_text:
            service.label.short_text = short_text
        else:
            # Auto-generate short label (first 8 chars)
            service.label.short_text = text[:8]

        logger.info("Service label updated via ZMQ",
                   service=service_uid,
                   old_label=old_text,
                   new_label=text)

        return {
            "success": True,
            "old_label": old_text,
            "new_label": text,
            "old_short": old_short,
            "new_short": service.label.short_text
        }

    def _zmq_get_all_services(self, args: Dict) -> Dict:
        """Get list of all services."""
        services = []
        for service in self.ensemble.services:
            services.append({
                "uid": service.uid,
                "id": service.id,
                "label": service.label.text,
                "short_label": service.label.short_text,
                "pty": service.pty,
                "language": service.language,
            })

        return {"services": services}

    def _zmq_get_all_components(self, args: Dict) -> Dict:
        """Get list of all components."""
        components = []
        for component in self.ensemble.components:
            comp_info = {
                "uid": component.uid,
                "service_id": component.service_id,
                "subchannel_id": component.subchannel_id,
                "label": component.label.text,
                "is_packet_mode": component.is_packet_mode,
            }

            # Add dynamic label info if present
            if component.dynamic_label:
                comp_info["dynamic_label"] = {
                    "text": component.dynamic_label.text,
                    "charset": component.dynamic_label.charset,
                    "toggle": component.dynamic_label.toggle
                }

            # Add carousel info if enabled
            if component.carousel_enabled:
                comp_info["carousel"] = {
                    "enabled": True,
                    "directory": component.carousel_directory
                }

            components.append(comp_info)

        return {"components": components}

    def _zmq_get_all_subchannels(self, args: Dict) -> Dict:
        """Get list of all subchannels."""
        subchannels = []
        for subchannel in self.ensemble.subchannels:
            sub_info = {
                "uid": subchannel.uid,
                "id": subchannel.id,
                "type": subchannel.type.value,
                "bitrate": subchannel.bitrate,
                "start_address": subchannel.start_address,
                "protection": {
                    "level": subchannel.protection.level,
                    "form": subchannel.protection.form.value
                }
            }

            # Add input info if connected
            if subchannel.uid in self.inputs:
                input_source = self.inputs[subchannel.uid]
                sub_info["input"] = {
                    "connected": input_source.is_open,
                    "type": type(input_source).__name__
                }

            subchannels.append(sub_info)

        return {"subchannels": subchannels}

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
        frame = EtiFrame.create_empty(mode=mode, with_tist=self.ensemble.enable_tist)

        # Update frame count
        frame.fc.fct = self.frame_count & 0xFF
        frame.fc.nst = len(self.ensemble.subchannels)

        # Alternate FSYNC between frames (required by ETSI EN 300 799)
        # Even frames: 0x073AB6, Odd frames: 0xF8C549
        if self.frame_count % 2 == 0:
            frame.sync.fsync = 0x073AB6
        else:
            frame.sync.fsync = 0xF8C549

        # Generate TIST timestamp if enabled (Priority 5.5 - Enhanced ETI)
        if self.ensemble.enable_tist:
            import time
            # Current time in seconds + offset for delay compensation
            current_time = time.time() + self.ensemble.tist_offset
            # Convert to TIST units (1/16.384 MHz = ~61 ns resolution)
            # Formula: TIST = seconds * 16,384,000
            tist_value = int(current_time * 16384000) & 0xFFFFFFFF  # 32-bit wrap
            frame.tist.tist = tist_value

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
            from dabmux.core.mux_elements import SubchannelType

            # Handle packet mode subchannels with MOT carousel (Phase 6)
            if subchannel.type == SubchannelType.Packet:
                # Find component associated with this subchannel
                component = None
                for comp in self.ensemble.components:
                    if comp.subchannel_id == subchannel.id:
                        component = comp
                        break

                # Check if component has carousel enabled
                if component and component.uid in self.carousel_managers:
                    carousel = self.carousel_managers[component.uid]

                    # Get next packet from carousel
                    packet = carousel.get_next_packet()

                    if packet:
                        # Encode packet
                        packet_data = packet.encode()

                        # Pad to 8-byte boundary as required by ETI
                        padding_needed = (8 - (len(packet_data) % 8)) % 8
                        frame_data = packet_data + bytes(padding_needed)
                        mst_data.extend(frame_data)

                        # Create STC header
                        stl = len(frame_data) // 8  # Size in 64-bit words
                        stc = EtiSTC(
                            scid=subchannel.id,
                            start_address=subchannel.start_address,
                            tpl=subchannel.protection.to_tpl(subchannel.bitrate),
                            stl=stl
                        )
                        frame.stc_headers.append(stc)
                    else:
                        # No packet available, use empty data
                        subchannel_size = subchannel.bitrate * 3
                        empty_data = bytes(subchannel_size)
                        padding_needed = (8 - (len(empty_data) % 8)) % 8
                        frame_data = empty_data + bytes(padding_needed)
                        mst_data.extend(frame_data)

                        stl = len(frame_data) // 8
                        stc = EtiSTC(
                            scid=subchannel.id,
                            start_address=subchannel.start_address,
                            tpl=subchannel.protection.to_tpl(subchannel.bitrate),
                            stl=stl
                        )
                        frame.stc_headers.append(stc)
                else:
                    # No carousel configured, use empty data
                    subchannel_size = subchannel.bitrate * 3
                    empty_data = bytes(subchannel_size)
                    padding_needed = (8 - (len(empty_data) % 8)) % 8
                    frame_data = empty_data + bytes(padding_needed)
                    mst_data.extend(frame_data)

                    stl = len(frame_data) // 8
                    stc = EtiSTC(
                        scid=subchannel.id,
                        start_address=subchannel.start_address,
                        tpl=subchannel.protection.to_tpl(subchannel.bitrate),
                        stl=stl
                    )
                    frame.stc_headers.append(stc)

                # Skip audio processing for packet mode
                continue

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
