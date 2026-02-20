"""
Helper utilities for working with ODR-AudioEnc.

Provides functions to generate odr-audioenc command lines, validate
configurations, and integrate with the multiplexer.
"""
import structlog
from typing import Optional, List
from pathlib import Path

logger = structlog.get_logger(__name__)


class ODRAudioEncHelper:
    """
    Helper for generating ODR-AudioEnc commands.

    ODR-AudioEnc is the reference DAB+ encoder that produces .dabp files
    for use with python-dabmux.

    Example:
        >>> helper = ODRAudioEncHelper()
        >>> cmd = helper.generate_command(
        ...     input_file='music.wav',
        ...     output='music.dabp',
        ...     bitrate=48
        ... )
        >>> print(cmd)
        odr-audioenc -i music.wav -o music.dabp -b 48 --aaclc -r 48000
    """

    # Supported bitrates for DAB+ (in kbps)
    SUPPORTED_BITRATES = [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 96, 112, 128, 144, 160, 192]

    # Recommended bitrates for different content types
    RECOMMENDED_BITRATES = {
        'speech': 24,       # Talk radio, podcasts
        'talk': 32,         # Talk with some music
        'music_low': 48,    # Music (acceptable quality)
        'music_standard': 64,  # Music (good quality)
        'music_high': 80,   # Music (very good quality)
        'music_premium': 96,   # Music (premium quality)
    }

    @staticmethod
    def validate_bitrate(bitrate: int) -> tuple[bool, Optional[str]]:
        """
        Validate bitrate value.

        Args:
            bitrate: Bitrate in kbps

        Returns:
            Tuple of (is_valid, error_message)
        """
        if bitrate not in ODRAudioEncHelper.SUPPORTED_BITRATES:
            nearest = min(
                ODRAudioEncHelper.SUPPORTED_BITRATES,
                key=lambda x: abs(x - bitrate)
            )
            return False, f"Bitrate {bitrate} kbps not supported. Nearest: {nearest} kbps"
        return True, None

    @staticmethod
    def recommend_bitrate(content_type: str = 'music_standard') -> int:
        """
        Get recommended bitrate for content type.

        Args:
            content_type: Type of content (speech, talk, music_low, music_standard,
                         music_high, music_premium)

        Returns:
            Recommended bitrate in kbps
        """
        return ODRAudioEncHelper.RECOMMENDED_BITRATES.get(
            content_type,
            ODRAudioEncHelper.RECOMMENDED_BITRATES['music_standard']
        )

    @staticmethod
    def generate_command(
        input_file: str,
        output: str,
        bitrate: int,
        sample_rate: int = 48000,
        channels: int = 2,
        afterburner: bool = True,
        pad: Optional[int] = None,
        dls_file: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> str:
        """
        Generate odr-audioenc command line.

        Args:
            input_file: Input audio file (WAV, MP3, etc.)
            output: Output .dabp file path (or udp:// URI)
            bitrate: Bitrate in kbps
            sample_rate: Sample rate in Hz (default: 48000)
            channels: Number of channels (1=mono, 2=stereo)
            afterburner: Enable AAC afterburner (better quality, slower)
            pad: PAD length in bytes (e.g., 58 for DLS)
            dls_file: Path to DLS text file
            extra_args: Additional command line arguments

        Returns:
            Complete command line string

        Example:
            >>> helper = ODRAudioEncHelper()
            >>> cmd = helper.generate_command(
            ...     input_file='music.wav',
            ...     output='music.dabp',
            ...     bitrate=48,
            ...     pad=58,
            ...     dls_file='nowplaying.txt'
            ... )
        """
        # Validate bitrate
        valid, error = ODRAudioEncHelper.validate_bitrate(bitrate)
        if not valid:
            logger.warning("Invalid bitrate", bitrate=bitrate, error=error)

        # Build command
        cmd_parts = ['odr-audioenc']

        # Input
        cmd_parts.extend(['-i', input_file])

        # Output
        cmd_parts.extend(['-o', output])

        # Bitrate
        cmd_parts.extend(['-b', str(bitrate)])

        # Profile (always use AAC-LC for DAB+)
        cmd_parts.append('--aaclc')

        # Sample rate
        cmd_parts.extend(['-r', str(sample_rate)])

        # Channels
        if channels == 1:
            cmd_parts.append('--mono')
        # stereo is default, no flag needed

        # Afterburner
        if afterburner:
            cmd_parts.append('--afterburner')

        # PAD
        if pad is not None:
            cmd_parts.extend(['--pad', str(pad)])

        # DLS
        if dls_file is not None:
            cmd_parts.extend(['--dls', dls_file])

        # Extra arguments
        if extra_args:
            cmd_parts.extend(extra_args)

        return ' '.join(cmd_parts)

    @staticmethod
    def generate_fifo_command(
        input_file: str,
        fifo_path: str,
        bitrate: int,
        **kwargs
    ) -> str:
        """
        Generate command for live streaming via FIFO.

        Args:
            input_file: Input audio file (or device)
            fifo_path: Path to FIFO
            bitrate: Bitrate in kbps
            **kwargs: Additional arguments for generate_command()

        Returns:
            Command line string

        Example:
            >>> helper = ODRAudioEncHelper()
            >>> cmd = helper.generate_fifo_command(
            ...     input_file='/dev/audio',
            ...     fifo_path='/tmp/audio.fifo',
            ...     bitrate=48
            ... )
        """
        return ODRAudioEncHelper.generate_command(
            input_file=input_file,
            output=fifo_path,
            bitrate=bitrate,
            **kwargs
        )

    @staticmethod
    def generate_udp_command(
        input_file: str,
        host: str,
        port: int,
        bitrate: int,
        **kwargs
    ) -> str:
        """
        Generate command for network streaming via UDP.

        Args:
            input_file: Input audio file
            host: Destination host
            port: Destination port
            bitrate: Bitrate in kbps
            **kwargs: Additional arguments for generate_command()

        Returns:
            Command line string

        Example:
            >>> helper = ODRAudioEncHelper()
            >>> cmd = helper.generate_udp_command(
            ...     input_file='music.wav',
            ...     host='localhost',
            ...     port=9000,
            ...     bitrate=48
            ... )
        """
        output_uri = f'udp://{host}:{port}'
        return ODRAudioEncHelper.generate_command(
            input_file=input_file,
            output=output_uri,
            bitrate=bitrate,
            **kwargs
        )

    @staticmethod
    def calculate_capacity(bitrate: int, pad_length: int = 0) -> dict:
        """
        Calculate audio capacity after PAD overhead.

        Args:
            bitrate: Total bitrate in kbps
            pad_length: PAD length in bytes (default: 0)

        Returns:
            Dictionary with capacity information

        Example:
            >>> helper = ODRAudioEncHelper()
            >>> info = helper.calculate_capacity(48, pad_length=58)
            >>> print(f"Audio capacity: {info['audio_capacity_kbps']} kbps")
        """
        # Superframe structure
        subchannel_index = bitrate // 8
        superframe_size = subchannel_index * 110  # bytes before FEC
        au_size = superframe_size // 5  # 5 AUs per superframe

        # PAD overhead
        audio_size = au_size - pad_length
        audio_capacity_kbps = (audio_size * 8 * 5) / 120  # 5 AUs per 120ms

        # Protected size (after RS encoding)
        protected_au_size = subchannel_index * 24  # bytes after FEC

        return {
            'total_bitrate_kbps': bitrate,
            'pad_length_bytes': pad_length,
            'au_size_bytes': au_size,
            'audio_size_bytes': audio_size,
            'audio_capacity_kbps': audio_capacity_kbps,
            'protected_au_size_bytes': protected_au_size,
            'superframe_size_bytes': superframe_size,
        }

    @staticmethod
    def get_usage_examples() -> List[tuple[str, str]]:
        """
        Get usage examples for common scenarios.

        Returns:
            List of (description, command) tuples
        """
        return [
            (
                "Simple music encoding (48 kbps)",
                "odr-audioenc -i music.wav -o music.dabp -b 48 --aaclc -r 48000 --afterburner"
            ),
            (
                "Talk radio (24 kbps, mono)",
                "odr-audioenc -i talk.wav -o talk.dabp -b 24 --aaclc -r 48000 --mono"
            ),
            (
                "Music with DLS (48 kbps + 58 bytes PAD)",
                "odr-audioenc -i music.wav -o music.dabp -b 48 --aaclc -r 48000 --pad 58 --dls nowplaying.txt"
            ),
            (
                "Live streaming via UDP",
                "odr-audioenc -i /dev/audio -o udp://localhost:9000 -b 48 --aaclc -r 48000"
            ),
            (
                "Live streaming via FIFO",
                "odr-audioenc -i /dev/audio -o /tmp/audio.fifo -b 48 --aaclc -r 48000"
            ),
        ]

    @staticmethod
    def check_odr_audioenc() -> tuple[bool, Optional[str]]:
        """
        Check if odr-audioenc is installed and accessible.

        Returns:
            Tuple of (is_available, version_or_error)
        """
        import subprocess

        try:
            result = subprocess.run(
                ['odr-audioenc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output
                version = result.stdout.strip().split('\n')[0]
                return True, version
            else:
                return False, "odr-audioenc found but failed to run"
        except FileNotFoundError:
            return False, "odr-audioenc not found in PATH"
        except subprocess.TimeoutExpired:
            return False, "odr-audioenc command timed out"
        except Exception as e:
            return False, f"Error checking odr-audioenc: {str(e)}"
