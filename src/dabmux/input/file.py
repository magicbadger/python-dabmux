"""
File-based input implementations.

This module provides input classes for reading DAB data from files,
including MPEG, raw binary, and packet formats.
"""
import os
import structlog
from typing import Optional
from dabmux.input.base import InputBase
from dabmux.audio.mpeg import MpegFrameParser
from dabmux.fec.reed_solomon import ReedSolomonDAB

logger = structlog.get_logger()


class FileInput(InputBase):
    """
    Base class for file-based inputs.

    Provides common functionality for reading from files with support
    for non-blocking I/O and full file preloading.
    """

    def __init__(self) -> None:
        """Initialize the file input."""
        super().__init__()
        self._file: Optional[object] = None
        self._filename: str = ""
        self._nonblock: bool = False
        self._load_entire_file: bool = False
        self._file_contents: bytes = b''
        self._file_offset: int = 0
        self._bitrate: int = 0

    def open(self, name: str) -> None:
        """
        Open the input file.

        Args:
            name: Path to the file

        Raises:
            RuntimeError: If file cannot be opened
            ValueError: If name is empty
        """
        if not name:
            raise ValueError("Filename cannot be empty")

        self._filename = name

        if self._load_entire_file:
            self._load_file_contents()
        else:
            try:
                mode = 'rb'
                self._file = open(name, mode)
                self._is_open = True
            except IOError as e:
                raise RuntimeError(f"Could not open input file {name}: {e}")

    def _load_file_contents(self) -> None:
        """Load entire file into memory."""
        try:
            with open(self._filename, 'rb') as f:
                self._file_contents = f.read()
            self._file_offset = 0
            self._is_open = True
        except IOError as e:
            raise RuntimeError(f"Could not load file {self._filename}: {e}")

    def set_bitrate(self, bitrate: int) -> int:
        """
        Set the input bitrate.

        Args:
            bitrate: Bitrate in kbps

        Returns:
            Effective bitrate (same as input for files)

        Raises:
            ValueError: If bitrate is invalid
        """
        if bitrate <= 0:
            raise ValueError(f"Invalid bitrate: {bitrate}")
        self._bitrate = bitrate
        return bitrate

    def close(self) -> None:
        """Close the input file."""
        if self._file is not None:
            self._file.close()
            self._file = None
        self._is_open = False

    def set_nonblocking(self, nonblock: bool) -> None:
        """
        Set non-blocking I/O mode.

        Args:
            nonblock: True for non-blocking mode

        Raises:
            RuntimeError: If load_entire_file is also set
        """
        if self._load_entire_file:
            raise RuntimeError("Cannot set both nonblock and load_entire_file")
        self._nonblock = nonblock

    def set_load_entire_file(self, load: bool) -> None:
        """
        Set whether to load entire file into memory.

        Args:
            load: True to load entire file

        Raises:
            RuntimeError: If nonblock is also set
        """
        if self._nonblock:
            raise RuntimeError("Cannot set both nonblock and load_entire_file")
        self._load_entire_file = load

    def rewind(self) -> None:
        """Rewind to the beginning of the file."""
        if self._load_entire_file:
            self._file_offset = 0
        elif self._file is not None:
            self._file.seek(0, 0)
        else:
            raise RuntimeError("Cannot rewind closed file")

    def _read_from_file(self, size: int) -> bytes:
        """
        Read bytes from file or memory buffer.

        Args:
            size: Number of bytes to read

        Returns:
            Data bytes read
        """
        if self._load_entire_file:
            # Read from memory buffer
            data = self._file_contents[self._file_offset:self._file_offset + size]
            self._file_offset += len(data)
            return data
        elif self._file is not None:
            # Read from file handle
            return self._file.read(size)
        else:
            return b''


class RawFileInput(FileInput):
    """
    Raw binary file input.

    Reads raw DAB frames directly from a file without any framing or formatting.
    """

    def read_frame(self, size: int) -> bytes:
        """
        Read a raw frame.

        Args:
            size: Number of bytes to read

        Returns:
            Raw data bytes
        """
        if not self._is_open:
            return b''

        data = self._read_from_file(size)

        # If we reached EOF and should loop, rewind
        if len(data) < size and self._load_entire_file:
            self.rewind()
            # Try reading again after rewind
            remaining = size - len(data)
            data += self._read_from_file(remaining)

        return data


