"""
Factory for creating DAB+ input sources from URIs.

Provides unified interface for creating different types of DAB+ inputs
based on URI scheme (file://, fifo://, udp://, edi://).
"""

import structlog
from urllib.parse import urlparse
from typing import Optional

from dabmux.input.dabplus_input import DABPlusInput
from dabmux.input.dabplus_file import DABPlusFileInput
from dabmux.input.dabplus_fifo import DABPlusFifoInput
from dabmux.input.dabplus_udp import DABPlusUdpInput

logger = structlog.get_logger(__name__)


class DABPlusInputFactory:
    """
    Factory for creating DAB+ input sources from URI strings.

    Supported URI formats:
    - file:///path/to/file.dabp
    - fifo:///path/to/pipe
    - udp://host:port
    - edi://host:port (future)

    Example:
        >>> factory = DABPlusInputFactory()
        >>> input_source = factory.create('file:///tmp/audio.dabp', bitrate=48)
        >>> if input_source.open():
        ...     frame = input_source.read_frame(144)
    """

    @staticmethod
    def create(input_uri: str, bitrate: int, **kwargs) -> DABPlusInput:
        """
        Create appropriate DAB+ input source from URI.

        Args:
            input_uri: Input URI (file://, fifo://, udp://, edi://)
            bitrate: Stream bitrate in kbps
            **kwargs: Additional arguments passed to input constructor

        Returns:
            DABPlusInput instance

        Raises:
            ValueError: If URI scheme is not supported

        Example:
            >>> # File input
            >>> inp = DABPlusInputFactory.create('file:///tmp/audio.dabp', 48)
            >>>
            >>> # FIFO input with custom timeout
            >>> inp = DABPlusInputFactory.create('fifo:///tmp/pipe', 48, timeout=2.0)
            >>>
            >>> # UDP input with buffer size
            >>> inp = DABPlusInputFactory.create('udp://0.0.0.0:9000', 64, buffer_frames=20)
        """
        parsed = urlparse(input_uri)
        scheme = parsed.scheme.lower() if parsed.scheme else 'file'

        logger.debug(
            "Creating DAB+ input",
            uri=input_uri,
            scheme=scheme,
            bitrate=bitrate
        )

        if scheme == 'file' or scheme == '':
            # File input - handle both file:// and plain paths
            path = parsed.path if parsed.path else input_uri

            # Get optional parameters
            loop = kwargs.get('loop', True)

            return DABPlusFileInput(
                file_path=path,
                bitrate=bitrate,
                loop=loop
            )

        elif scheme == 'fifo':
            # FIFO input
            path = parsed.path

            # Get optional parameters
            timeout = kwargs.get('timeout', 1.0)

            return DABPlusFifoInput(
                fifo_path=path,
                bitrate=bitrate,
                timeout=timeout
            )

        elif scheme == 'udp':
            # UDP input
            host = parsed.hostname or '0.0.0.0'
            port = parsed.port or 9000

            # Get optional parameters
            buffer_frames = kwargs.get('buffer_frames', 10)

            return DABPlusUdpInput(
                host=host,
                port=port,
                bitrate=bitrate,
                buffer_frames=buffer_frames
            )

        elif scheme == 'edi':
            # EDI input (future implementation)
            raise NotImplementedError(
                "EDI input not yet implemented. "
                "Use file://, fifo://, or udp:// for now."
            )

        else:
            raise ValueError(
                f"Unsupported input URI scheme: '{scheme}'. "
                f"Supported schemes: file, fifo, udp"
            )

    @staticmethod
    def validate_uri(input_uri: str) -> tuple[bool, Optional[str]]:
        """
        Validate input URI format.

        Args:
            input_uri: URI to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None

        Example:
            >>> valid, error = DABPlusInputFactory.validate_uri('file:///tmp/audio.dabp')
            >>> if valid:
            ...     print("URI is valid")
        """
        try:
            parsed = urlparse(input_uri)
            scheme = parsed.scheme.lower() if parsed.scheme else 'file'

            if scheme not in ['file', 'fifo', 'udp', 'edi', '']:
                return False, f"Unsupported scheme: '{scheme}'"

            if scheme == 'file' or scheme == '':
                # File/path - just check if path exists
                if not parsed.path and not input_uri:
                    return False, "Empty file path"

            elif scheme == 'fifo':
                # FIFO - check path exists
                if not parsed.path:
                    return False, "Missing FIFO path"

            elif scheme == 'udp':
                # UDP - check host:port format
                if not parsed.hostname:
                    return False, "Missing UDP hostname"
                if not parsed.port:
                    return False, "Missing UDP port"

            elif scheme == 'edi':
                # EDI - not yet implemented
                return False, "EDI input not yet implemented"

            return True, None

        except Exception as e:
            return False, f"Invalid URI format: {str(e)}"

    @staticmethod
    def get_supported_schemes() -> list[str]:
        """
        Get list of supported URI schemes.

        Returns:
            List of supported scheme names
        """
        return ['file', 'fifo', 'udp']
