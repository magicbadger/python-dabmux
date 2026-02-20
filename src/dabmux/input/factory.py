"""
Unified input factory for all DAB stream types.

Provides centralized input creation based on subchannel type and URI scheme.
"""
import structlog
from urllib.parse import urlparse
from typing import Optional

from dabmux.input.base import InputBase
from dabmux.input.file import MPEGFileInput, RawFileInput
from dabmux.input.dabplus_input import DABPlusInput
from dabmux.input.dabplus_factory import DABPlusInputFactory
from dabmux.core.mux_elements import SubchannelType

logger = structlog.get_logger(__name__)


class InputFactory:
    """
    Unified factory for creating input sources.

    Handles all subchannel types (DAB, DAB+, data) and all URI schemes
    (file, fifo, udp, tcp, edi).

    Example:
        >>> # Create DAB+ file input
        >>> inp = InputFactory.create(
        ...     uri='file:///path/to/audio.dabp',
        ...     subchannel_type=SubchannelType.DABPlusAudio,
        ...     bitrate=48
        ... )
        >>>
        >>> # Create DAB MPEG input
        >>> inp = InputFactory.create(
        ...     uri='file:///path/to/audio.mp2',
        ...     subchannel_type=SubchannelType.DABAudio,
        ...     bitrate=96
        ... )
        >>>
        >>> # Create DAB+ UDP input
        >>> inp = InputFactory.create(
        ...     uri='udp://0.0.0.0:9000',
        ...     subchannel_type=SubchannelType.DABPlusAudio,
        ...     bitrate=48
        ... )
    """

    @staticmethod
    def create(
        uri: str,
        subchannel_type: SubchannelType,
        bitrate: int,
        **kwargs
    ) -> InputBase:
        """
        Create input source based on URI and subchannel type.

        Args:
            uri: Input URI (file://, fifo://, udp://, tcp://, edi://)
            subchannel_type: Type of subchannel (DAB, DAB+, data)
            bitrate: Stream bitrate in kbps
            **kwargs: Additional arguments passed to input constructor

        Returns:
            InputBase or DABPlusInput instance

        Raises:
            ValueError: If URI or subchannel type is invalid
            NotImplementedError: If feature is not yet implemented

        Example:
            >>> factory = InputFactory()
            >>> input_source = factory.create(
            ...     'file:///tmp/audio.dabp',
            ...     SubchannelType.DABPlusAudio,
            ...     bitrate=48
            ... )
        """
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower() if parsed.scheme else 'file'

        logger.debug(
            "Creating input source",
            uri=uri,
            scheme=scheme,
            type=subchannel_type,
            bitrate=bitrate
        )

        # DAB+ uses the specialized DABPlus input classes
        if subchannel_type == SubchannelType.DABPlusAudio:
            return InputFactory._create_dabplus_input(uri, bitrate, scheme, **kwargs)

        # DAB and data use legacy file-based inputs
        elif subchannel_type == SubchannelType.DABAudio:
            return InputFactory._create_dab_input(uri, bitrate, scheme, **kwargs)

        elif subchannel_type in [SubchannelType.Packet, SubchannelType.DataDmb]:
            return InputFactory._create_data_input(uri, bitrate, scheme, **kwargs)

        else:
            raise ValueError(f"Unsupported subchannel type: {subchannel_type}")

    @staticmethod
    def _create_dabplus_input(
        uri: str,
        bitrate: int,
        scheme: str,
        **kwargs
    ) -> DABPlusInput:
        """
        Create DAB+ input (from ODR-AudioEnc).

        Supports: file (.dabp), fifo, udp, edi

        Args:
            uri: Input URI
            bitrate: Stream bitrate in kbps
            scheme: URI scheme
            **kwargs: Additional arguments

        Returns:
            DABPlusInput instance (already opened)
        """
        # Use DABPlusInputFactory for all DAB+ inputs
        try:
            input_source = DABPlusInputFactory.create(uri, bitrate, **kwargs)

            # Open the input
            if not input_source.open():
                raise RuntimeError(f"Failed to open DAB+ input: {uri}")

            return input_source
        except Exception as e:
            logger.error(
                "Failed to create DAB+ input",
                uri=uri,
                error=str(e)
            )
            raise

    @staticmethod
    def _create_dab_input(
        uri: str,
        bitrate: int,
        scheme: str,
        **kwargs
    ) -> InputBase:
        """
        Create DAB (MPEG Layer II) input.

        Only file:// is supported for DAB audio.

        Args:
            uri: Input URI
            bitrate: Stream bitrate in kbps
            scheme: URI scheme
            **kwargs: Additional arguments

        Returns:
            MPEGFileInput instance
        """
        if scheme not in ['file', '']:
            raise NotImplementedError(
                f"DAB audio only supports file:// input. "
                f"For live streaming, use DAB+ with ODR-AudioEnc."
            )

        parsed = urlparse(uri)
        file_path = parsed.path if parsed.path else uri

        # Create MPEG input
        input_source = MPEGFileInput()
        input_source._load_entire_file = kwargs.get('loop', True)
        input_source.set_bitrate(bitrate)
        input_source.open(file_path)

        return input_source

    @staticmethod
    def _create_data_input(
        uri: str,
        bitrate: int,
        scheme: str,
        **kwargs
    ) -> InputBase:
        """
        Create data subchannel input.

        Only file:// is supported for data subchannels.

        Args:
            uri: Input URI
            bitrate: Stream bitrate in kbps
            scheme: URI scheme
            **kwargs: Additional arguments

        Returns:
            RawFileInput instance
        """
        if scheme not in ['file', '']:
            raise NotImplementedError(
                f"Data subchannels only support file:// input."
            )

        parsed = urlparse(uri)
        file_path = parsed.path if parsed.path else uri

        # Create raw input
        input_source = RawFileInput()
        input_source._load_entire_file = kwargs.get('loop', True)
        input_source.set_bitrate(bitrate)
        input_source.open(file_path)

        return input_source

    @staticmethod
    def validate_uri(
        uri: str,
        subchannel_type: SubchannelType
    ) -> tuple[bool, Optional[str]]:
        """
        Validate input URI for given subchannel type.

        Args:
            uri: Input URI to validate
            subchannel_type: Subchannel type

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            parsed = urlparse(uri)
            scheme = parsed.scheme.lower() if parsed.scheme else 'file'

            # DAB+ supports all schemes via DABPlusInputFactory
            if subchannel_type == SubchannelType.DABPlusAudio:
                return DABPlusInputFactory.validate_uri(uri)

            # DAB audio and data only support file://
            elif subchannel_type in [SubchannelType.DABAudio, SubchannelType.Packet, SubchannelType.DataDmb]:
                if scheme not in ['file', '']:
                    return False, f"Only file:// supported for {subchannel_type}"
                # Check for empty path (either no path at all, or file:// with no path)
                path = parsed.path if parsed.scheme else uri
                if not path or path == '':
                    return False, "Empty file path"
                return True, None

            else:
                return False, f"Unknown subchannel type: {subchannel_type}"

        except Exception as e:
            return False, f"Invalid URI: {str(e)}"

    @staticmethod
    def get_supported_schemes(subchannel_type: SubchannelType) -> list[str]:
        """
        Get supported URI schemes for subchannel type.

        Args:
            subchannel_type: Subchannel type

        Returns:
            List of supported scheme names
        """
        if subchannel_type == SubchannelType.DABPlusAudio:
            return DABPlusInputFactory.get_supported_schemes()
        else:
            return ['file']
