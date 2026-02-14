"""
File-based output implementations.

This module provides output classes for writing ETI frames to files
in various formats (raw, framed, streamed).
"""
import struct
from enum import Enum
from typing import Optional
from dabmux.output.base import DabOutput


class EtiFileType(Enum):
    """
    ETI file format types.

    RAW: Raw ETI frames with padding to 6144 bytes
    FRAMED: Frames with count and length headers
    STREAMED: Frames with length prefix only
    """
    NONE = 0
    RAW = 1
    STREAMED = 2
    FRAMED = 3


class FileOutput(DabOutput):
    """
    File output for ETI frames.

    Supports multiple ETI file formats with automatic type detection
    from filename or explicit specification.
    """

    def __init__(self) -> None:
        """Initialize file output."""
        super().__init__()
        self._file: Optional[object] = None
        self._filename: str = ""
        self._file_type: EtiFileType = EtiFileType.FRAMED
        self._frame_count: int = 0

    def open(self, name: str) -> None:
        """
        Open the output file.

        Args:
            name: Path to file (may include ?type=raw/framed/streamed)

        Raises:
            RuntimeError: If file cannot be opened
            ValueError: If name is empty or type is invalid
        """
        if not name:
            raise ValueError("Filename cannot be empty")

        # Parse filename and extract type parameter
        self._filename = self._parse_filename_and_type(name)

        try:
            self._file = open(self._filename, 'wb')
            self._is_open = True
            self._frame_count = 0

            # For framed format, write initial frame count (will be updated later)
            if self._file_type == EtiFileType.FRAMED:
                self._file.write(struct.pack('<I', 0))

        except IOError as e:
            raise RuntimeError(f"Could not open output file {self._filename}: {e}")

    def _parse_filename_and_type(self, name: str) -> str:
        """
        Parse filename and extract type parameter.

        Args:
            name: Filename with optional ?type=xxx parameter

        Returns:
            Filename without type parameter

        Raises:
            ValueError: If type is invalid
        """
        if '?' not in name:
            return name

        # Split at question mark
        filename, query = name.split('?', 1)

        # Parse query parameters
        for param in query.split('&'):
            if '=' not in param:
                continue

            key, value = param.split('=', 1)

            if key == 'type':
                if value == 'raw':
                    self._file_type = EtiFileType.RAW
                elif value == 'framed':
                    self._file_type = EtiFileType.FRAMED
                elif value == 'streamed':
                    self._file_type = EtiFileType.STREAMED
                else:
                    raise ValueError(f"Unsupported file type: {value}")
                break

        return filename

    def write(self, data: bytes) -> int:
        """
        Write an ETI frame to the file.

        Args:
            data: ETI frame data

        Returns:
            Number of bytes written (may differ from input due to framing)

        Raises:
            RuntimeError: On write error
        """
        if not self._is_open or self._file is None:
            raise RuntimeError("Output file is not open")

        size = len(data)
        self._frame_count += 1

        try:
            if self._file_type == EtiFileType.FRAMED:
                # Update frame count at beginning of file
                current_pos = self._file.tell()
                self._file.seek(0, 0)
                self._file.write(struct.pack('<I', self._frame_count))
                self._file.seek(current_pos, 0)

                # Write frame length (2 bytes, little-endian)
                self._file.write(struct.pack('<H', size))

                # Write frame data
                self._file.write(data)

            elif self._file_type == EtiFileType.STREAMED:
                # Write frame length (2 bytes, little-endian)
                self._file.write(struct.pack('<H', size))

                # Write frame data
                self._file.write(data)

            elif self._file_type == EtiFileType.RAW:
                # Write frame data
                self._file.write(data)

                # Pad to 6144 bytes with 0x55
                padding_size = 6144 - size
                if padding_size > 0:
                    padding = bytes([0x55] * padding_size)
                    self._file.write(padding)

            else:
                raise RuntimeError("File type is not supported")

            # Flush to ensure data is written
            self._file.flush()

            return size

        except IOError as e:
            raise RuntimeError(f"Error writing to file: {e}")

    def close(self) -> None:
        """Close the output file."""
        if self._file is not None:
            try:
                # For framed format, ensure final frame count is written
                if self._file_type == EtiFileType.FRAMED:
                    self._file.seek(0, 0)
                    self._file.write(struct.pack('<I', self._frame_count))

                self._file.close()
            except IOError:
                pass
            finally:
                self._file = None
                self._is_open = False

    def get_info(self) -> str:
        """
        Get output information.

        Returns:
            File URL with type information
        """
        type_name = self._file_type.name.lower()
        return f"file://{self._filename}?type={type_name}"

    @property
    def frame_count(self) -> int:
        """Get number of frames written."""
        return self._frame_count
