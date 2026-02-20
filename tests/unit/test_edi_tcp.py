"""
Tests for EDI TCP output.

Per ETSI TS 102 693 Section 6.
"""
import pytest
import socket
import threading
import time
from dabmux.output.edi_tcp import EdiTcpOutput
from dabmux.edi.protocol import AFPacket


class TestEdiTcpOutput_ClientMode:
    """Test EDI TCP output in client mode."""

    def test_client_creation(self):
        """Test creating TCP client output."""
        output = EdiTcpOutput(mode="client", host="127.0.0.1", port=12345)

        assert output.mode == "client"
        assert output.host == "127.0.0.1"
        assert output.port == 12345
        assert not output.is_open()

    def test_client_connection(self):
        """Test client connection to server."""
        # Start a simple TCP server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))  # Random port
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        # Connect client
        output = EdiTcpOutput(mode="client", host="127.0.0.1", port=port)
        output.open()

        assert output.is_open()

        # Accept connection
        client_sock, _ = server_sock.accept()

        # Cleanup
        output.close()
        client_sock.close()
        server_sock.close()

    def test_client_send_packet(self):
        """Test sending AF packet via TCP client."""
        # Start server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        # Connect client
        output = EdiTcpOutput(mode="client", host="127.0.0.1", port=port)
        output.open()

        # Accept connection
        client_sock, _ = server_sock.accept()

        # Send packet
        af_packet = AFPacket(seq=123, payload=b"test_payload")
        output.write(af_packet)

        # Receive on server side
        data = client_sock.recv(1024)
        assert len(data) > 0
        assert b"AF" in data  # AF sync

        # Cleanup
        output.close()
        client_sock.close()
        server_sock.close()

    def test_client_connection_error(self):
        """Test client connection error handling."""
        # Try to connect to non-existent server
        output = EdiTcpOutput(mode="client", host="127.0.0.1", port=1)  # Port 1 unlikely to be open

        with pytest.raises(Exception):
            output.open()


class TestEdiTcpOutput_ServerMode:
    """Test EDI TCP output in server mode."""

    def test_server_creation(self):
        """Test creating TCP server output."""
        output = EdiTcpOutput(mode="server", host="127.0.0.1", port=12345)

        assert output.mode == "server"
        assert output.host == "127.0.0.1"
        assert output.port == 12345
        assert not output.is_open()

    def test_server_listen(self):
        """Test server listen mode."""
        output = EdiTcpOutput(mode="server", host="127.0.0.1", port=0)  # Random port
        output.open()

        assert output.is_open()

        # Get the actual port
        port = output._socket.getsockname()[1]
        assert port > 0

        # Cleanup
        output.close()

    def test_server_accept_client(self):
        """Test server accepting client connections."""
        output = EdiTcpOutput(mode="server", host="127.0.0.1", port=0)
        output.open()
        port = output._socket.getsockname()[1]

        # Give accept thread time to start
        time.sleep(0.1)

        # Connect client
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))

        # Give time for accept
        time.sleep(0.1)

        # Check client was accepted
        assert len(output._clients) == 1

        # Cleanup
        client_sock.close()
        output.close()

    def test_server_broadcast_to_clients(self):
        """Test server broadcasting to multiple clients."""
        output = EdiTcpOutput(mode="server", host="127.0.0.1", port=0)
        output.open()
        port = output._socket.getsockname()[1]

        time.sleep(0.1)

        # Connect two clients
        client1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client1.connect(("127.0.0.1", port))

        client2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client2.connect(("127.0.0.1", port))

        time.sleep(0.1)

        # Send packet
        af_packet = AFPacket(seq=456, payload=b"broadcast_test")
        output.write(af_packet)

        # Both clients should receive
        data1 = client1.recv(1024)
        data2 = client2.recv(1024)

        assert len(data1) > 0
        assert len(data2) > 0
        assert data1 == data2

        # Cleanup
        client1.close()
        client2.close()
        output.close()

    def test_server_remove_dead_client(self):
        """Test server removes disconnected clients."""
        output = EdiTcpOutput(mode="server", host="127.0.0.1", port=0)
        output.open()
        port = output._socket.getsockname()[1]

        time.sleep(0.1)

        # Connect client
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))

        time.sleep(0.1)
        assert len(output._clients) == 1

        # Close client
        client_sock.close()

        time.sleep(0.1)

        # Send multiple packets (might take a few sends to detect dead connection)
        for i in range(5):
            af_packet = AFPacket(seq=789 + i, payload=f"dead_client_test_{i}".encode())
            output.write(af_packet)
            time.sleep(0.05)

        # Dead client should be removed (eventually)
        # Note: TCP might buffer some sends before detecting the closed connection
        assert len(output._clients) == 0

        # Cleanup
        output.close()


class TestEdiTcpOutput_Statistics:
    """Test EDI TCP output statistics."""

    def test_statistics_client(self):
        """Test statistics in client mode."""
        # Start server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        # Connect client
        output = EdiTcpOutput(mode="client", host="127.0.0.1", port=port)
        output.open()
        client_sock, _ = server_sock.accept()

        # Send packet
        af_packet = AFPacket(seq=1, payload=b"stats_test")
        output.write(af_packet)

        # Check statistics
        stats = output.get_statistics()
        assert stats['packets_sent'] == 1
        assert stats['bytes_sent'] > 0
        assert stats['mode'] == 'client'

        # Cleanup
        output.close()
        client_sock.close()
        server_sock.close()

    def test_statistics_server(self):
        """Test statistics in server mode."""
        output = EdiTcpOutput(mode="server", host="127.0.0.1", port=0)
        output.open()
        port = output._socket.getsockname()[1]

        time.sleep(0.1)

        # Connect client
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))

        time.sleep(0.1)

        # Check statistics
        stats = output.get_statistics()
        assert stats['mode'] == 'server'
        assert stats['connected_clients'] == 1

        # Cleanup
        client_sock.close()
        output.close()


class TestEdiTcpOutput_ErrorHandling:
    """Test EDI TCP output error handling."""

    def test_invalid_mode(self):
        """Test invalid mode raises error."""
        output = EdiTcpOutput(mode="invalid")

        with pytest.raises(ValueError, match="Invalid mode"):
            output.open()

    def test_write_when_closed(self):
        """Test writing when connection is closed."""
        output = EdiTcpOutput(mode="client")

        # Write should not raise, just return silently
        af_packet = AFPacket(seq=0, payload=b"test")
        output.write(af_packet)  # Should not crash

    def test_double_close(self):
        """Test closing already closed connection."""
        # Start server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        output = EdiTcpOutput(mode="client", host="127.0.0.1", port=port)
        output.open()
        client_sock, _ = server_sock.accept()

        output.close()
        output.close()  # Should not crash

        # Cleanup
        client_sock.close()
        server_sock.close()


class TestEdiTcpOutput_ThreadSafety:
    """Test thread safety of server mode."""

    def test_concurrent_writes(self):
        """Test concurrent writes from multiple threads."""
        output = EdiTcpOutput(mode="server", host="127.0.0.1", port=0)
        output.open()
        port = output._socket.getsockname()[1]

        time.sleep(0.1)

        # Connect client
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))

        time.sleep(0.1)

        # Write from multiple threads
        def write_packets():
            for i in range(10):
                af_packet = AFPacket(seq=i, payload=f"packet_{i}".encode())
                output.write(af_packet)

        threads = [threading.Thread(target=write_packets) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check statistics
        stats = output.get_statistics()
        assert stats['packets_sent'] == 30  # 3 threads * 10 packets

        # Cleanup
        client_sock.close()
        output.close()
