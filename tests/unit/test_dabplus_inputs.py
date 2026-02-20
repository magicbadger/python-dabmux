"""
Unit tests for DAB+ input sources.

Tests file, FIFO, and UDP inputs for pre-encoded DAB+ streams.
"""

import os
import tempfile
import socket
import threading
import time
import pytest
from pathlib import Path

from dabmux.input.dabplus_file import DABPlusFileInput
from dabmux.input.dabplus_fifo import DABPlusFifoInput
from dabmux.input.dabplus_udp import DABPlusUdpInput
from dabmux.input.dabplus_factory import DABPlusInputFactory


class TestDABPlusFileInput:
    """Test DAB+ file input."""

    def test_create_file_input(self):
        """Test creating file input."""
        inp = DABPlusFileInput('/tmp/test.dabp', bitrate=48, loop=True)
        assert inp.bitrate == 48
        assert inp.frame_size == 144  # (48/8) * 120 / 5
        assert inp.loop is True

    def test_frame_size_calculation(self):
        """Test frame size calculation for different bitrates."""
        test_cases = [
            (24, 72),   # (24/8) * 120 / 5 = 3 * 24 = 72
            (32, 96),   # (32/8) * 120 / 5 = 4 * 24 = 96
            (48, 144),  # (48/8) * 120 / 5 = 6 * 24 = 144
            (64, 192),  # (64/8) * 120 / 5 = 8 * 24 = 192
            (96, 288),  # (96/8) * 120 / 5 = 12 * 24 = 288
        ]

        for bitrate, expected_size in test_cases:
            inp = DABPlusFileInput('/tmp/test.dabp', bitrate=bitrate)
            assert inp.frame_size == expected_size, f"Bitrate {bitrate} kbps"

    def test_open_nonexistent_file(self):
        """Test opening file that doesn't exist."""
        inp = DABPlusFileInput('/tmp/nonexistent_file_12345.dabp', bitrate=48)
        assert not inp.open()
        assert not inp.is_open()

    def test_open_and_read_file(self):
        """Test opening and reading from actual file."""
        # Create temporary test file with known data
        with tempfile.NamedTemporaryFile(suffix='.dabp', delete=False) as f:
            temp_path = f.name
            # Write 5 frames worth of test data (144 bytes each for 48 kbps)
            test_data = b''.join([bytes([i] * 144) for i in range(5)])
            f.write(test_data)

        try:
            inp = DABPlusFileInput(temp_path, bitrate=48, loop=False)
            assert inp.open()
            assert inp.is_open()

            # Read frames and verify
            for i in range(5):
                frame = inp.read_frame(144)
                assert len(frame) == 144
                assert frame == bytes([i] * 144)

            # Next read should return zeros (no loop)
            frame = inp.read_frame(144)
            assert frame == b'\x00' * 144

            inp.close()
            assert not inp.is_open()

        finally:
            os.unlink(temp_path)

    def test_file_looping(self):
        """Test file looping behavior."""
        # Create small test file
        with tempfile.NamedTemporaryFile(suffix='.dabp', delete=False) as f:
            temp_path = f.name
            # Write 2 frames
            f.write(b'A' * 144 + b'B' * 144)

        try:
            inp = DABPlusFileInput(temp_path, bitrate=48, loop=True)
            assert inp.open()

            # Read first 2 frames
            frame1 = inp.read_frame(144)
            frame2 = inp.read_frame(144)
            assert frame1 == b'A' * 144
            assert frame2 == b'B' * 144

            # Should loop back to beginning
            frame3 = inp.read_frame(144)
            assert frame3 == b'A' * 144
            assert inp.get_loop_count() == 1

            inp.close()

        finally:
            os.unlink(temp_path)

    def test_empty_file(self):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(suffix='.dabp', delete=False) as f:
            temp_path = f.name
            # Leave file empty

        try:
            inp = DABPlusFileInput(temp_path, bitrate=48)
            assert not inp.open()  # Should fail to open empty file

        finally:
            os.unlink(temp_path)


