#!/usr/bin/env python3
"""
Simple DAB Multiplexer - Loop Audio File

Creates a DAB ensemble with a single looping audio service.

Usage:
    python simple_loop.py input.mp3
    python simple_loop.py input.mp3 --output stream.eti
    python simple_loop.py input.mp3 --station-name "My Radio"
    python simple_loop.py input.mp3 --edi udp://192.168.1.100:12000
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def encode_audio(input_file: Path, output_file: Path, bitrate: int = 128) -> bool:
    """
    Encode audio file to MPEG Layer II format.

    Args:
        input_file: Input audio file (any format)
        output_file: Output .mp2 file
        bitrate: Bitrate in kbps (default: 128)

    Returns:
        True if successful, False otherwise
    """
    print(f"Encoding {input_file.name} to MPEG Layer II at {bitrate} kbps...")

    cmd = [
        'ffmpeg',
        '-i', str(input_file),
        '-c:a', 'mp2',
        '-ar', '48000',
        '-b:a', f'{bitrate}k',
        '-y',  # Overwrite output
        str(output_file)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print(f"Error encoding audio: {result.stderr}")
            return False

        print(f"✓ Audio encoded successfully: {output_file}")
        return True

    except Exception as e:
        print(f"Error running ffmpeg: {e}")
        return False


def create_config(
    audio_file: Path,
    station_name: str = "My Station",
    ensemble_name: str = "My DAB",
    bitrate: int = 128
) -> dict:
    """
    Create DAB multiplexer configuration.

    Args:
        audio_file: Path to audio file
        station_name: Station name (max 16 chars)
        ensemble_name: Ensemble name (max 16 chars)
        bitrate: Audio bitrate in kbps

    Returns:
        Configuration dictionary
    """
    # Truncate names if too long
    station_name = station_name[:16]
    ensemble_name = ensemble_name[:16]

    config = {
        'ensemble': {
            'id': '0xCE15',
            'ecc': '0xE1',
            'transmission_mode': 'I',
            'label': {
                'text': ensemble_name,
                'short': ensemble_name[:8]
            },
            'lto_auto': True
        },
        'subchannels': [
            {
                'uid': 'audio1',
                'id': 0,
                'type': 'audio',
                'bitrate': bitrate,
                'start_address': 0,
                'protection': {
                    'level': 2,
                    'shortform': True
                },
                'input': f'file://{audio_file.absolute()}'
            }
        ],
        'services': [
            {
                'uid': 'service1',
                'id': '0x5001',
                'label': {
                    'text': station_name,
                    'short': station_name[:8]
                },
                'pty': 10,  # Pop Music
                'language': 9  # English
            }
        ],
        'components': [
            {
                'uid': 'comp1',
                'service_id': '0x5001',
                'subchannel_id': 0,
                'type': 0
            }
        ]
    }

    return config


def run_multiplexer(config_file: Path, output_eti: Path = None, edi_url: str = None, format: str = 'raw'):
    """
    Run the DAB multiplexer.

    Args:
        config_file: Path to configuration YAML file
        output_eti: Output ETI file path (optional)
        edi_url: EDI output URL (optional)
        format: ETI file format - 'raw', 'framed', or 'streamed' (default: raw)
    """
    cmd = [
        sys.executable, '-m', 'dabmux.cli',
        '-c', str(config_file),
        '--continuous'
    ]

    if output_eti:
        cmd.extend(['-o', str(output_eti)])

    if edi_url:
        cmd.extend(['--edi', edi_url])

    if not output_eti and not edi_url:
        # Default to output.eti if nothing specified
        cmd.extend(['-o', 'output.eti'])

    # Add format flag (raw is compatible with etisnoop/dablin)
    if output_eti or (not output_eti and not edi_url):
        cmd.extend(['-f', format])

    print(f"\n{'='*60}")
    print("Starting DAB Multiplexer")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    print("Press Ctrl+C to stop\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\nError running multiplexer: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Simple DAB Multiplexer - Loop an audio file as a DAB service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (creates output.eti)
  python simple_loop.py music.mp3

  # Custom output file
  python simple_loop.py music.mp3 --output mystream.eti

  # Custom station name
  python simple_loop.py music.mp3 --station-name "Rock FM"

  # Stream to network modulator
  python simple_loop.py music.mp3 --edi udp://192.168.1.100:12000

  # Everything custom
  python simple_loop.py music.mp3 \\
    --station-name "My Radio" \\
    --ensemble-name "My DAB" \\
    --bitrate 160 \\
    --output stream.eti

  # Use framed format (for internal use)
  python simple_loop.py music.mp3 --format framed
        """
    )

    parser.add_argument(
        'input',
        type=Path,
        help='Input audio file (mp3, wav, flac, etc.)'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output ETI file (default: output.eti)'
    )

    parser.add_argument(
        '--edi',
        type=str,
        help='EDI output URL (udp://host:port or tcp://host:port)'
    )

    parser.add_argument(
        '-s', '--station-name',
        type=str,
        default='My Station',
        help='Station name (max 16 characters, default: My Station)'
    )

    parser.add_argument(
        '-e', '--ensemble-name',
        type=str,
        default='My DAB',
        help='Ensemble name (max 16 characters, default: My DAB)'
    )

    parser.add_argument(
        '-b', '--bitrate',
        type=int,
        default=128,
        choices=[64, 96, 128, 160, 192],
        help='Audio bitrate in kbps (default: 128)'
    )

    parser.add_argument(
        '--keep-encoded',
        action='store_true',
        help='Keep encoded .mp2 file after exit'
    )

    parser.add_argument(
        '-f', '--format',
        type=str,
        default='raw',
        choices=['raw', 'framed', 'streamed'],
        help='ETI file format (default: raw, compatible with etisnoop/dablin)'
    )

    args = parser.parse_args()

    # Check input file exists
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Check ffmpeg
    if not check_ffmpeg():
        print("Error: ffmpeg not found. Please install ffmpeg:")
        print("  macOS:   brew install ffmpeg")
        print("  Linux:   sudo apt install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/")
        sys.exit(1)

    # Create temporary directory for encoded audio and config
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Encode audio to MPEG Layer II
        encoded_audio = tmpdir / 'audio.mp2'
        if args.keep_encoded:
            encoded_audio = Path('audio_encoded.mp2')

        if not encode_audio(args.input, encoded_audio, args.bitrate):
            sys.exit(1)

        # Create configuration
        print(f"\nCreating configuration...")
        config = create_config(
            encoded_audio,
            args.station_name,
            args.ensemble_name,
            args.bitrate
        )

        config_file = tmpdir / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"✓ Configuration created: {config_file}")

        # Display configuration summary
        print(f"\n{'='*60}")
        print("Configuration Summary")
        print(f"{'='*60}")
        print(f"Input file:      {args.input.name}")
        print(f"Ensemble:        {args.ensemble_name}")
        print(f"Station:         {args.station_name}")
        print(f"Bitrate:         {args.bitrate} kbps")
        if args.output:
            print(f"Output ETI:      {args.output}")
        if args.edi:
            print(f"EDI streaming:   {args.edi}")
        print(f"Format:          {args.format}")
        print(f"{'='*60}\n")

        # Run multiplexer
        run_multiplexer(config_file, args.output, args.edi, args.format)

        if args.keep_encoded:
            print(f"\n✓ Encoded audio saved: {encoded_audio}")


if __name__ == '__main__':
    main()
