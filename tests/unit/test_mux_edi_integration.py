"""
Tests for EDI output integration with multiplexer.

Per ETSI TS 102 693.
"""
import pytest
import socket
import time
from dabmux.mux import DabMultiplexer
from dabmux.core.mux_elements import (
    DabEnsemble, DabLabel, EdiOutputConfig
)


class TestMuxEdiIntegration_Disabled:
    """Test multiplexer behavior when EDI is disabled."""

    def test_edi_disabled_by_default(self):
        """Test EDI is not initialized when not configured."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble")
        )

        mux = DabMultiplexer(ensemble)

        assert mux.edi_encoder is None
        assert mux.edi_output is None

    def test_edi_disabled_explicit(self):
        """Test EDI not initialized when explicitly disabled."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(enabled=False)
        )

        mux = DabMultiplexer(ensemble)

        assert mux.edi_encoder is None
        assert mux.edi_output is None

    def test_frame_generation_without_edi(self):
        """Test frame generation works normally without EDI."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble")
        )

        mux = DabMultiplexer(ensemble)
        frame = mux.generate_frame()

        assert frame is not None
        assert frame.sync.fsync in [0x073AB6, 0xF8C549]


class TestMuxEdiIntegration_TcpClient:
    """Test multiplexer EDI integration with TCP client mode."""

    def test_tcp_client_creation(self):
        """Test EDI TCP client output is created and opened."""
        # Start TCP server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        # Create multiplexer with TCP client
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination=f"127.0.0.1:{port}",
                tcp_mode="client"
            )
        )

        mux = DabMultiplexer(ensemble)

        # Accept connection
        client_sock, _ = server_sock.accept()

        # Verify EDI output is initialized
        assert mux.edi_encoder is not None
        assert mux.edi_output is not None
        assert mux.edi_output.is_open()

        # Cleanup
        mux.edi_output.close()
        client_sock.close()
        server_sock.close()

    def test_tcp_client_frame_transmission(self):
        """Test frames are transmitted via TCP client."""
        # Start TCP server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        # Create multiplexer
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination=f"127.0.0.1:{port}",
                tcp_mode="client"
            )
        )

        mux = DabMultiplexer(ensemble)
        client_sock, _ = server_sock.accept()

        # Generate frame (should auto-transmit to EDI)
        frame = mux.generate_frame()

        # Receive EDI packet
        data = client_sock.recv(4096)

        # Verify AF packet received
        assert len(data) > 0
        assert b"AF" in data  # AF sync

        # Cleanup
        mux.edi_output.close()
        client_sock.close()
        server_sock.close()


class TestMuxEdiIntegration_TcpServer:
    """Test multiplexer EDI integration with TCP server mode."""

    def test_tcp_server_creation(self):
        """Test EDI TCP server output is created and listening."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination="127.0.0.1:0",  # Random port
                tcp_mode="server"
            )
        )

        mux = DabMultiplexer(ensemble)

        # Verify EDI server is listening
        assert mux.edi_encoder is not None
        assert mux.edi_output is not None
        assert mux.edi_output.is_open()

        # Cleanup
        mux.edi_output.close()

    def test_tcp_server_broadcast(self):
        """Test frames are broadcast to multiple TCP clients."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination="127.0.0.1:0",
                tcp_mode="server"
            )
        )

        mux = DabMultiplexer(ensemble)
        port = mux.edi_output._socket.getsockname()[1]

        time.sleep(0.1)

        # Connect two clients
        client1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client1.connect(("127.0.0.1", port))

        client2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client2.connect(("127.0.0.1", port))

        time.sleep(0.1)

        # Generate frame
        frame = mux.generate_frame()

        # Both clients should receive
        data1 = client1.recv(4096)
        data2 = client2.recv(4096)

        assert len(data1) > 0
        assert len(data2) > 0
        assert b"AF" in data1
        assert b"AF" in data2

        # Cleanup
        client1.close()
        client2.close()
        mux.edi_output.close()


class TestMuxEdiIntegration_UdpOutput:
    """Test multiplexer EDI integration with UDP output."""

    def test_udp_output_creation(self):
        """Test EDI UDP output is created and opened."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="udp",
                destination="127.0.0.1:12000"
            )
        )

        mux = DabMultiplexer(ensemble)

        # Verify EDI output is initialized
        assert mux.edi_encoder is not None
        assert mux.edi_output is not None
        assert mux.edi_output.is_open()

        # Cleanup
        mux.edi_output.close()

    def test_udp_frame_transmission(self):
        """Test frames are transmitted via UDP."""
        # Create receiver socket
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1.0)
        port = receiver.getsockname()[1]

        # Create multiplexer
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="udp",
                destination=f"127.0.0.1:{port}"
            )
        )

        mux = DabMultiplexer(ensemble)

        # Generate frame
        frame = mux.generate_frame()

        # Receive EDI packet
        data, addr = receiver.recvfrom(4096)

        # Verify AF packet received
        assert len(data) > 0
        assert b"AF" in data

        # Cleanup
        mux.edi_output.close()
        receiver.close()


