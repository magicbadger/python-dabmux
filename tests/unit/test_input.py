"""
Unit tests for input abstractions.

These tests verify that input classes work correctly for reading
audio/data from various sources.
"""
import pytest
import tempfile
import os
from dabmux.input.base import InputBase, BufferManagement
from dabmux.input.file import FileInput, RawFileInput, MPEGFileInput, PacketFileInput


class TestBufferManagement:
    """Test buffer management enum."""

    def test_buffer_management_values(self) -> None:
        """Test buffer management enum values."""
        assert BufferManagement.Prebuffering.value == "prebuffering"
        assert BufferManagement.Timestamped.value == "timestamped"


class TestInputBase:
    """Test InputBase abstract class."""

    def test_default_values(self) -> None:
        """Test default input base values using concrete implementation."""
        input_obj = RawFileInput()
        assert input_obj.get_buffer_management() == BufferManagement.Prebuffering
        assert input_obj._tist_delay_ms == 0
        assert input_obj.is_open is False

    def test_set_buffer_management(self) -> None:
        """Test setting buffer management."""
        input_obj = RawFileInput()
        input_obj.set_buffer_management(BufferManagement.Timestamped)
        assert input_obj.get_buffer_management() == BufferManagement.Timestamped

    def test_set_tist_delay(self) -> None:
        """Test setting TIST delay."""
        input_obj = RawFileInput()
        input_obj.set_tist_delay(100)
        assert input_obj._tist_delay_ms == 100


class TestFileInput:
    """Test base FileInput class."""

    def test_default_values(self) -> None:
        """Test default file input values."""
        input_obj = RawFileInput()
        assert input_obj._filename == ""
        assert input_obj._nonblock is False
        assert input_obj._load_entire_file is False
        assert input_obj.is_open is False

    def test_open_nonexistent_file(self) -> None:
        """Test opening nonexistent file raises error."""
        input_obj = RawFileInput()
        with pytest.raises(RuntimeError, match="Could not open"):
            input_obj.open("/nonexistent/file.dat")

    def test_open_empty_filename(self) -> None:
        """Test opening empty filename raises error."""
        input_obj = RawFileInput()
        with pytest.raises(ValueError, match="cannot be empty"):
            input_obj.open("")

    def test_set_bitrate(self) -> None:
        """Test setting bitrate."""
        input_obj = RawFileInput()
        bitrate = input_obj.set_bitrate(128)
        assert bitrate == 128

    def test_set_invalid_bitrate(self) -> None:
        """Test setting invalid bitrate."""
        input_obj = RawFileInput()
        with pytest.raises(ValueError, match="Invalid bitrate"):
            input_obj.set_bitrate(0)

        with pytest.raises(ValueError):
            input_obj.set_bitrate(-100)

    def test_set_nonblocking_with_load_entire_file(self) -> None:
        """Test that nonblock and load_entire_file are mutually exclusive."""
        input_obj = RawFileInput()
        input_obj.set_load_entire_file(True)

        with pytest.raises(RuntimeError, match="Cannot set both"):
            input_obj.set_nonblocking(True)

    def test_set_load_entire_file_with_nonblocking(self) -> None:
        """Test that load_entire_file and nonblock are mutually exclusive."""
        input_obj = RawFileInput()
        input_obj.set_nonblocking(True)

        with pytest.raises(RuntimeError, match="Cannot set both"):
            input_obj.set_load_entire_file(True)


