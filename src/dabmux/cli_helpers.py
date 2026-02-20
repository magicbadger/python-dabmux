"""
CLI helper commands for ODR-AudioEnc integration and configuration validation.

Provides utility commands to help users work with the multiplexer and ODR-AudioEnc.
"""
import sys
import argparse
import structlog
from pathlib import Path
from typing import Optional

from dabmux.utils.odr_audioenc import ODRAudioEncHelper
from dabmux.config import load_config
from dabmux.input.factory import InputFactory
from dabmux.core.mux_elements import SubchannelType

logger = structlog.get_logger(__name__)


def cmd_odr_helper(args: argparse.Namespace) -> int:
    """
    Generate ODR-AudioEnc command for a service.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 = success)
    """
    helper = ODRAudioEncHelper()

    # Check if odr-audioenc is available
    available, version = helper.check_odr_audioenc()
    if not available:
        print(f"Warning: {version}", file=sys.stderr)
        print("Install from: https://github.com/Opendigitalradio/ODR-AudioEnc\n", file=sys.stderr)

    # Generate command
    if args.action == 'generate':
        cmd = helper.generate_command(
            input_file=args.input,
            output=args.output,
            bitrate=args.bitrate,
            sample_rate=args.sample_rate,
            channels=1 if args.mono else 2,
            afterburner=args.afterburner,
            pad=args.pad,
            dls_file=args.dls
        )
        print("Generated command:")
        print(cmd)
        print()
        print("Run this command to encode your audio:")
        print(f"  {cmd}")

    elif args.action == 'examples':
        print("ODR-AudioEnc Usage Examples\n")
        print("=" * 70)
        examples = helper.get_usage_examples()
        for i, (description, command) in enumerate(examples, 1):
            print(f"\n{i}. {description}")
            print(f"   {command}")
        print()

    elif args.action == 'capacity':
        info = helper.calculate_capacity(args.bitrate, args.pad or 0)
        print(f"Capacity Analysis for {args.bitrate} kbps")
        print("=" * 70)
        print(f"Total bitrate:            {info['total_bitrate_kbps']:.1f} kbps")
        print(f"PAD length:               {info['pad_length_bytes']} bytes")
        print(f"AU size (before FEC):     {info['au_size_bytes']} bytes")
        print(f"Audio capacity:           {info['audio_size_bytes']} bytes per AU")
        print(f"Audio bitrate:            {info['audio_capacity_kbps']:.1f} kbps")
        print(f"Protected AU size:        {info['protected_au_size_bytes']} bytes")
        print(f"Superframe size:          {info['superframe_size_bytes']} bytes")
        print()
        if args.pad:
            print(f"Note: PAD overhead is {args.pad} bytes, reducing audio capacity")

    elif args.action == 'recommend':
        bitrate = helper.recommend_bitrate(args.content_type)
        print(f"Recommended bitrate for '{args.content_type}': {bitrate} kbps")
        print()
        print("Content type recommendations:")
        for content, rate in helper.RECOMMENDED_BITRATES.items():
            marker = " <--" if content == args.content_type else ""
            print(f"  {content:20s}: {rate:3d} kbps{marker}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """
    Validate configuration file.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 = valid, 1 = invalid)
    """
    print(f"Validating configuration: {args.config}")
    print("=" * 70)

    try:
        # Load configuration
        config = load_config(args.config)

        # Basic validation
        print("\n✓ Configuration file syntax is valid")

        # Ensemble validation
        print(f"\nEnsemble:")
        print(f"  ID:    0x{config.id:04X}")
        print(f"  Label: {config.label}")
        print(f"  ECC:   0x{config.ecc:02X}")

        # Services validation
        print(f"\nServices: {len(config.services)}")
        total_bitrate = 0
        for service in config.services:
            print(f"  - {service.label} (SID: 0x{service.sid:04X})")
            print(f"    Bitrate: {service.bitrate} kbps")
            print(f"    Type: {service.type}")
            total_bitrate += service.bitrate

        # Subchannels validation
        print(f"\nSubchannels: {len(config.subchannels)}")
        errors = []
        warnings = []

        for subchannel in config.subchannels:
            print(f"  - {subchannel.uid}")
            print(f"    Bitrate: {subchannel.bitrate} kbps")
            print(f"    Protection: {subchannel.protection}")

            # Validate input URI
            if subchannel.input_uri:
                print(f"    Input: {subchannel.input_uri}")

                # Validate URI
                valid, error = InputFactory.validate_uri(
                    subchannel.input_uri,
                    subchannel.type
                )

                if not valid:
                    errors.append(f"Subchannel '{subchannel.uid}': {error}")
                    print(f"    ✗ Invalid input URI: {error}")
                else:
                    print(f"    ✓ Input URI valid")

                # Check if file exists (for file:// URIs)
                if subchannel.input_uri.startswith('file://') or '://' not in subchannel.input_uri:
                    file_path = subchannel.input_uri.replace('file://', '')
                    if not Path(file_path).exists():
                        warnings.append(f"Subchannel '{subchannel.uid}': Input file not found: {file_path}")
                        print(f"    ⚠ Warning: Input file not found")
            else:
                warnings.append(f"Subchannel '{subchannel.uid}': No input configured (will use silence)")
                print(f"    ⚠ Warning: No input configured")

        # Capacity check
        print(f"\nTotal bitrate: {total_bitrate} kbps")
        if total_bitrate > 1200:
            warnings.append(f"Total bitrate ({total_bitrate} kbps) exceeds typical DAB Mode I capacity (1200 kbps)")
            print(f"  ⚠ Warning: May exceed capacity")
        else:
            remaining = 1200 - total_bitrate
            print(f"  Remaining capacity: {remaining} kbps")

        # Summary
        print("\n" + "=" * 70)
        if errors:
            print(f"\n✗ Validation FAILED with {len(errors)} error(s):")
            for error in errors:
                print(f"  - {error}")
            return 1
        elif warnings:
            print(f"\n⚠ Validation passed with {len(warnings)} warning(s):")
            for warning in warnings:
                print(f"  - {warning}")
            return 0
        else:
            print("\n✓ Validation PASSED - configuration is valid")
            return 0

    except Exception as e:
        print(f"\n✗ Validation FAILED: {str(e)}", file=sys.stderr)
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """
    Show system information and capabilities.

    Args:
        args: Command-line arguments

    Returns:
        Exit code (0 = success)
    """
    print("python-dabmux Information")
    print("=" * 70)

    # Version info
    try:
        from dabmux import __version__
        print(f"\nVersion: {__version__}")
    except:
        print("\nVersion: Development")

    # Supported features
    print("\nSupported Features:")
    print("  ✓ DAB (MPEG Layer II)")
    print("  ✓ DAB+ (HE-AAC v2)")
    print("  ✓ Multiple services")
    print("  ✓ FIC encoding (FIG 0/1, 0/2, etc.)")
    print("  ✓ PAD/DLS support")
    print("  ✓ ETI output (raw, framed, streamed)")
    print("  ✓ File input (.dabp, .mp2)")
    print("  ✓ FIFO input (named pipes)")
    print("  ✓ UDP input (network streaming)")

    # Input types
    print("\nSupported Input Types:")
    print("  DAB+:  file://, fifo://, udp://")
    print("  DAB:   file://")
    print("  Data:  file://")

    # ODR-AudioEnc check
    print("\nODR-AudioEnc:")
    helper = ODRAudioEncHelper()
    available, version = helper.check_odr_audioenc()
    if available:
        print(f"  ✓ {version}")
    else:
        print(f"  ✗ Not found: {version}")
        print("    Install from: https://github.com/Opendigitalradio/ODR-AudioEnc")

    # Bitrate recommendations
    if args.verbose:
        print("\nBitrate Recommendations:")
        for content, bitrate in helper.RECOMMENDED_BITRATES.items():
            print(f"  {content:20s}: {bitrate:3d} kbps")

    # Examples location
    print("\nExample Configurations:")
    print("  examples/01_simple_single_service.yaml")
    print("  examples/02_multi_service.yaml")
    print("  examples/03_live_streaming_udp.yaml")
    print("  examples/04_live_streaming_fifo.yaml")

    print()
    return 0


def setup_cli_helpers() -> argparse.ArgumentParser:
    """
    Setup argument parser for CLI helpers.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description='python-dabmux Helper Utilities',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # ODR-AudioEnc helper
    odr_parser = subparsers.add_parser('odr', help='ODR-AudioEnc helper')
    odr_subparsers = odr_parser.add_subparsers(dest='action', help='Actions')

    # Generate command
    gen_parser = odr_subparsers.add_parser('generate', help='Generate odr-audioenc command')
    gen_parser.add_argument('-i', '--input', required=True, help='Input audio file')
    gen_parser.add_argument('-o', '--output', required=True, help='Output .dabp file or URI')
    gen_parser.add_argument('-b', '--bitrate', type=int, required=True, help='Bitrate in kbps')
    gen_parser.add_argument('-r', '--sample-rate', type=int, default=48000, help='Sample rate (default: 48000)')
    gen_parser.add_argument('--mono', action='store_true', help='Mono audio')
    gen_parser.add_argument('--no-afterburner', dest='afterburner', action='store_false', help='Disable afterburner')
    gen_parser.add_argument('--pad', type=int, help='PAD length in bytes')
    gen_parser.add_argument('--dls', help='DLS text file')

    # Examples
    odr_subparsers.add_parser('examples', help='Show usage examples')

    # Capacity calculator
    cap_parser = odr_subparsers.add_parser('capacity', help='Calculate capacity')
    cap_parser.add_argument('-b', '--bitrate', type=int, required=True, help='Bitrate in kbps')
    cap_parser.add_argument('--pad', type=int, help='PAD length in bytes')

    # Recommendations
    rec_parser = odr_subparsers.add_parser('recommend', help='Get bitrate recommendation')
    rec_parser.add_argument('content_type', choices=list(ODRAudioEncHelper.RECOMMENDED_BITRATES.keys()),
                           help='Content type')

    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate configuration file')
    val_parser.add_argument('config', help='Configuration file to validate')

    # Info command
    info_parser = subparsers.add_parser('info', help='Show system information')
    info_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    return parser


def main_helpers():
    """Main entry point for CLI helpers."""
    parser = setup_cli_helpers()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate handler
    if args.command == 'odr':
        if not args.action:
            parser.print_help()
            return 1
        return cmd_odr_helper(args)
    elif args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'info':
        return cmd_info(args)

    return 0


if __name__ == '__main__':
    sys.exit(main_helpers())
