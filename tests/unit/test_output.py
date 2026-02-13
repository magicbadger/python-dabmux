"""
Unit tests for output abstractions.

These tests verify that output classes work correctly for writing
ETI frames to various destinations.
"""
import pytest
import tempfile
import os
import struct
from dabmux.output.base import DabOutput
from dabmux.output.file import FileOutput, EtiFileType


class TestEtiFileType:
    """Test ETI file type enum."""

    def test_file_type_values(self) -> None:
        """Test file type enum values."""
        assert EtiFileType.NONE.value == 0
        assert EtiFileType.RAW.value == 1
        assert EtiFileType.STREAMED.value == 2
        assert EtiFileType.FRAMED.value == 3


class TestDabOutputBase:
    """Test DabOutput abstract class."""

    def test_default_values(self) -> None:
        """Test default output base values."""
        output = FileOutput()
        assert output.is_open is False


class TestFileOutput:
    """Test FileOutput class."""

    def test_default_values(self) -> None:
        """Test default file output values."""
        output = FileOutput()
        assert output._filename == ""
        assert output._file_type == EtiFileType.FRAMED
        assert output._frame_count == 0
        assert output.is_open is False

    def test_open_empty_filename(self) -> None:
        """Test opening empty filename raises error."""
        output = FileOutput()
        with pytest.raises(ValueError, match="cannot be empty"):
            output.open("")

    def test_open_file(self) -> None:
        """Test opening output file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            # File should be created and opened
            output = FileOutput()
            output.open(temp_path)
            assert output.is_open
            assert output._filename == temp_path

            output.close()
            assert not output.is_open

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_parse_filename_framed_type(self) -> None:
        """Test parsing filename with framed type."""
        output = FileOutput()
        filename = output._parse_filename_and_type("output.eti?type=framed")
        assert filename == "output.eti"
        assert output._file_type == EtiFileType.FRAMED

    def test_parse_filename_raw_type(self) -> None:
        """Test parsing filename with raw type."""
        output = FileOutput()
        filename = output._parse_filename_and_type("output.eti?type=raw")
        assert filename == "output.eti"
        assert output._file_type == EtiFileType.RAW

    def test_parse_filename_streamed_type(self) -> None:
        """Test parsing filename with streamed type."""
        output = FileOutput()
        filename = output._parse_filename_and_type("output.eti?type=streamed")
        assert filename == "output.eti"
        assert output._file_type == EtiFileType.STREAMED

    def test_parse_filename_invalid_type(self) -> None:
        """Test parsing filename with invalid type."""
        output = FileOutput()
        with pytest.raises(ValueError, match="Unsupported file type"):
            output._parse_filename_and_type("output.eti?type=invalid")

    def test_parse_filename_no_type(self) -> None:
        """Test parsing filename without type parameter."""
        output = FileOutput()
        filename = output._parse_filename_and_type("output.eti")
        assert filename == "output.eti"
        assert output._file_type == EtiFileType.FRAMED  # Default

    def test_write_framed_format(self) -> None:
        """Test writing in framed format."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path + "?type=framed")

            # Write test frames
            test_data = b'Frame 1 data' + b'\x00' * 100
            output.write(test_data)

            test_data2 = b'Frame 2 data' + b'\x00' * 100
            output.write(test_data2)

            assert output.frame_count == 2
            output.close()

            # Verify file format
            with open(temp_path, 'rb') as f:
                # Read frame count (first 4 bytes)
                frame_count = struct.unpack('<I', f.read(4))[0]
                assert frame_count == 2

                # Read first frame
                frame_len = struct.unpack('<H', f.read(2))[0]
                frame_data = f.read(frame_len)
                assert len(frame_data) == frame_len

                # Read second frame
                frame_len = struct.unpack('<H', f.read(2))[0]
                frame_data = f.read(frame_len)
                assert len(frame_data) == frame_len

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_write_streamed_format(self) -> None:
        """Test writing in streamed format."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path + "?type=streamed")

            # Write test frame
            test_data = b'Streamed frame' + b'\x00' * 100
            written = output.write(test_data)
            assert written == len(test_data)

            output.close()

            # Verify file format
            with open(temp_path, 'rb') as f:
                # Read frame length (2 bytes)
                frame_len = struct.unpack('<H', f.read(2))[0]
                assert frame_len == len(test_data)

                # Read frame data
                frame_data = f.read(frame_len)
                assert len(frame_data) == frame_len

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_write_raw_format(self) -> None:
        """Test writing in raw format with padding."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path + "?type=raw")

            # Write test frame (should be padded to 6144 bytes)
            test_data = b'Raw frame' + b'\x00' * 100
            written = output.write(test_data)
            assert written == len(test_data)

            output.close()

            # Verify file format
            with open(temp_path, 'rb') as f:
                # Read entire frame (should be 6144 bytes)
                frame_data = f.read(6144)
                assert len(frame_data) == 6144

                # First part should be our data
                assert frame_data[:len(test_data)] == test_data

                # Rest should be padding (0x55)
                padding = frame_data[len(test_data):]
                assert all(b == 0x55 for b in padding)

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_write_to_closed_file(self) -> None:
        """Test writing to closed file raises error."""
        output = FileOutput()
        with pytest.raises(RuntimeError, match="not open"):
            output.write(b'test data')

    def test_get_info(self) -> None:
        """Test getting output information."""
        output = FileOutput()
        output._filename = "/path/to/output.eti"
        output._file_type = EtiFileType.FRAMED

        info = output.get_info()
        assert info == "file:///path/to/output.eti?type=framed"

    def test_multiple_writes(self) -> None:
        """Test writing multiple frames."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path + "?type=streamed")

            # Write multiple frames
            for i in range(10):
                data = f'Frame {i}'.encode() + b'\x00' * 100
                output.write(data)

            assert output.frame_count == 10
            output.close()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_frame_count_tracking(self) -> None:
        """Test that frame count is properly tracked."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path)

            assert output.frame_count == 0

            output.write(b'Frame 1' + b'\x00' * 100)
            assert output.frame_count == 1

            output.write(b'Frame 2' + b'\x00' * 100)
            assert output.frame_count == 2

            output.close()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestFileOutputEdgeCases:
    """Test edge cases for file output."""

    def test_write_empty_frame(self) -> None:
        """Test writing empty frame."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path + "?type=streamed")

            # Write empty frame
            written = output.write(b'')
            assert written == 0
            assert output.frame_count == 1

            output.close()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_write_large_frame(self) -> None:
        """Test writing large frame."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.eti') as f:
            temp_path = f.name

        try:
            output = FileOutput()
            output.open(temp_path + "?type=raw")

            # Write large frame (larger than 6144 bytes)
            large_data = b'X' * 7000
            written = output.write(large_data)
            assert written == len(large_data)

            output.close()

            # Verify padding still added (6144 - 7000 = negative, so no padding)
            with open(temp_path, 'rb') as f:
                data = f.read()
                # For raw format with data > 6144, should be data + no padding
                assert len(data) == len(large_data)

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