class TestRawFileInput:
    """Test RawFileInput class."""

    def test_read_from_file(self) -> None:
        """Test reading raw data from file."""
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'Hello, DAB World!' * 10
            f.write(test_data)
            temp_path = f.name

        try:
            input_obj = RawFileInput()
            input_obj.open(temp_path)
            assert input_obj.is_open

            # Read some data
            data = input_obj.read_frame(20)
            assert len(data) == 20
            assert data == test_data[:20]

            # Read more data
            data = input_obj.read_frame(30)
            assert len(data) == 30

            input_obj.close()
            assert not input_obj.is_open

        finally:
            os.unlink(temp_path)

    def test_read_frame_from_closed_file(self) -> None:
        """Test reading from closed file returns empty."""
        input_obj = RawFileInput()
        data = input_obj.read_frame(100)
        assert data == b''

    def test_rewind(self) -> None:
        """Test rewinding file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'Test data for rewind'
            f.write(test_data)
            temp_path = f.name

        try:
            input_obj = RawFileInput()
            input_obj.open(temp_path)

            # Read some data
            data1 = input_obj.read_frame(10)

            # Rewind and read again
            input_obj.rewind()
            data2 = input_obj.read_frame(10)

            assert data1 == data2
            input_obj.close()

        finally:
            os.unlink(temp_path)

    def test_load_entire_file(self) -> None:
        """Test loading entire file into memory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'Memory loaded data' * 100
            f.write(test_data)
            temp_path = f.name

        try:
            input_obj = RawFileInput()
            input_obj.set_load_entire_file(True)
            input_obj.open(temp_path)

            # Read data (should come from memory)
            data = input_obj.read_frame(50)
            assert len(data) == 50

            # Rewind should work with memory buffer
            input_obj.rewind()
            data2 = input_obj.read_frame(50)
            assert data == data2

            input_obj.close()

        finally:
            os.unlink(temp_path)


class TestMPEGFileInput:
    """Test MPEGFileInput class."""

    def test_mpeg_file_open(self) -> None:
        """Test opening MPEG file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'\xFF\xFB\x90\x00' + b'\x00' * 100  # MPEG sync + data
            f.write(test_data * 10)
            temp_path = f.name

        try:
            input_obj = MPEGFileInput()
            input_obj.open(temp_path)
            assert input_obj.is_open

            data = input_obj.read_frame(100)
            assert len(data) == 100

            input_obj.close()

        finally:
            os.unlink(temp_path)

    def test_mpeg_bitrate_validation(self) -> None:
        """Test MPEG bitrate validation and rounding."""
        input_obj = MPEGFileInput()

        # Valid bitrate
        bitrate = input_obj.set_bitrate(128)
        assert bitrate == 128

        # Invalid bitrate should round to nearest
        bitrate = input_obj.set_bitrate(100)
        assert bitrate == 96  # Nearest valid

        bitrate = input_obj.set_bitrate(200)
        assert bitrate == 192  # Nearest valid


class TestPacketFileInput:
    """Test PacketFileInput class."""

    def test_packet_file_basic(self) -> None:
        """Test basic packet file reading."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'Packet data' * 20
            f.write(test_data)
            temp_path = f.name

        try:
            input_obj = PacketFileInput(enhanced_packet_mode=False)
            input_obj.open(temp_path)

            data = input_obj.read_frame(50)
            assert len(data) == 50

            input_obj.close()

        finally:
            os.unlink(temp_path)

    def test_packet_file_enhanced_mode(self) -> None:
        """Test packet file with enhanced mode."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b'Enhanced packet' * 30
            f.write(test_data)
            temp_path = f.name

        try:
            input_obj = PacketFileInput(enhanced_packet_mode=True)
            assert input_obj._enhanced_packet_mode is True

            input_obj.open(temp_path)
            data = input_obj.read_frame(100)
            assert len(data) == 100

            input_obj.close()

        finally:
            os.unlink(temp_path)


class TestInputTimestamps:
    """Test timestamp-related functionality."""

    def test_read_frame_timestamped_default(self) -> None:
        """Test timestamped read (not supported by file inputs)."""
        input_obj = RawFileInput()

        # Should return empty data (not supported)
        data = input_obj.read_frame_timestamped(
            size=100,
            seconds=1234567890,
            utco=0,
            tsta=0
        )
        assert data == b''
