"""
Unit tests for unified input factory.

Tests the InputFactory for creating all types of inputs based on
subchannel type and URI scheme.
"""
import os
import tempfile
import pytest

from dabmux.input.factory import InputFactory
from dabmux.input.base import InputBase
from dabmux.input.dabplus_input import DABPlusInput
from dabmux.input.dabplus_file import DABPlusFileInput
from dabmux.input.dabplus_udp import DABPlusUdpInput
from dabmux.input.dabplus_fifo import DABPlusFifoInput
from dabmux.input.file import MPEGFileInput, RawFileInput
from dabmux.core.mux_elements import SubchannelType


class TestInputFactory:
    """Test unified input factory."""

    def test_create_dabplus_file_input(self):
        """Test creating DAB+ file input."""
        with tempfile.NamedTemporaryFile(suffix='.dabp', delete=False) as f:
            temp_path = f.name
            # Write some test data
            f.write(b'\x00' * 720)  # 720 bytes = 48 kbps superframe

        try:
            inp = InputFactory.create(
                uri=f'file://{temp_path}',
                subchannel_type=SubchannelType.DABPlusAudio,
                bitrate=48
            )

            assert isinstance(inp, DABPlusFileInput)
            assert inp.bitrate == 48
            assert inp.is_open()  # Factory opens inputs automatically

            inp.close()

        finally:
            os.unlink(temp_path)

    def test_create_dabplus_file_input_no_scheme(self):
        """Test creating DAB+ file input without URI scheme."""
        with tempfile.NamedTemporaryFile(suffix='.dabp', delete=False) as f:
            temp_path = f.name
            f.write(b'\x00' * 720)

        try:
            inp = InputFactory.create(
                uri=temp_path,  # No file:// prefix
                subchannel_type=SubchannelType.DABPlusAudio,
                bitrate=48
            )

            assert isinstance(inp, DABPlusFileInput)
            assert inp.is_open()
            inp.close()

        finally:
            os.unlink(temp_path)

    def test_create_dabplus_udp_input(self):
        """Test creating DAB+ UDP input."""
        port = 19000 + os.getpid() % 10000

        inp = InputFactory.create(
            uri=f'udp://127.0.0.1:{port}',
            subchannel_type=SubchannelType.DABPlusAudio,
            bitrate=48
        )

        assert isinstance(inp, DABPlusUdpInput)
        assert inp.bitrate == 48
        assert inp.is_open()

        inp.close()

    @pytest.mark.skipif(os.name == 'nt', reason="FIFOs not supported on Windows")
    def test_create_dabplus_fifo_input(self):
        """Test creating DAB+ FIFO input."""
        fifo_path = tempfile.mktemp(suffix='.fifo')

        try:
            os.mkfifo(fifo_path)

            inp = InputFactory.create(
                uri=f'fifo://{fifo_path}',
                subchannel_type=SubchannelType.DABPlusAudio,
                bitrate=48
            )

            assert isinstance(inp, DABPlusFifoInput)
            assert inp.bitrate == 48
            # Note: FIFO won't be open until a writer connects

            inp.close()

        finally:
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)

    def test_create_dab_mpeg_input(self):
        """Test creating DAB MPEG input."""
        with tempfile.NamedTemporaryFile(suffix='.mp2', delete=False) as f:
            temp_path = f.name
            # Write minimal MPEG header
            f.write(b'\xFF\xFD\x64\x04' + b'\x00' * 288)

        try:
            inp = InputFactory.create(
                uri=f'file://{temp_path}',
                subchannel_type=SubchannelType.DABAudio,
                bitrate=96
            )

            assert isinstance(inp, MPEGFileInput)
            assert inp._is_open  # Legacy inputs use _is_open attribute

            inp.close()

        finally:
            os.unlink(temp_path)

    def test_create_data_input(self):
        """Test creating data subchannel input."""
        with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as f:
            temp_path = f.name
            f.write(b'\x00' * 1024)

        try:
            inp = InputFactory.create(
                uri=f'file://{temp_path}',
                subchannel_type=SubchannelType.Packet,
                bitrate=32
            )

            assert isinstance(inp, RawFileInput)
            assert inp._is_open  # Legacy inputs use _is_open attribute

            inp.close()

        finally:
            os.unlink(temp_path)

    def test_dab_udp_not_supported(self):
        """Test that UDP is not supported for DAB audio."""
        with pytest.raises(NotImplementedError, match="only supports file://"):
            InputFactory.create(
                uri='udp://0.0.0.0:9000',
                subchannel_type=SubchannelType.DABAudio,
                bitrate=96
            )

    def test_data_udp_not_supported(self):
        """Test that UDP is not supported for data subchannels."""
        with pytest.raises(NotImplementedError, match="only support file://"):
            InputFactory.create(
                uri='udp://0.0.0.0:9000',
                subchannel_type=SubchannelType.Packet,
                bitrate=32
            )

    def test_invalid_subchannel_type(self):
        """Test invalid subchannel type."""
        with pytest.raises(ValueError, match="Unsupported subchannel type"):
            InputFactory.create(
                uri='file:///tmp/test',
                subchannel_type=None,
                bitrate=48
            )

    def test_validate_uri_dabplus_file(self):
        """Test URI validation for DAB+ file."""
        valid, error = InputFactory.validate_uri(
            'file:///tmp/test.dabp',
            SubchannelType.DABPlusAudio
        )
        assert valid
        assert error is None

    def test_validate_uri_dabplus_udp(self):
        """Test URI validation for DAB+ UDP."""
        valid, error = InputFactory.validate_uri(
            'udp://0.0.0.0:9000',
            SubchannelType.DABPlusAudio
        )
        assert valid
        assert error is None

    def test_validate_uri_dab_file(self):
        """Test URI validation for DAB file."""
        valid, error = InputFactory.validate_uri(
            'file:///tmp/audio.mp2',
            SubchannelType.DABAudio
        )
        assert valid
        assert error is None

    def test_validate_uri_dab_udp_invalid(self):
        """Test URI validation for DAB UDP (not supported)."""
        valid, error = InputFactory.validate_uri(
            'udp://0.0.0.0:9000',
            SubchannelType.DABAudio
        )
        assert not valid
        assert 'Only file://' in error

    def test_validate_uri_empty_path(self):
        """Test URI validation with empty path."""
        valid, error = InputFactory.validate_uri(
            'file://',
            SubchannelType.DABAudio
        )
        assert not valid
        assert 'Empty file path' in error

    def test_get_supported_schemes_dabplus(self):
        """Test getting supported schemes for DAB+."""
        schemes = InputFactory.get_supported_schemes(SubchannelType.DABPlusAudio)
        assert 'file' in schemes
        assert 'fifo' in schemes
        assert 'udp' in schemes

    def test_get_supported_schemes_dab(self):
        """Test getting supported schemes for DAB."""
        schemes = InputFactory.get_supported_schemes(SubchannelType.DABAudio)
        assert schemes == ['file']

    def test_get_supported_schemes_data(self):
        """Test getting supported schemes for data."""
        schemes = InputFactory.get_supported_schemes(SubchannelType.Packet)
        assert schemes == ['file']

    def test_create_with_loop_parameter(self):
        """Test creating input with loop parameter."""
        with tempfile.NamedTemporaryFile(suffix='.dabp', delete=False) as f:
            temp_path = f.name
            f.write(b'\x00' * 720)

        try:
            inp = InputFactory.create(
                uri=temp_path,
                subchannel_type=SubchannelType.DABPlusAudio,
                bitrate=48,
                loop=True
            )

            assert isinstance(inp, DABPlusFileInput)
            assert inp.loop is True

            inp.close()

        finally:
            os.unlink(temp_path)

    def test_inheritance_dabplus_input(self):
        """Test that DAB+ inputs inherit from DABPlusInput."""
        with tempfile.NamedTemporaryFile(suffix='.dabp', delete=False) as f:
            temp_path = f.name
            f.write(b'\x00' * 720)

        try:
            inp = InputFactory.create(
                uri=temp_path,
                subchannel_type=SubchannelType.DABPlusAudio,
                bitrate=48
            )

            assert isinstance(inp, DABPlusInput)
            assert hasattr(inp, 'get_frame_size')
            assert hasattr(inp, 'read_frame')

            inp.close()

        finally:
            os.unlink(temp_path)

    def test_inheritance_input_base(self):
        """Test that DAB inputs inherit from InputBase."""
        with tempfile.NamedTemporaryFile(suffix='.mp2', delete=False) as f:
            temp_path = f.name
            f.write(b'\xFF\xFD\x64\x04' + b'\x00' * 288)

        try:
            inp = InputFactory.create(
                uri=temp_path,
                subchannel_type=SubchannelType.DABAudio,
                bitrate=96
            )

            assert isinstance(inp, InputBase)
            assert hasattr(inp, 'read_frame')
            assert hasattr(inp, '_is_open')  # Legacy inputs use _is_open

            inp.close()

        finally:
            os.unlink(temp_path)