class MPEGFileInput(FileInput):
    """
    MPEG file input with frame parsing.

    Reads MPEG frames, validates headers, and provides data for DAB audio streams.
    Supports MPEG Layer II audio (MP2) commonly used in DAB.
    """

    def __init__(self) -> None:
        """Initialize MPEG file input."""
        super().__init__()
        self._parity: bool = False
        self._parser = MpegFrameParser()
        self._read_buffer: bytearray = bytearray()
        self._frame_count: int = 0

    def read_frame(self, size: int) -> bytes:
        """
        Read an MPEG frame.

        Searches for MPEG sync, validates header, and returns frame data.
        If frame size differs from requested size, returns padded/truncated data.

        Args:
            size: Expected frame size in bytes

        Returns:
            MPEG frame data (padded to size if needed)
        """
        if not self._is_open:
            return bytes(size)  # Return silence

        # Read more data if buffer is low
        if len(self._read_buffer) < size + 2000:
            chunk = self._read_from_file(4096)
            if chunk:
                self._read_buffer.extend(chunk)
            elif len(self._read_buffer) == 0:
                # EOF and buffer empty
                if self._load_entire_file:
                    # Loop back to beginning
                    self.rewind()
                    chunk = self._read_from_file(4096)
                    if chunk:
                        self._read_buffer.extend(chunk)

                if len(self._read_buffer) == 0:
                    # Still no data, return silence
                    logger.warning("MPEG input underrun", size=size)
                    return bytes(size)

        # Try to parse an MPEG frame
        result = self._parser.read_frame(bytes(self._read_buffer))

        if result is None:
            # No valid frame found, skip first byte and try again next time
            if len(self._read_buffer) > 0:
                self._read_buffer.pop(0)

            logger.debug("No valid MPEG frame found")
            return bytes(size)  # Return silence

        header, frame_data = result
        frame_length = len(frame_data)

        # Remove consumed data from buffer
        self._read_buffer = self._read_buffer[frame_length:]

        self._frame_count += 1

        # Log frame info occasionally
        if self._frame_count % 100 == 0:
            logger.debug(
                "MPEG frame",
                count=self._frame_count,
                bitrate=header.get_bitrate(),
                sampling_rate=header.get_sampling_rate(),
                length=frame_length
            )

        # Adjust to requested size
        if frame_length == size:
            return frame_data
        elif frame_length < size:
            # Pad with zeros
            return frame_data + bytes(size - frame_length)
        else:
            # Truncate
            logger.warning(
                "MPEG frame too large, truncating",
                frame_size=frame_length,
                requested=size
            )
            return frame_data[:size]

    def set_bitrate(self, bitrate: int) -> int:
        """
        Set MPEG bitrate.

        Args:
            bitrate: Bitrate in kbps

        Returns:
            Effective bitrate

        Raises:
            ValueError: If bitrate is invalid for MPEG
        """
        if bitrate <= 0:
            raise ValueError(f"Invalid bitrate: {bitrate}")

        # Validate against common DAB bitrates
        valid_bitrates = [32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384]
        if bitrate not in valid_bitrates:
            # Find nearest valid bitrate
            nearest = min(valid_bitrates, key=lambda x: abs(x - bitrate))
            logger.info(
                "Adjusting bitrate to nearest valid value",
                requested=bitrate,
                actual=nearest
            )
            self._bitrate = nearest
            return nearest

        self._bitrate = bitrate
        return bitrate


class PacketFileInput(FileInput):
    """
    Packet mode file input with optional Reed-Solomon FEC.

    Reads packetized data for DAB packet mode services.
    Supports enhanced packet mode with RS(204, 188) encoding.
    """

    def __init__(self, enhanced_packet_mode: bool = False) -> None:
        """
        Initialize packet file input.

        Args:
            enhanced_packet_mode: Enable FEC for MSC packet mode
        """
        super().__init__()
        self._enhanced_packet_mode = enhanced_packet_mode
        self._packet_data: bytearray = bytearray()
        self._packet_length: int = 0

        # Enhanced packet mode uses RS(204, 188)
        # 12 rows of 188 bytes each = 2256 bytes input
        # Encoded to 12 rows of 204 bytes = 2448 bytes output
        if enhanced_packet_mode:
            self._rs_encoder = ReedSolomonDAB.packet_mode()
            self._enhanced_buffer = bytearray()
            self._enhanced_parity_waiting = 0

    def read_frame(self, size: int) -> bytes:
        """
        Read a packet frame with optional RS encoding.

        For enhanced packet mode, applies RS(204, 188) encoding
        to 12 x 188-byte rows.

        Args:
            size: Number of bytes to read

        Returns:
            Packet data (with RS parity if enhanced mode)
        """
        if not self._is_open:
            return bytes(size)

        if self._enhanced_packet_mode:
            return self._read_enhanced_packet(size)
        else:
            # Standard packet mode (no FEC)
            data = self._read_from_file(size)

            if len(data) < size and self._load_entire_file:
                self.rewind()
                remaining = size - len(data)
                data += self._read_from_file(remaining)

            # Pad if necessary
            if len(data) < size:
                data += bytes(size - len(data))

            return data

    def _read_enhanced_packet(self, size: int) -> bytes:
        """
        Read enhanced packet with RS encoding.

        Accumulates 12 x 188 byte rows, encodes with RS(204, 188),
        then outputs the encoded data with parity.

        Args:
            size: Number of bytes to read

        Returns:
            Encoded packet data
        """
        output = bytearray()

        while len(output) < size:
            # If we have parity waiting to output
            if self._enhanced_parity_waiting > 0:
                # Output parity bytes
                to_output = min(self._enhanced_parity_waiting, size - len(output))
                output.extend(self._enhanced_buffer[:to_output])
                self._enhanced_buffer = self._enhanced_buffer[to_output:]
                self._enhanced_parity_waiting -= to_output
                continue

            # Read data to accumulate 12 x 188 bytes
            needed = (12 * 188) - len(self._packet_data)
            if needed > 0:
                chunk = self._read_from_file(needed)
                if not chunk:
                    if self._load_entire_file:
                        self.rewind()
                        chunk = self._read_from_file(needed)

                if chunk:
                    self._packet_data.extend(chunk)

            # If we have enough data, encode it
            if len(self._packet_data) >= (12 * 188):
                # Encode 12 rows with RS(204, 188)
                for i in range(12):
                    row_start = i * 188
                    row_data = bytes(self._packet_data[row_start:row_start + 188])

                    # Encode row (188 bytes info + 16 bytes parity)
                    parity = self._rs_encoder.encode(row_data)

                    # Output information bytes first
                    output.extend(row_data)

                    # Store parity for later output
                    self._enhanced_buffer.extend(parity)

                # Mark parity as waiting (12 rows × 16 bytes = 192 bytes)
                self._enhanced_parity_waiting = 192

                # Remove processed data
                self._packet_data = self._packet_data[12 * 188:]
            else:
                # Not enough data, pad and break
                remaining = size - len(output)
                output.extend(bytes(remaining))
                break

        return bytes(output[:size])
