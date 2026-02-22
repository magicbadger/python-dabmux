"""
Unit tests for telnet server.
"""
import pytest
import asyncio
import socket
from unittest.mock import Mock, AsyncMock
from dabmux.remote.telnet_server import TelnetServer, TelnetSession


class TestTelnetSession:
    """Tests for TelnetSession class."""

    def create_mock_reader_writer(self):
        """Create mock StreamReader and StreamWriter."""
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = AsyncMock(spec=asyncio.StreamWriter)
        writer.get_extra_info = Mock(return_value=('127.0.0.1', 12345))
        return reader, writer

    def test_session_creation(self):
        """Test session creation."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        assert session.session_id == 1
        assert session.handlers == handlers
        assert session.authenticated is True  # No auth in Phase 3
        assert session.history == []

    def test_parse_get_statistics(self):
        """Test parsing 'get statistics' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("get statistics")
        assert cmd_name == "get_statistics"
        assert args == {}

    def test_parse_get_label(self):
        """Test parsing 'get label' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("get label comp1")
        assert cmd_name == "get_label"
        assert args == {"component_uid": "comp1"}

    def test_parse_set_label(self):
        """Test parsing 'set label' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("set label comp1 'Now Playing'")
        assert cmd_name == "set_label"
        assert args == {"component_uid": "comp1", "text": "Now Playing"}

    def test_parse_set_service_pty(self):
        """Test parsing 'set service pty' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("set service pty radio1 10")
        assert cmd_name == "set_service_pty"
        assert args == {"service_uid": "radio1", "pty": 10}

    def test_parse_set_service_language(self):
        """Test parsing 'set service language' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("set service language radio1 15")
        assert cmd_name == "set_service_language"
        assert args == {"service_uid": "radio1", "language": 15}

    def test_parse_set_service_label(self):
        """Test parsing 'set service label' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("set service label radio1 'Test Radio' 'Test'")
        assert cmd_name == "set_service_label"
        assert args == {"service_uid": "radio1", "text": "Test Radio", "short_text": "Test"}

    def test_parse_get_all_services(self):
        """Test parsing 'get all services' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("get all services")
        assert cmd_name == "get_all_services"
        assert args == {}

    def test_parse_trigger_announcement(self):
        """Test parsing 'trigger announcement' command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        cmd_name, args = session.parse_command("trigger announcement 0x5001 alarm 0")
        assert cmd_name == "trigger_announcement"
        assert args == {"service_id": 0x5001, "type": "alarm", "subchannel_id": 0}

    def test_parse_invalid_command(self):
        """Test parsing invalid command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        with pytest.raises(ValueError, match="Unknown command format"):
            session.parse_command("invalid command")

    def test_format_simple_response(self):
        """Test formatting simple response."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        result = session.format_response({"success": True, "value": 42})
        assert "✓ Success" in result
        assert "value: 42" in result

    def test_format_list_response(self):
        """Test formatting list response."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        result = session.format_response({
            "services": [
                {"uid": "radio1", "id": 0x5001},
                {"uid": "radio2", "id": 0x5002}
            ]
        })
        assert "services:" in result
        assert "uid: radio1" in result
        assert "uid: radio2" in result

    @pytest.mark.asyncio
    async def test_execute_command_success(self):
        """Test executing command successfully."""
        reader, writer = self.create_mock_reader_writer()

        def mock_handler(args):
            return {"success": True, "value": 123}

        handlers = {"get_statistics": mock_handler}
        session = TelnetSession(reader, writer, handlers, 1)

        response = await session.execute_command("get statistics")
        assert "✓ Success" in response
        assert "value: 123" in response

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self):
        """Test executing unknown command."""
        reader, writer = self.create_mock_reader_writer()
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        response = await session.execute_command("get statistics")
        assert "✗ Unknown command" in response

    @pytest.mark.asyncio
    async def test_execute_command_handler_exception(self):
        """Test handler raising exception."""
        reader, writer = self.create_mock_reader_writer()

        def mock_handler(args):
            raise ValueError("Test error")

        handlers = {"get_statistics": mock_handler}
        session = TelnetSession(reader, writer, handlers, 1)

        response = await session.execute_command("get statistics")
        assert "✗ Error: Test error" in response


