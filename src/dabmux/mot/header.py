"""
MOT Header encoding per ETSI TS 101 499 Section 6.

The MOT header contains metadata about the object being transmitted,
including content type, size, name, and optional parameters.
"""

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import IntEnum
import structlog

logger = structlog.get_logger(__name__)


class MotContentType(IntEnum):
    """MOT Content Types per TS 101 499 Table 6."""
    # General
    GENERAL_DATA = 0x00
    TEXT = 0x01
    HTML = 0x02

    # Images
    IMAGE_GIF = 0x03
    IMAGE_JFIF = 0x04  # JPEG
    IMAGE_BMP = 0x05
    IMAGE_PNG = 0x06

    # Audio/Video
    MPEG_AUDIO = 0x07
    MPEG_VIDEO = 0x08

    # EPG (ETSI TS 102 371)
    EPG_SI = 0x11  # Service Information
    EPG_PI = 0x12  # Programme Information
    EPG_GI = 0x13  # Group Information

    # Application-specific
    MOT_TRANSPORT = 0x60

    # Proprietary
    PROPRIETARY = 0x1F


class MotParameterType(IntEnum):
    """MOT Parameter IDs per TS 101 499 Table 8."""
    # Core parameters
    CONTENT_NAME = 0x0C

    # Slideshow parameters
    CATEGORY_ID = 0x25
    SLIDE_ID = 0x26
    CATEGORY_TITLE = 0x27
    CLICK_THROUGH_URL = 0x28
    ALTERNATE_LOCATION_URL = 0x29
    ALERT_URL = 0x2A

    # Timing parameters
    EXPIRATION_TIME = 0x04
    TRIGGER_TIME = 0x05

    # EPG parameters
    EPG_PROFILE = 0x30
    EPG_VERSION = 0x31


@dataclass
class MotParameter:
    """
    MOT Parameter (TLV structure).

    Per TS 101 499 Section 6.1, parameters are encoded as:
    - Parameter ID (6 bits)
    - Data field indicator (1 bit)
    - Extension flag (1 bit)
    - Length (variable)
    - Data (variable)
    """
    param_id: int
    data: bytes

    def encode(self) -> bytes:
        """
        Encode parameter to bytes.

        Returns:
            Encoded parameter bytes
        """
        # Parameter header
        # Bit 7-2: Parameter ID (6 bits)
        # Bit 1: DataFieldIndicator (0=data follows, 1=length follows)
        # Bit 0: Extension flag (0=last, 1=more params)

        data_len = len(self.data)

        # For now, always use DataFieldIndicator=0 (data length indicator follows)
        # Extension flag set to 0 (will be set by encoder)
        header_byte = (self.param_id & 0x3F) << 2

        # Encode length
        if data_len < 128:
            # Short form: 1 byte (bit 7=0, bits 6-0=length)
            length_bytes = bytes([data_len & 0x7F])
        else:
            # Long form: 2 bytes (bit 7=1 in first byte, 15-bit length)
            length_bytes = bytes([
                0x80 | ((data_len >> 8) & 0x7F),
                data_len & 0xFF
            ])

        return bytes([header_byte]) + length_bytes + self.data

    def set_extension_flag(self) -> None:
        """Mark this parameter as not the last (has more following)."""
        # Will be handled during encoding in MotHeader