class TestDABPlusFifoInput:
    """Test DAB+ FIFO input."""

    def test_create_fifo_input(self):
        """Test creating FIFO input."""
        inp = DABPlusFifoInput('/tmp/test.fifo', bitrate=48, timeout=1.0)
        assert inp.bitrate == 48
        assert inp.frame_size == 144
        assert inp.timeout == 1.0

    def test_open_nonexistent_fifo(self):
        """Test opening FIFO that doesn't exist."""
        inp = DABPlusFifoInput('/tmp/nonexistent_fifo_12345', bitrate=48)
        assert not inp.open()
        assert not inp.is_open()

    @pytest.mark.skipif(os.name == 'nt', reason="FIFOs not supported on Windows")
    def test_open_regular_file_as_fifo(self):
        """Test that opening regular file as FIFO fails."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            inp = DABPlusFifoInput(temp_path, bitrate=48)
            assert not inp.open()  # Should fail - not a FIFO

        finally:
            os.unlink(temp_path)

    @pytest.mark.skipif(os.name == 'nt', reason="FIFOs not supported on Windows")
    def test_fifo_read_write(self):
        """Test reading and writing through FIFO."""
        fifo_path = tempfile.mktemp(suffix='.fifo')

        try:
            # Create FIFO
            os.mkfifo(fifo_path)

            inp = DABPlusFifoInput(fifo_path, bitrate=48, timeout=2.0)

            # Writer thread to prevent blocking
            def writer():
                time.sleep(0.1)  # Give reader time to open
                with open(fifo_path, 'wb') as f:
                    # Write 3 frames
                    for i in range(3):
                        f.write(bytes([i] * 144))
                        f.flush()

            writer_thread = threading.Thread(target=writer)
            writer_thread.start()

            # Open and read
            assert inp.open()
            assert inp.is_open()

            # Read frames
            for i in range(3):
                frame = inp.read_frame(144)
                assert len(frame) == 144
                assert frame == bytes([i] * 144)

            writer_thread.join()
            inp.close()

        finally:
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)

    @pytest.mark.skipif(os.name == 'nt', reason="FIFOs not supported on Windows")
    def test_fifo_timeout(self):
        """Test FIFO read timeout."""
        fifo_path = tempfile.mktemp(suffix='.fifo')

        try:
            os.mkfifo(fifo_path)

            inp = DABPlusFifoInput(fifo_path, bitrate=48, timeout=0.5)

            # Writer thread that doesn't write anything
            def dummy_writer():
                time.sleep(0.1)
                with open(fifo_path, 'wb') as f:
                    pass  # Don't write anything

            writer_thread = threading.Thread(target=dummy_writer)
            writer_thread.start()

            assert inp.open()

            # Read should timeout and return zeros
            frame = inp.read_frame(144)
            assert len(frame) == 144
            assert frame == b'\x00' * 144
            assert inp.get_stats()['underruns'] > 0

            writer_thread.join()
            inp.close()

        finally:
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)


class TestDABPlusUdpInput:
    """Test DAB+ UDP input."""

    def test_create_udp_input(self):
        """Test creating UDP input."""
        inp = DABPlusUdpInput('0.0.0.0', 9000, bitrate=48, buffer_frames=10)
        assert inp.host == '0.0.0.0'
        assert inp.port == 9000
        assert inp.bitrate == 48
        assert inp.frame_size == 144

    def test_udp_open_close(self):
        """Test opening and closing UDP socket."""
        # Use high port number to avoid conflicts
        port = 19000 + os.getpid() % 10000

        inp = DABPlusUdpInput('127.0.0.1', port, bitrate=48)
        assert inp.open()
        assert inp.is_open()

        inp.close()
        assert not inp.is_open()

    def test_udp_receive_frames(self):
        """Test receiving frames via UDP."""
        port = 19000 + os.getpid() % 10000

        inp = DABPlusUdpInput('127.0.0.1', port, bitrate=48, buffer_frames=5)
        assert inp.open()

        # Sender thread
        def sender():
            time.sleep(0.2)  # Give receiver time to start
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Send 3 frames
                for i in range(3):
                    data = bytes([i] * 144)
                    sock.sendto(data, ('127.0.0.1', port))
                    time.sleep(0.05)
            finally:
                sock.close()

        sender_thread = threading.Thread(target=sender)
        sender_thread.start()

        # Receive frames
        received_frames = []
        for _ in range(3):
            frame = inp.read_frame(144)
            received_frames.append(frame)

        sender_thread.join()

        # Verify
        for i, frame in enumerate(received_frames):
            assert len(frame) == 144
            assert frame == bytes([i] * 144)

        stats = inp.get_stats()
        assert stats['frames_received'] == 3
        assert stats['frames_dropped'] == 0

        inp.close()

    def test_udp_buffer_overflow(self):
        """Test UDP buffer overflow behavior."""
        port = 19000 + os.getpid() % 10000

        # Small buffer to trigger overflow
        inp = DABPlusUdpInput('127.0.0.1', port, bitrate=48, buffer_frames=2)
        assert inp.open()

        # Sender floods with frames
        def sender():
            time.sleep(0.1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Send many frames quickly
                for i in range(10):
                    data = bytes([i % 256] * 144)
                    sock.sendto(data, ('127.0.0.1', port))
            finally:
                sock.close()

        sender_thread = threading.Thread(target=sender)
        sender_thread.start()
        sender_thread.join()

        time.sleep(0.3)  # Let receiver process

        stats = inp.get_stats()
        # Should have dropped some frames due to small buffer
        assert stats['frames_dropped'] > 0 or stats['frames_received'] < 10

        inp.close()

    def test_udp_wrong_packet_size(self):
        """Test handling of incorrectly sized packets."""
        port = 19000 + os.getpid() % 10000

        inp = DABPlusUdpInput('127.0.0.1', port, bitrate=48)
        assert inp.open()

        # Send wrong sized packet
        def sender():
            time.sleep(0.1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # Send packet that's too small
                sock.sendto(b'X' * 100, ('127.0.0.1', port))
                # Send correct packet
                sock.sendto(b'Y' * 144, ('127.0.0.1', port))
            finally:
                sock.close()

        sender_thread = threading.Thread(target=sender)
        sender_thread.start()
        sender_thread.join()

        time.sleep(0.3)

        # Read should get the correct packet
        frame = inp.read_frame(144)
        assert frame == b'Y' * 144

        stats = inp.get_stats()
        assert stats['size_errors'] > 0

        inp.close()


class TestDABPlusInputFactory:
    """Test DAB+ input factory."""

    def test_create_file_input(self):
        """Test creating file input from URI."""
        inp = DABPlusInputFactory.create('file:///tmp/test.dabp', bitrate=48)
        assert isinstance(inp, DABPlusFileInput)
        assert inp.bitrate == 48

    def test_create_file_input_no_scheme(self):
        """Test creating file input without scheme."""
        inp = DABPlusInputFactory.create('/tmp/test.dabp', bitrate=48)
        assert isinstance(inp, DABPlusFileInput)

    def test_create_fifo_input(self):
        """Test creating FIFO input from URI."""
        inp = DABPlusInputFactory.create('fifo:///tmp/test.fifo', bitrate=48)
        assert isinstance(inp, DABPlusFifoInput)
        assert inp.bitrate == 48

    def test_create_udp_input(self):
        """Test creating UDP input from URI."""
        inp = DABPlusInputFactory.create('udp://0.0.0.0:9000', bitrate=64)
        assert isinstance(inp, DABPlusUdpInput)
        assert inp.host == '0.0.0.0'
        assert inp.port == 9000
        assert inp.bitrate == 64

    def test_create_udp_input_default_port(self):
        """Test UDP input with default port."""
        inp = DABPlusInputFactory.create('udp://localhost', bitrate=48)
        assert isinstance(inp, DABPlusUdpInput)
        assert inp.port == 9000  # Default port

    def test_unsupported_scheme(self):
        """Test unsupported URI scheme."""
        with pytest.raises(ValueError, match="Unsupported input URI scheme"):
            DABPlusInputFactory.create('http://example.com/audio', bitrate=48)

    def test_edi_not_implemented(self):
        """Test EDI scheme (not yet implemented)."""
        with pytest.raises(NotImplementedError, match="EDI input not yet implemented"):
            DABPlusInputFactory.create('edi://localhost:9001', bitrate=48)

    def test_validate_uri_file(self):
        """Test URI validation for file."""
        valid, error = DABPlusInputFactory.validate_uri('file:///tmp/test.dabp')
        assert valid
        assert error is None

    def test_validate_uri_fifo(self):
        """Test URI validation for FIFO."""
        valid, error = DABPlusInputFactory.validate_uri('fifo:///tmp/pipe')
        assert valid
        assert error is None

    def test_validate_uri_udp(self):
        """Test URI validation for UDP."""
        valid, error = DABPlusInputFactory.validate_uri('udp://0.0.0.0:9000')
        assert valid
        assert error is None

    def test_validate_uri_invalid(self):
        """Test URI validation for invalid scheme."""
        valid, error = DABPlusInputFactory.validate_uri('http://example.com')
        assert not valid
        assert 'Unsupported scheme' in error

    def test_get_supported_schemes(self):
        """Test getting supported schemes."""
        schemes = DABPlusInputFactory.get_supported_schemes()
        assert 'file' in schemes
        assert 'fifo' in schemes
        assert 'udp' in schemes
