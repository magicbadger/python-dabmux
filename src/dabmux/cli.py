"""
Command-line interface for DAB multiplexer.
"""
import sys
import argparse
import signal
from pathlib import Path
from typing import Optional
import structlog

from dabmux.config import load_config
from dabmux.mux import DabMultiplexer
from dabmux.output.file import FileOutput, EtiFileType
from dabmux.core.mux_elements import EdiOutputConfig
from dabmux.input.file import MPEGFileInput, RawFileInput

logger = structlog.get_logger(__name__)


class DabMuxCLI:
    """
    Command-line interface for DAB multiplexer.
    """

    def __init__(self) -> None:
        """Initialize CLI."""
        self.mux: Optional[DabMultiplexer] = None
        self.running = False

    def parse_args(self, args: list = None) -> argparse.Namespace:
        """
        Parse command-line arguments.

        Args:
            args: Command-line arguments (default: sys.argv[1:])

        Returns:
            Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description='DAB/DAB+ Multiplexer',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  # Generate ETI file
  dabmux -c config.yaml -o output.eti -n 1000

  # Stream EDI over UDP
  dabmux -c config.yaml --edi udp://192.168.1.100:12000

  # Stream EDI with PFT and FEC
  dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fec 3

  # Stream EDI over TCP (client mode)
  dabmux -c config.yaml --edi tcp://192.168.1.100:12000

  # Stream EDI over TCP (server mode)
  dabmux -c config.yaml --edi tcp://0.0.0.0:12000 --edi-tcp-mode server

  # Output to file AND stream to network
  dabmux -c config.yaml -o archive.eti --edi udp://192.168.1.100:12000

  # Continuous multiplexing with TIST timestamps
  dabmux -c config.yaml --edi udp://192.168.1.100:12000 --tist --continuous

  # Show version
  dabmux --version
            '''
        )

        # Configuration
        parser.add_argument(
            '-c', '--config',
            metavar='FILE',
            required=True,
            help='Configuration file (YAML)'
        )

        # Output options
        parser.add_argument(
            '-o', '--output',
            metavar='FILE',
            help='Output ETI file'
        )
        parser.add_argument(
            '--edi',
            metavar='URL',
            help='EDI output URL (udp://host:port or tcp://host:port)'
        )

        # Output format (for file output)
        parser.add_argument(
            '-f', '--format',
            choices=['raw', 'streamed', 'framed'],
            default='framed',
            help='ETI output format (default: framed)'
        )

        # EDI options
        parser.add_argument(
            '--edi-tcp-mode',
            choices=['client', 'server'],
            default='client',
            help='TCP mode: client (connect) or server (listen) - for tcp:// URLs only (default: client)'
        )
        parser.add_argument(
            '--edi-source-port',
            type=int,
            default=0,
            metavar='PORT',
            help='UDP source port (0 = random) - for udp:// URLs only (default: 0)'
        )
        parser.add_argument(
            '--pft',
            action='store_true',
            help='Enable PFT (Protection, Fragmentation and Transport) for EDI'
        )
        parser.add_argument(
            '--pft-fec',
            type=int,
            default=0,
            metavar='DEPTH',
            help='PFT FEC depth (0-7, 0=disabled) - number of parity fragments (default: 0)'
        )
        parser.add_argument(
            '--pft-fragment-size',
            type=int,
            default=1400,
            metavar='SIZE',
            help='PFT maximum fragment size in bytes (default: 1400)'
        )

        # Frame generation
        parser.add_argument(
            '-n', '--num-frames',
            type=int,
            default=1,
            metavar='N',
            help='Number of frames to generate (default: 1)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Generate frames continuously until interrupted'
        )

        # TIST options
        parser.add_argument(
            '--tist',
            action='store_true',
            help='Enable timestamps (TIST)'
        )
        parser.add_argument(
            '--tist-offset',
            type=float,
            default=0.0,
            metavar='MS',
            help='TIST offset in milliseconds (default: 0)'
        )

        # Remote control
        parser.add_argument(
            '--zmq',
            type=str,
            metavar='BIND',
            help='Enable ZeroMQ server (format: tcp://*:9000)'
        )
        parser.add_argument(
            '--telnet',
            type=str,
            metavar='BIND',
            help='Enable telnet server (format: address:port, e.g., 0.0.0.0:9001)'
        )

        # Verbosity
        parser.add_argument(
            '-v', '--verbose',
            action='count',
            default=0,
            help='Increase verbosity (-v, -vv, -vvv)'
        )
        parser.add_argument(
            '-q', '--quiet',
            action='store_true',
            help='Quiet mode (errors only)'
        )

        # Version
        parser.add_argument(
            '--version',
            action='version',
            version='python-dabmux 0.6.0'
        )

        return parser.parse_args(args)

    def setup_logging(self, args: argparse.Namespace) -> None:
        """
        Setup logging based on verbosity.

        Args:
            args: Parsed arguments
        """
        import logging

        if args.quiet:
            level = logging.ERROR
        elif args.verbose >= 3:
            level = logging.DEBUG
        elif args.verbose == 2:
            level = logging.INFO
        elif args.verbose == 1:
            level = logging.WARNING
        else:
            level = logging.WARNING

        logging.basicConfig(level=level)

    def create_inputs(self) -> None:
        """
        Create and add input sources from ensemble configuration.

        Reads input_uri from each subchannel and creates appropriate
        input sources using the unified InputFactory.
        """
        from dabmux.input.factory import InputFactory

        for subchannel in self.mux.ensemble.subchannels:
            if not subchannel.input_uri:
                logger.warning(
                    "No input configured for subchannel, will use silence",
                    subchannel=subchannel.uid
                )
                continue

            uri = subchannel.input_uri

            try:
                # Validate URI first
                valid, error = InputFactory.validate_uri(uri, subchannel.type)
                if not valid:
                    logger.error(
                        "Invalid input URI",
                        subchannel=subchannel.uid,
                        uri=uri,
                        error=error
                    )
                    continue

                # Create input source using unified factory
                logger.info(
                    "Creating input source",
                    subchannel=subchannel.uid,
                    uri=uri,
                    type=subchannel.type
                )

                input_source = InputFactory.create(
                    uri=uri,
                    subchannel_type=subchannel.type,
                    bitrate=subchannel.bitrate,
                    loop=True  # Enable looping for file inputs
                )

                # Add to multiplexer
                self.mux.add_input(subchannel.uid, input_source)

                logger.info(
                    "Input source created successfully",
                    subchannel=subchannel.uid
                )

            except Exception as e:
                logger.error(
                    "Failed to create input source",
                    subchannel=subchannel.uid,
                    uri=uri,
                    error=str(e)
                )

    def configure_edi_output(self, args: argparse.Namespace, ensemble):
        """
        Configure EDI output in the ensemble based on CLI arguments.

        Args:
            args: Parsed arguments
            ensemble: Ensemble configuration

        Modifies ensemble.edi_output in place.
        """
        if not args.edi:
            return

        # Parse URL
        url = args.edi
        if not (url.startswith('udp://') or url.startswith('tcp://')):
            raise ValueError(f"Invalid EDI URL: {url} (must start with udp:// or tcp://)")

        protocol = 'udp' if url.startswith('udp://') else 'tcp'

        # Extract host and port
        url_parts = url.split('://', 1)[1]
        if ':' in url_parts:
            host, port_str = url_parts.rsplit(':', 1)
            port = int(port_str)
            destination = f"{host}:{port}"
        else:
            raise ValueError(f"Invalid EDI URL: {url} (must include port)")

        # Create EDI configuration
        ensemble.edi_output = EdiOutputConfig(
            enabled=True,
            protocol=protocol,
            destination=destination,
            tcp_mode=args.edi_tcp_mode,
            source_port=args.edi_source_port,
            enable_pft=args.pft,
            pft_fec=args.pft_fec,
            pft_fragment_size=args.pft_fragment_size,
            enable_tist=args.tist
        )

        logger.info("EDI output configured",
                   protocol=protocol,
                   destination=destination,
                   tcp_mode=args.edi_tcp_mode if protocol == 'tcp' else None,
                   pft=args.pft,
                   fec=args.pft_fec if args.pft else 0)

    def create_file_output(self, args: argparse.Namespace):
        """
        Create file output if requested.

        Args:
            args: Parsed arguments

        Returns:
            FileOutput instance or None
        """
        if not args.output:
            return None

        # File output
        output = FileOutput()
        # Set file type before opening
        format_map = {
            'raw': EtiFileType.RAW,
            'streamed': EtiFileType.STREAMED,
            'framed': EtiFileType.FRAMED
        }
        output._file_type = format_map[args.format]
        logger.info("File output configured", file=args.output, format=args.format)
        return output

    def run(self, args: list = None) -> int:
        """
        Run the multiplexer.

        Args:
            args: Command-line arguments

        Returns:
            Exit code (0 = success, non-zero = error)
        """
        try:
            # Parse arguments
            parsed_args = self.parse_args(args)

            # Setup logging
            self.setup_logging(parsed_args)

            # Load configuration
            logger.info("Loading configuration", file=parsed_args.config)
            ensemble = load_config(parsed_args.config)
            logger.info("Configuration loaded",
                       ensemble_id=f"0x{ensemble.id:04X}",
                       services=len(ensemble.services),
                       subchannels=len(ensemble.subchannels))

            # Configure EDI output from CLI arguments
            self.configure_edi_output(parsed_args, ensemble)

            # Apply TIST settings to ensemble (Priority 5.5 - Enhanced ETI)
            if parsed_args.tist:
                ensemble.enable_tist = True
                # Convert offset from milliseconds to seconds
                ensemble.tist_offset = parsed_args.tist_offset / 1000.0
                logger.info("TIST enabled", offset_ms=parsed_args.tist_offset)

            # Create multiplexer (will auto-setup EDI if configured)
            self.mux = DabMultiplexer(ensemble)

            # Create and add input sources
            self.create_inputs()

            # Setup MOT carousels (Phase 6)
            self.mux.setup_carousels()

            # Start remote control servers if requested
            if parsed_args.zmq:
                self.mux.start_zmq_server(parsed_args.zmq)

            if parsed_args.telnet:
                # Parse address:port
                if ':' in parsed_args.telnet:
                    address, port_str = parsed_args.telnet.rsplit(':', 1)
                    port = int(port_str)
                else:
                    address = parsed_args.telnet
                    port = 9001
                self.mux.start_telnet_server(address, port)

            # Create file output if requested
            file_output = self.create_file_output(parsed_args)

            # Validate that at least one output is configured
            if not file_output and not ensemble.edi_output:
                raise ValueError("No output configured (use -o for file or --edi for network)")

            # Setup signal handler for graceful shutdown
            def signal_handler(signum, frame):
                logger.info("Received interrupt signal, shutting down...")
                self.running = False

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Open file output if configured
            if file_output:
                file_output.open(parsed_args.output)

            try:
                # Determine number of frames to generate
                if parsed_args.continuous:
                    num_frames = None  # Infinite
                    logger.info("Starting continuous multiplexing (Ctrl+C to stop)")
                else:
                    num_frames = parsed_args.num_frames
                    logger.info(f"Generating {num_frames} frame(s)")

                # Generate and output frames
                frame_count = 0
                self.running = True

                while self.running:
                    # Generate frame (EDI automatically sent if configured)
                    frame = self.mux.generate_frame()

                    # Write to file output if configured
                    if file_output:
                        frame_bytes = frame.pack()
                        file_output.write(frame_bytes)

                    frame_count += 1

                    # Check if we've generated enough frames
                    if num_frames is not None and frame_count >= num_frames:
                        break

                    # Progress logging every 100 frames
                    if frame_count % 100 == 0:
                        logger.debug(f"Generated {frame_count} frames...")

                logger.info(f"Generated {frame_count} frame(s)")

            finally:
                # Close file output
                if file_output:
                    file_output.close()

                # Close EDI output (handled by multiplexer cleanup)
                if self.mux.edi_output:
                    self.mux.edi_output.close()

            return 0

        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            return 1
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return 1


def main() -> int:
    """
    Main entry point for command-line interface.

    Returns:
        Exit code
    """
    cli = DabMuxCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())