@dataclass
class MotHeader:
    """
    MOT Header per ETSI TS 101 499 Section 6.

    The header contains:
    - Header size (13 bits)
    - Body size (28 bits)
    - Content type and subtype
    - Parameters (content name, category, etc.)
    """
    body_size: int
    content_type: MotContentType
    content_subtype: int = 0x00
    parameters: List[MotParameter] = field(default_factory=list)

    def __post_init__(self):
        """Validate header fields."""
        if self.body_size < 0 or self.body_size > (1 << 28) - 1:
            raise ValueError(f"Body size {self.body_size} out of range (0 to {(1<<28)-1})")

    def add_parameter(self, param_id: int, data: bytes) -> None:
        """
        Add a parameter to the header.

        Args:
            param_id: Parameter ID (MotParameterType)
            data: Parameter data bytes
        """
        self.parameters.append(MotParameter(param_id=param_id, data=data))

    def set_content_name(self, name: str) -> None:
        """
        Set content name parameter.

        Args:
            name: Content name (filename)
        """
        # Encode as UTF-8
        name_bytes = name.encode('utf-8')
        self.add_parameter(MotParameterType.CONTENT_NAME, name_bytes)

    def set_category_id(self, category: int) -> None:
        """
        Set CategoryID parameter for slideshow.

        Args:
            category: Category ID (0x01=album art, 0x02=logo, etc.)
        """
        self.add_parameter(MotParameterType.CATEGORY_ID, bytes([category]))

    def set_slide_id(self, slide_id: int) -> None:
        """
        Set SlideID parameter.

        Args:
            slide_id: Slide identifier
        """
        self.add_parameter(MotParameterType.SLIDE_ID, bytes([slide_id]))

    def set_click_through_url(self, url: str) -> None:
        """
        Set ClickThroughURL parameter.

        Args:
            url: URL to open when image clicked
        """
        url_bytes = url.encode('utf-8')
        self.add_parameter(MotParameterType.CLICK_THROUGH_URL, url_bytes)

    def set_trigger_time(self, trigger_time: int) -> None:
        """
        Set TriggerTime parameter (when to display image).

        Args:
            trigger_time: Trigger time in seconds (0=now)
        """
        # Encode as 32-bit unsigned
        trigger_bytes = struct.pack('>I', trigger_time)
        self.add_parameter(MotParameterType.TRIGGER_TIME, trigger_bytes)

    def encode(self) -> bytes:
        """
        Encode MOT header to bytes.

        Header structure per TS 101 499 Section 6.1:
        - Header size (13 bits)
        - Body size (28 bits)
        - Content type (6 bits)
        - Content subtype (9 bits)
        - Parameters (variable)

        Returns:
            Encoded header bytes
        """
        # Encode core header (without parameters)
        core_header = self._encode_core_header()

        # Encode parameters
        param_data = self._encode_parameters()

        # Calculate total header size (in bytes)
        # Header size includes: size field (2 bytes) + body size (4 bytes MSB)
        # + content type fields + parameters
        header_size = 7 + len(param_data)  # 7 bytes for fixed fields

        if header_size > 8191:  # 13-bit max
            raise ValueError(f"Header size {header_size} exceeds maximum 8191 bytes")

        # Rebuild core header with correct size
        full_header = self._encode_core_header_with_size(header_size)

        return full_header + param_data

    def _encode_core_header(self) -> bytes:
        """Encode core header fields (temporary, size will be recalculated)."""
        return self._encode_core_header_with_size(0)

    def _encode_core_header_with_size(self, header_size: int) -> bytes:
        """
        Encode core header with specified size.

        Args:
            header_size: Header size in bytes

        Returns:
            Encoded core header (7 bytes)
        """
        # Bytes 0-1: Header size (13 bits) + Body size MSB (3 bits)
        # Byte 2-4: Body size (remaining 25 bits)
        # Byte 5: Content type (6 bits) + Content subtype MSB (2 bits)
        # Byte 6: Content subtype (remaining 7 bits) + Extension flag (1 bit)

        header_and_body = (header_size << 28) | (self.body_size & 0x0FFFFFFF)

        # Pack as 5 bytes (41 bits)
        byte0 = (header_and_body >> 33) & 0xFF
        byte1 = (header_and_body >> 25) & 0xFF
        byte2 = (header_and_body >> 17) & 0xFF
        byte3 = (header_and_body >> 9) & 0xFF
        byte4 = (header_and_body >> 1) & 0xFF

        # Content type (6 bits) + content subtype MSB (2 bits)
        byte5 = ((self.content_type & 0x3F) << 2) | ((self.content_subtype >> 7) & 0x03)

        # Content subtype (7 bits) + extension flag (1 bit)
        # Extension flag = 1 if parameters present
        extension_flag = 1 if self.parameters else 0
        byte6 = ((self.content_subtype & 0x7F) << 1) | extension_flag

        return bytes([byte0, byte1, byte2, byte3, byte4, byte5, byte6])

    def _encode_parameters(self) -> bytes:
        """
        Encode all parameters.

        Returns:
            Encoded parameter bytes
        """
        if not self.parameters:
            return b''

        result = b''

        for i, param in enumerate(self.parameters):
            param_bytes = param.encode()

            # Set extension flag for all but last parameter
            if i < len(self.parameters) - 1:
                # Modify first byte to set extension flag (bit 0)
                param_bytes = bytes([param_bytes[0] | 0x01]) + param_bytes[1:]

            result += param_bytes

        return result

    @classmethod
    def decode(cls, data: bytes) -> 'MotHeader':
        """
        Decode MOT header from bytes.

        Args:
            data: Encoded header bytes

        Returns:
            Decoded MotHeader
        """
        if len(data) < 7:
            raise ValueError(f"Header too short: {len(data)} bytes (minimum 7)")

        # Decode header size and body size (5 bytes)
        value = (data[0] << 33) | (data[1] << 25) | (data[2] << 17) | (data[3] << 9) | (data[4] << 1)
        header_size = (value >> 28) & 0x1FFF  # 13 bits
        body_size = value & 0x0FFFFFFF  # 28 bits

        # Decode content type and subtype
        content_type = (data[5] >> 2) & 0x3F  # 6 bits
        content_subtype = ((data[5] & 0x03) << 7) | ((data[6] >> 1) & 0x7F)  # 9 bits
        extension_flag = data[6] & 0x01

        # Decode parameters if present
        parameters = []
        if extension_flag:
            offset = 7
            while offset < len(data):
                param, consumed = cls._decode_parameter(data[offset:])
                parameters.append(param)
                offset += consumed

                # Check if more parameters follow
                if not (data[offset - consumed] & 0x01):
                    break  # No extension flag, this was last parameter

        return cls(
            body_size=body_size,
            content_type=MotContentType(content_type),
            content_subtype=content_subtype,
            parameters=parameters
        )

    @staticmethod
    def _decode_parameter(data: bytes) -> tuple[MotParameter, int]:
        """
        Decode a single parameter.

        Args:
            data: Parameter data starting at first byte

        Returns:
            Tuple of (MotParameter, bytes_consumed)
        """
        if len(data) < 2:
            raise ValueError("Parameter data too short")

        # First byte: param_id (6 bits) + DFI (1 bit) + Ext (1 bit)
        param_id = (data[0] >> 2) & 0x3F

        # Decode length
        if data[1] & 0x80:
            # Long form (2 bytes)
            if len(data) < 3:
                raise ValueError("Parameter length field truncated")
            length = ((data[1] & 0x7F) << 8) | data[2]
            offset = 3
        else:
            # Short form (1 byte)
            length = data[1] & 0x7F
            offset = 2

        # Extract data
        if len(data) < offset + length:
            raise ValueError(f"Parameter data truncated: need {offset + length}, have {len(data)}")

        param_data = data[offset:offset + length]

        return MotParameter(param_id=param_id, data=param_data), offset + length