class TestMuxEdiIntegration_EncoderBehavior:
    """Test EDI encoder integration behavior."""

    def test_encoder_uses_ensemble_config(self):
        """Test EDI encoder is initialized with ensemble."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination="127.0.0.1:12000",
                tcp_mode="server"
            )
        )

        mux = DabMultiplexer(ensemble)

        # Verify encoder has ensemble reference
        assert mux.edi_encoder is not None
        assert mux.edi_encoder.ensemble is ensemble

        # Cleanup
        mux.edi_output.close()

    def test_af_packet_generation(self):
        """Test AF packets are generated from ETI frames."""
        # Start TCP server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination=f"127.0.0.1:{port}",
                tcp_mode="client"
            )
        )

        mux = DabMultiplexer(ensemble)
        client_sock, _ = server_sock.accept()

        # Generate multiple frames
        for i in range(5):
            frame = mux.generate_frame()

        # Give TCP time to flush buffers
        time.sleep(0.1)

        # Receive all data (may need multiple recv calls)
        data = b""
        client_sock.settimeout(0.5)
        try:
            while len(data) < 16384:  # Reasonable upper limit
                chunk = client_sock.recv(8192)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass  # No more data available

        # Count AF syncs (should have at least 5)
        af_count = data.count(b"AF")
        assert af_count >= 5

        # Cleanup
        mux.edi_output.close()
        client_sock.close()
        server_sock.close()


class TestMuxEdiIntegration_Configuration:
    """Test EDI configuration parsing."""

    def test_tcp_mode_defaults(self):
        """Test TCP mode defaults to client."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination="127.0.0.1:12000"
                # tcp_mode not specified, should default to "client"
            )
        )

        # Should not raise (would raise if trying to connect)
        # Just verify config is parsed
        assert ensemble.edi_output.tcp_mode == "client"

    def test_destination_port_parsing(self):
        """Test destination port parsing."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination="127.0.0.1:54321",
                tcp_mode="server"
            )
        )

        mux = DabMultiplexer(ensemble)

        # Verify output was created (port parsing succeeded)
        assert mux.edi_output is not None
        assert mux.edi_output.host == "127.0.0.1"
        assert mux.edi_output.port == 54321

        # Cleanup
        mux.edi_output.close()

    def test_destination_without_port(self):
        """Test destination without port uses default."""
        ensemble = DabEnsemble(
            id=0xCE15,
            ecc=0xE1,
            label=DabLabel(text="Test Ensemble"),
            edi_output=EdiOutputConfig(
                enabled=True,
                protocol="tcp",
                destination="127.0.0.1",  # No port
                tcp_mode="server"
            )
        )

        mux = DabMultiplexer(ensemble)

        # Should use default port 12000
        assert mux.edi_output.port == 12000

        # Cleanup
        mux.edi_output.close()
