"""
Unit tests for ZeroMQ remote control server.
"""
import pytest
import zmq
import json
import time
from dabmux.remote.zmq_server import ZmqServer


class TestZmqServer:
    """Tests for ZMQ server functionality."""

    def test_server_creation(self):
        """Test ZMQ server creation."""
        server = ZmqServer("tcp://127.0.0.1:19000")
        assert server.bind_address == "tcp://127.0.0.1:19000"
        assert server.running is False
        assert len(server.handlers) == 0

    def test_register_handler(self):
        """Test handler registration."""
        server = ZmqServer("tcp://127.0.0.1:19001")

        def test_handler(args):
            return {"result": "ok"}

        server.register_handler("test_command", test_handler)

        assert "test_command" in server.handlers
        assert server.handlers["test_command"] == test_handler

    def test_server_start_stop(self):
        """Test server start and stop."""
        server = ZmqServer("tcp://127.0.0.1:19002")

        server.start()
        assert server.running is True
        assert server.context is not None
        assert server.socket is not None
        assert server.thread is not None

        time.sleep(0.1)  # Give server time to start

        server.stop()
        assert server.running is False

    def test_request_response(self):
        """Test basic request/response."""
        server = ZmqServer("tcp://127.0.0.1:19003")

        # Register test handler
        def echo_handler(args):
            return {"echo": args.get("message", "")}

        server.register_handler("echo", echo_handler)
        server.start()

        time.sleep(0.1)  # Give server time to start

        # Create client
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:19003")

        # Send request
        request = {
            "command": "echo",
            "args": {"message": "Hello, World!"}
        }
        socket.send_string(json.dumps(request))

        # Receive response
        response_json = socket.recv_string()
        response = json.loads(response_json)

        assert response["success"] is True
        assert response["data"]["echo"] == "Hello, World!"

        # Cleanup
        socket.close()
        context.term()
        server.stop()

    def test_unknown_command(self):
        """Test handling of unknown command."""
        server = ZmqServer("tcp://127.0.0.1:19004")
        server.start()

        time.sleep(0.1)

        # Create client
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:19004")

        # Send request with unknown command
        request = {"command": "unknown_command", "args": {}}
        socket.send_string(json.dumps(request))

        # Receive response
        response_json = socket.recv_string()
        response = json.loads(response_json)

        assert response["success"] is False
        assert "Unknown command" in response["error"]

        # Cleanup
        socket.close()
        context.term()
        server.stop()

    def test_missing_command_field(self):
        """Test handling of missing command field."""
        server = ZmqServer("tcp://127.0.0.1:19005")
        server.start()

        time.sleep(0.1)

        # Create client
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:19005")

        # Send request without command field
        request = {"args": {}}
        socket.send_string(json.dumps(request))

        # Receive response
        response_json = socket.recv_string()
        response = json.loads(response_json)

        assert response["success"] is False
        assert "Missing 'command' field" in response["error"]

        # Cleanup
        socket.close()
        context.term()
        server.stop()

    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        server = ZmqServer("tcp://127.0.0.1:19006")
        server.start()

        time.sleep(0.1)

        # Create client
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:19006")

        # Send invalid JSON
        socket.send_string("{ invalid json")

        # Receive response
        response_json = socket.recv_string()
        response = json.loads(response_json)

        assert response["success"] is False
        assert "Invalid JSON" in response["error"]

        # Cleanup
        socket.close()
        context.term()
        server.stop()

    def test_handler_exception(self):
        """Test handling of exceptions in handler."""
        server = ZmqServer("tcp://127.0.0.1:19007")

        # Register handler that raises exception
        def failing_handler(args):
            raise ValueError("Test error")

        server.register_handler("failing", failing_handler)
        server.start()

        time.sleep(0.1)

        # Create client
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:19007")

        # Send request
        request = {"command": "failing", "args": {}}
        socket.send_string(json.dumps(request))

        # Receive response
        response_json = socket.recv_string()
        response = json.loads(response_json)

        assert response["success"] is False
        assert "Test error" in response["error"]

        # Cleanup
        socket.close()
        context.term()
        server.stop()

    def test_multiple_requests(self):
        """Test handling of multiple requests."""
        server = ZmqServer("tcp://127.0.0.1:19008")

        # Register counter handler
        counter = {"count": 0}

        def counter_handler(args):
            counter["count"] += 1
            return {"count": counter["count"]}

        server.register_handler("count", counter_handler)
        server.start()

        time.sleep(0.1)

        # Create client
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:19008")

        # Send multiple requests
        for i in range(5):
            request = {"command": "count", "args": {}}
            socket.send_string(json.dumps(request))

            response_json = socket.recv_string()
            response = json.loads(response_json)

            assert response["success"] is True
            assert response["data"]["count"] == i + 1

        # Cleanup
        socket.close()
        context.term()
        server.stop()
