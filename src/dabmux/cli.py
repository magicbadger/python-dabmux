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
from dabmux.output.edi import EdiOutput
from dabmux.edi.pft import PFTConfig

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
  # Multiplex from configuration file
  dabmux -c config.yaml -o output.eti

  # Output EDI over UDP
  dabmux -c config.yaml --edi udp://239.1.2.3:12000

  # Output EDI with PFT
  dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft

  # Generate frames continuously
  dabmux -c config.yaml -o output.eti --continuous

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
        output_group = parser.add_mutually_exclusive_group(required=True)
        output_group.add_argument(
            '-o', '--output',
            metavar='FILE',
            help='Output ETI file'
        )
        output_group.add_argument(
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
            '--pft',
            action='store_true',
            help='Enable PFT (Protection, Fragmentation and Transport) for EDI'
        )
        parser.add_argument(
            '--pft-fec',
            action='store_true',
            help='Enable FEC for PFT (requires --pft)'
        )
        parser.add_argument(
            '--pft-fec-m',
            type=int,
            default=2,
            metavar='M',
            help='PFT FEC: max recoverable fragments (default: 2)'
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

    def create_output(self, args: argparse.Namespace):
        """
        Create output based on arguments.

        Args:
            args: Parsed arguments

        Returns:
            Output instance (FileOutput or EdiOutput)
        """
        if args.output:
            # File output
            output = FileOutput()
            # Set file type before opening
            format_map = {
                'raw': EtiFileType.RAW,
                'streamed': EtiFileType.STREAMED,
                'framed': EtiFileType.FRAMED
            }
            output._file_type = format_map[args.format]
            logger.info("Output configured", file=args.output, format=args.format)
            return output

        elif args.edi:
            # EDI output
            # Parse URL
            url = args.edi
            if not (url.startswith('udp://') or url.startswith('tcp://')):
                raise ValueError(f"Invalid EDI URL: {url} (must start with udp:// or tcp://)")

            # Extract host and port
            url_parts = url.split('://', 1)[1]
            if ':' in url_parts:
                host, port_str = url_parts.rsplit(':', 1)
                port = int(port_str)
            else:
                raise ValueError(f"Invalid EDI URL: {url} (must include port)")

            # Create PFT config if requested
            pft_config = None
            if args.pft:
                pft_config = PFTConfig(
                    fec=args.pft_fec,
                    fec_m=args.pft_fec_m if args.pft_fec else 0,
                    max_fragment_size=args.pft_fragment_size
                )

            output = EdiOutput(
                dest_addr=host,
                dest_port=port,
                enable_pft=args.pft,
                pft_config=pft_config
            )
            logger.info("EDI output configured",
                       dest=f"{host}:{port}",
                       pft=args.pft,
                       fec=args.pft_fec if args.pft else False)
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

            # Create multiplexer
            self.mux = DabMultiplexer(ensemble)

            # Create output
            output = self.create_output(parsed_args)

            # Setup signal handler for graceful shutdown
            def signal_handler(signum, frame):
                logger.info("Received interrupt signal, shutting down...")
                self.running = False

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Open output
            if isinstance(output, FileOutput):
                output.open(parsed_args.output)
            else:
                output.open()

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
                    # Generate frame
                    frame = self.mux.generate_frame()

                    # Write to output
                    if isinstance(output, FileOutput):
                        # Serialize frame to bytes
                        frame_bytes = frame.pack()
                        output.write(frame_bytes)
                    elif isinstance(output, EdiOutput):
                        # Convert to EDI (would need EdiEncoder here)
                        # For now, just log
                        logger.warning("EDI encoding not fully integrated yet")
                        break

                    frame_count += 1

                    # Check if we've generated enough frames
                    if num_frames is not None and frame_count >= num_frames:
                        break

                logger.info(f"Generated {frame_count} frame(s)")

            finally:
                output.close()

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