class TestTelnetServer:
    """Tests for TelnetServer class."""

    def test_server_creation(self):
        """Test server creation."""
        server = TelnetServer("0.0.0.0", 9001)
        assert server.bind_address == "0.0.0.0"
        assert server.port == 9001
        assert server.handlers == {}
        assert server.running is False

    def test_register_handler(self):
        """Test registering handler."""
        server = TelnetServer()
        handler = Mock()
        server.register_handler("test_cmd", handler)
        assert server.handlers["test_cmd"] == handler

    def test_server_lifecycle(self):
        """Test server start/stop lifecycle."""
        server = TelnetServer("127.0.0.1", 19001)  # Use high port to avoid conflicts

        # Start server
        server.start()
        import time
        time.sleep(0.5)  # Give server time to start

        assert server.running is True
        assert server.thread is not None
        assert server.thread.is_alive()

        # Stop server
        server.stop()
        time.sleep(0.5)  # Give server time to stop

        assert server.running is False

    @pytest.mark.asyncio
    async def test_connection_and_command(self):
        """Test connecting and sending command."""
        server = TelnetServer("127.0.0.1", 19002)

        # Register test handler
        def test_handler(args):
            return {"success": True, "test": "value"}

        server.register_handler("get_statistics", test_handler)

        # Start server
        server.start()
        await asyncio.sleep(0.5)

        try:
            # Connect with raw socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", 19002))
            sock.settimeout(5.0)

            # Read welcome message
            welcome = sock.recv(2048).decode('utf-8')
            assert "python-dabmux telnet server" in welcome

            # Read initial prompt (sent separately)
            prompt = sock.recv(1024).decode('utf-8')
            assert "> " in prompt

            # Send command
            sock.sendall(b"get statistics\n")

            # Read response (includes new prompt)
            response = b""
            for _ in range(10):  # Read multiple chunks
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                # Stop when we see the next prompt
                if b"> " in response:
                    break

            response_str = response.decode('utf-8')
            assert "✓ Success" in response_str
            assert "test: value" in response_str

            # Send quit
            sock.sendall(b"quit\n")
            goodbye = sock.recv(1024).decode('utf-8')
            assert "Goodbye" in goodbye

            sock.close()

        finally:
            server.stop()
            await asyncio.sleep(0.5)

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """Test multiple simultaneous connections."""
        server = TelnetServer("127.0.0.1", 19003)

        def test_handler(args):
            return {"success": True}

        server.register_handler("get_statistics", test_handler)

        server.start()
        await asyncio.sleep(0.5)

        try:
            # Create two connections
            sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock1.connect(("127.0.0.1", 19003))
            sock1.settimeout(5.0)

            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.connect(("127.0.0.1", 19003))
            sock2.settimeout(5.0)

            # Read welcomes
            welcome1 = sock1.recv(1024).decode('utf-8')
            welcome2 = sock2.recv(1024).decode('utf-8')

            assert "python-dabmux" in welcome1
            assert "python-dabmux" in welcome2

            # Close connections
            sock1.sendall(b"quit\n")
            sock2.sendall(b"quit\n")

            sock1.close()
            sock2.close()

        finally:
            server.stop()
            await asyncio.sleep(0.5)

    def test_help_command(self):
        """Test built-in help command."""
        reader, writer = Mock(), Mock()
        writer.get_extra_info = Mock(return_value=('127.0.0.1', 12345))
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        help_text = session.get_help()
        assert "get statistics" in help_text
        assert "set label" in help_text
        assert "quit" in help_text

    def test_list_commands(self):
        """Test list commands."""
        reader, writer = Mock(), Mock()
        writer.get_extra_info = Mock(return_value=('127.0.0.1', 12345))
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        list_text = session.list_commands()
        assert "Available commands:" in list_text
        assert "get_statistics" in list_text

    def test_command_history(self):
        """Test command history."""
        reader, writer = Mock(), Mock()
        writer.get_extra_info = Mock(return_value=('127.0.0.1', 12345))
        handlers = {}
        session = TelnetSession(reader, writer, handlers, 1)

        session.history.append("get statistics")
        session.history.append("set label comp1 'text'")

        history_text = session.show_history()
        assert "get statistics" in history_text
        assert "set label comp1 'text'" in history_text
