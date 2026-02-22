"""
ZeroMQ Remote Control Server.

Provides request/reply interface for runtime control.
"""
import zmq
import json
import time
import threading
import structlog
from typing import Dict, Any, Optional, Callable

logger = structlog.get_logger()


class ZmqServer:
    """
    ZeroMQ server for remote control.

    Implements REP (reply) socket pattern for request/response.
    Runs in separate thread to avoid blocking multiplexer.
    """

    def __init__(
        self,
        bind_address: str = "tcp://*:9000",
        authenticator: Optional[Any] = None,
        audit_logger: Optional[Any] = None
    ) -> None:
        """
        Initialize ZMQ server.

        Args:
            bind_address: ZMQ bind address (default: tcp://*:9000)
            authenticator: Optional Authenticator instance
            audit_logger: Optional AuditLogger instance
        """
        self.bind_address = bind_address
        self.context: Optional[zmq.Context] = None
        self.socket: Optional[zmq.Socket] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

        # Authentication and audit
        self.authenticator = authenticator
        self.audit_logger = audit_logger

        # Command handlers registry
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, command: str, handler: Callable) -> None:
        """
        Register command handler.

        Args:
            command: Command name (e.g., "get_label", "set_announcement")
            handler: Callable that takes dict args and returns dict result
        """
        self.handlers[command] = handler
        logger.debug("Registered ZMQ handler", command=command)

    def start(self) -> None:
        """Start ZMQ server in background thread."""
        if self.running:
            logger.warning("ZMQ server already running")
            return

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(self.bind_address)

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        logger.info("ZMQ server started", address=self.bind_address)

    def stop(self) -> None:
        """Stop ZMQ server and cleanup."""
        if not self.running:
            return

        self.running = False

        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()

        if self.thread:
            self.thread.join(timeout=5.0)

        logger.info("ZMQ server stopped")

    def _run(self) -> None:
        """Main server loop (runs in background thread)."""
        logger.info("ZMQ server loop started")

        while self.running:
            try:
                # Wait for request with timeout
                if self.socket.poll(1000):  # 1 second timeout
                    request_json = self.socket.recv_string()

                    # Parse request
                    try:
                        request = json.loads(request_json)
                        response = self._handle_request(request)
                    except json.JSONDecodeError:
                        response = {
                            "success": False,
                            "error": "Invalid JSON"
                        }
                    except Exception as e:
                        logger.error("Error handling request", error=str(e))
                        response = {
                            "success": False,
                            "error": str(e)
                        }

                    # Send response
                    response_json = json.dumps(response)
                    self.socket.send_string(response_json)

            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    # Context terminated, exit gracefully
                    break
                logger.error("ZMQ error in server loop", error=str(e))

        logger.info("ZMQ server loop exited")

    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming request.

        Args:
            request: Request dict with 'command', optional 'auth', and optional 'args'

        Returns:
            Response dict with 'success' and optional 'data' or 'error'
        """
        command = request.get("command")
        start_time = time.time()

        if not command:
            return {
                "success": False,
                "error": "Missing 'command' field"
            }

        # Check authentication
        if self.authenticator and self.authenticator.is_enabled():
            auth = request.get("auth", "")
            if not self.authenticator.verify(auth):
                if self.audit_logger:
                    self.audit_logger.log_command(
                        source="zmq",
                        client="unknown",  # ZMQ doesn't expose client address easily
                        command=command,
                        args={},
                        success=False,
                        duration_ms=(time.time() - start_time) * 1000,
                        error="Authentication failed"
                    )
                return {
                    "success": False,
                    "error": "Authentication failed"
                }

        if command not in self.handlers:
            return {
                "success": False,
                "error": f"Unknown command: {command}"
            }

        # Call handler
        handler = self.handlers[command]
        args = request.get("args", {})

        try:
            result = handler(args)
            duration_ms = (time.time() - start_time) * 1000

            # Log to audit
            if self.audit_logger:
                self.audit_logger.log_command(
                    source="zmq",
                    client="unknown",
                    command=command,
                    args=args,
                    success=True,
                    duration_ms=duration_ms
                )

            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("Handler error", command=command, error=str(e))

            # Log to audit
            if self.audit_logger:
                self.audit_logger.log_command(
                    source="zmq",
                    client="unknown",
                    command=command,
                    args=args,
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e)
                )

            return {
                "success": False,
                "error": str(e)
            }
