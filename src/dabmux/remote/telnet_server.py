"""
Telnet server for interactive remote control.

Provides a human-friendly command-line interface for DAB multiplexer control.
Complements the ZMQ JSON API with text-based commands.
"""
import asyncio
import shlex
import threading
import structlog
from typing import Dict, Callable, Optional, Any, List, Tuple

logger = structlog.get_logger(__name__)


class TelnetSession:
    """
    Manages an individual telnet client session.

    Each session has isolated state including command history
    and authentication status.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        handlers: Dict[str, Callable],
        session_id: int,
        authenticator: Optional[Any] = None,
        audit_logger: Optional[Any] = None
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.handlers = handlers
        self.session_id = session_id
        self.history: List[str] = []
        self.authenticator = authenticator
        self.audit_logger = audit_logger
        self.authenticated = not (authenticator and authenticator.is_enabled())
        self.addr = writer.get_extra_info('peername')

    async def handle(self) -> None:
        """Main session handler loop."""
        try:
            await self.send_welcome()

            # Authentication prompt if required
            if not self.authenticated:
                await self.send("Password: ")
                try:
                    password = await self.read_command()
                    if password and self.authenticator.verify(password):
                        self.authenticated = True
                        await self.send("✓ Authenticated\n\n")
                    else:
                        await self.send("✗ Authentication failed\nConnection closing...\n")
                        return
                except Exception:
                    await self.send("✗ Authentication error\n")
                    return

            while True:
                await self.send_prompt()

                try:
                    command = await self.read_command()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Error reading command: {e}")
                    break

                if command is None:  # Connection closed
                    break

                command = command.strip()
                if not command:
                    continue

                # Add to history
                self.history.append(command)

                # Handle built-in commands
                if command.lower() in ('quit', 'exit'):
                    await self.send("Goodbye!\n")
                    break
                elif command.lower().startswith('auth '):
                    # Allow re-authentication
                    password = command[5:].strip()
                    if self.authenticator and self.authenticator.verify(password):
                        self.authenticated = True
                        await self.send("✓ Authenticated\n")
                    else:
                        await self.send("✗ Authentication failed\n")
                    continue
                elif command.lower() == 'help':
                    await self.send(self.get_help())
                    continue
                elif command.lower().startswith('help '):
                    cmd = command[5:].strip()
                    await self.send(self.get_command_help(cmd))
                    continue
                elif command.lower() == 'list':
                    await self.send(self.list_commands())
                    continue
                elif command.lower() == 'history':
                    await self.send(self.show_history())
                    continue

                # Check authentication for regular commands
                if not self.authenticated:
                    await self.send("✗ Authentication required\n")
                    continue

                # Execute command
                try:
                    response = await self.execute_command(command)
                    await self.send(response)
                except Exception as e:
                    await self.send(f"✗ Error: {e}\n")

        except Exception as e:
            logger.error(f"Session error: {e}", session_id=self.session_id)
        finally:
            logger.info(f"Session closed", session_id=self.session_id, addr=self.addr)
            self.writer.close()
            await self.writer.wait_closed()

    async def send_welcome(self) -> None:
        """Send welcome message."""
        welcome = (
            "\n"
            "python-dabmux telnet server\n"
            "Type 'help' for available commands, 'quit' to exit\n"
            "\n"
        )
        await self.send(welcome)

    async def send_prompt(self) -> None:
        """Send command prompt."""
        await self.send("> ")

    async def send(self, text: str) -> None:
        """Send text to client."""
        self.writer.write(text.encode('utf-8'))
        await self.writer.drain()

    async def read_command(self) -> Optional[str]:
        """Read command from client."""
        try:
            # Read until newline (handle CR, LF, CRLF)
            data = await asyncio.wait_for(
                self.reader.readuntil(b'\n'),
                timeout=300.0  # 5 minute timeout
            )
            return data.decode('utf-8').rstrip('\r\n')
        except asyncio.TimeoutError:
            logger.info(f"Session timeout", session_id=self.session_id)
            return None
        except asyncio.IncompleteReadError:
            return None

    async def execute_command(self, command: str) -> str:
        """Parse and execute command."""
        import time
        start_time = time.time()

        try:
            cmd_name, args = self.parse_command(command)
        except ValueError as e:
            return f"✗ Invalid command: {e}\n"
        except Exception as e:
            logger.error(f"Command parsing error: {e}", command=command)
            return f"✗ Error: {e}\n"

        try:
            # Look up handler
            handler = self.handlers.get(cmd_name)
            if not handler:
                return f"✗ Unknown command: {cmd_name}\nType 'list' to see available commands\n"

            # Execute handler (blocking call in thread pool)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, handler, args)
            duration_ms = (time.time() - start_time) * 1000

            # Log to audit
            if self.audit_logger:
                self.audit_logger.log_command(
                    source="telnet",
                    client=f"{self.addr[0]}:{self.addr[1]}" if self.addr else "unknown",
                    command=cmd_name,
                    args=args,
                    success=True,
                    duration_ms=duration_ms
                )

            # Format response
            return self.format_response(result)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Command execution error: {e}", command=command)

            # Log to audit
            if self.audit_logger:
                self.audit_logger.log_command(
                    source="telnet",
                    client=f"{self.addr[0]}:{self.addr[1]}" if self.addr else "unknown",
                    command=cmd_name,
                    args=args,
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e)
                )

            return f"✗ Error: {e}\n"

    def parse_command(self, command_line: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse command line into command name and arguments.

        Examples:
            "get statistics" -> ("get_statistics", {})
            "set label comp1 'Text'" -> ("set_label", {"component_uid": "comp1", "text": "Text"})
            "set service pty radio1 10" -> ("set_service_pty", {"service_uid": "radio1", "pty": 10})
        """
        parts = shlex.split(command_line)
        if not parts:
            raise ValueError("Empty command")

        # Map command syntax to handler names
        if len(parts) >= 2 and parts[0] == 'get':
            return self._parse_get_command(parts[1:])
        elif len(parts) >= 2 and parts[0] == 'set':
            return self._parse_set_command(parts[1:])
        elif len(parts) >= 2 and parts[0] == 'trigger':
            return self._parse_trigger_command(parts[1:])
        elif len(parts) >= 2 and parts[0] == 'clear':
            return self._parse_clear_command(parts[1:])
        elif len(parts) >= 1 and parts[0] == 'reload':
            return self._parse_reload_command(parts[1:])
        elif len(parts) >= 1 and parts[0] == 'list':
            return ('list_commands', {})
        else:
            raise ValueError(f"Unknown command format: {command_line}")

    def _parse_get_command(self, parts: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Parse 'get' commands."""
        if not parts:
            raise ValueError("Missing get subcommand")

        subcommand = parts[0]

        if subcommand == 'statistics':
            return ('get_statistics', {})
        elif subcommand == 'label' and len(parts) >= 2:
            return ('get_label', {'component_uid': parts[1]})
        elif subcommand == 'service' and len(parts) >= 3 and parts[1] == 'info':
            return ('get_service_info', {'service_uid': parts[2]})
        elif subcommand == 'input' and len(parts) >= 3 and parts[1] == 'status':
            return ('get_input_status', {'subchannel_uid': parts[2]})
        elif subcommand == 'carousel' and len(parts) >= 3 and parts[1] == 'stats':
            return ('get_carousel_stats', {'component_uid': parts[2]})
        elif subcommand == 'command' and len(parts) >= 3 and parts[1] == 'info':
            return ('get_command_info', {'command': parts[2]})
        elif subcommand == 'all' and len(parts) >= 2:
            if parts[1] == 'services':
                return ('get_all_services', {})
            elif parts[1] == 'components':
                return ('get_all_components', {})
            elif parts[1] == 'subchannels':
                return ('get_all_subchannels', {})

        raise ValueError(f"Unknown get command: {' '.join(parts)}")

    def _parse_set_command(self, parts: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Parse 'set' commands."""
        if not parts:
            raise ValueError("Missing set subcommand")

        subcommand = parts[0]

        if subcommand == 'label' and len(parts) >= 3:
            return ('set_label', {
                'component_uid': parts[1],
                'text': parts[2]
            })
        elif subcommand == 'service' and len(parts) >= 3:
            if parts[1] == 'pty' and len(parts) >= 4:
                return ('set_service_pty', {
                    'service_uid': parts[2],
                    'pty': int(parts[3])
                })
            elif parts[1] == 'language' and len(parts) >= 4:
                return ('set_service_language', {
                    'service_uid': parts[2],
                    'language': int(parts[3])
                })
            elif parts[1] == 'label' and len(parts) >= 4:
                args = {
                    'service_uid': parts[2],
                    'text': parts[3]
                }
                if len(parts) >= 5:
                    args['short_text'] = parts[4]
                return ('set_service_label', args)

        raise ValueError(f"Unknown set command: {' '.join(parts)}")

    def _parse_trigger_command(self, parts: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Parse 'trigger' commands."""
        if parts and parts[0] == 'announcement' and len(parts) >= 4:
            return ('trigger_announcement', {
                'service_id': int(parts[1], 0),  # Support hex with 0x
                'type': parts[2],
                'subchannel_id': int(parts[3])
            })
        raise ValueError(f"Unknown trigger command: {' '.join(parts)}")

    def _parse_clear_command(self, parts: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Parse 'clear' commands."""
        if parts and parts[0] == 'announcement' and len(parts) >= 3:
            return ('clear_announcement', {
                'service_id': int(parts[1], 0),
                'type': parts[2]
            })
        raise ValueError(f"Unknown clear command: {' '.join(parts)}")

    def _parse_reload_command(self, parts: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Parse 'reload' commands."""
        if parts and parts[0] == 'carousel' and len(parts) >= 2:
            return ('reload_carousel', {'component_uid': parts[1]})
        raise ValueError(f"Unknown reload command: {' '.join(parts)}")

    def format_response(self, data: Dict[str, Any]) -> str:
        """Format handler response as human-readable text."""
        if not isinstance(data, dict):
            return f"{data}\n"

        lines = []

        # Check for success flag
        if 'success' in data:
            if data['success']:
                lines.append("✓ Success")
            else:
                lines.append("✗ Failed")

        # Format data fields
        for key, value in data.items():
            if key == 'success':
                continue

            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    if isinstance(item, dict):
                        # Format nested dict
                        lines.append(f"  -")
                        for k, v in item.items():
                            lines.append(f"    {k}: {v}")
                    else:
                        lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"{key}: {value}")

        lines.append("")  # Blank line
        return "\n".join(lines)

    def get_help(self) -> str:
        """Get general help text."""
        return """Available commands:

get statistics                           - Get multiplexer statistics
get label <component_uid>                - Get dynamic label text
get service info <service_uid>           - Get service information
get input status <subchannel_uid>        - Get input source status
get carousel stats <component_uid>       - Get carousel statistics
get all services                         - List all services
get all components                       - List all components
get all subchannels                      - List all subchannels

set label <component_uid> <text>         - Set dynamic label text
set service pty <service_uid> <pty>      - Set service Programme Type (0-31)
set service language <uid> <lang>        - Set service language (0-127)
set service label <uid> <text> [short]   - Set service static label

trigger announcement <svc_id> <type> <subch_id> - Trigger announcement
clear announcement <service_id> <type>           - Clear announcement

reload carousel <component_uid>          - Reload MOT carousel from directory

list                                     - List all commands
help [command]                           - Show help for specific command
history                                  - Show command history
quit / exit                              - Disconnect

"""

    def get_command_help(self, command: str) -> str:
        """Get help for specific command."""
        from dabmux.remote.protocol import COMMANDS

        if command not in COMMANDS:
            return f"Unknown command: {command}\n"

        spec = COMMANDS[command]
        lines = [
            f"\n{command}",
            f"  {spec['description']}\n"
        ]

        if spec['args']:
            lines.append("Arguments:")
            for arg, type_str in spec['args'].items():
                lines.append(f"  {arg} ({type_str})")
            lines.append("")

        if spec['returns']:
            lines.append("Returns:")
            for field, type_str in spec['returns'].items():
                lines.append(f"  {field} ({type_str})")
            lines.append("")

        return "\n".join(lines)

    def list_commands(self) -> str:
        """List all available commands."""
        from dabmux.remote.protocol import COMMANDS

        lines = ["\nAvailable commands:"]
        for cmd_name, spec in sorted(COMMANDS.items()):
            lines.append(f"  {cmd_name:30s} - {spec['description']}")
        lines.append("")

        return "\n".join(lines)

    def show_history(self) -> str:
        """Show command history."""
        if not self.history:
            return "No commands in history\n"

        lines = ["\nCommand history:"]
        for i, cmd in enumerate(self.history, 1):
            lines.append(f"{i:4d}: {cmd}")
        lines.append("")

        return "\n".join(lines)


class TelnetServer:
    """
    Asyncio-based telnet server for interactive control.

    Runs in background thread with asyncio event loop.
    Supports multiple concurrent client sessions.
    """

    def __init__(
        self,
        bind_address: str = "0.0.0.0",
        port: int = 9001,
        authenticator: Optional[Any] = None,
        audit_logger: Optional[Any] = None
    ) -> None:
        self.bind_address = bind_address
        self.port = port
        self.handlers: Dict[str, Callable] = {}
        self.server: Optional[asyncio.Server] = None
        self.thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.running = False
        self.sessions: Dict[int, TelnetSession] = {}
        self.next_session_id = 1
        self.authenticator = authenticator
        self.audit_logger = audit_logger

    def register_handler(self, command: str, handler: Callable) -> None:
        """Register command handler."""
        self.handlers[command] = handler
        logger.debug(f"Registered telnet handler: {command}")

    def start(self) -> None:
        """Start telnet server in background thread."""
        if self.running:
            logger.warning("Telnet server already running")
            return

        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
        logger.info(f"Telnet server starting on {self.bind_address}:{self.port}")

    def stop(self) -> None:
        """Stop telnet server."""
        if not self.running:
            return

        self.running = False

        if self.loop and self.server:
            # Schedule server close
            asyncio.run_coroutine_threadsafe(
                self._stop_server(),
                self.loop
            )

        # Wait for thread
        if self.thread:
            self.thread.join(timeout=5.0)

        logger.info("Telnet server stopped")

    def _run_event_loop(self) -> None:
        """Run asyncio event loop in background thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._start_server())
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Telnet server error: {e}")
        finally:
            self.loop.close()

    async def _start_server(self) -> None:
        """Start asyncio server."""
        self.server = await asyncio.start_server(
            self._handle_client,
            self.bind_address,
            self.port
        )
        self.running = True
        logger.info(f"Telnet server listening on {self.bind_address}:{self.port}")

    async def _stop_server(self) -> None:
        """Stop asyncio server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle new client connection."""
        session_id = self.next_session_id
        self.next_session_id += 1

        addr = writer.get_extra_info('peername')
        logger.info(f"New telnet connection", session_id=session_id, addr=addr)

        session = TelnetSession(
            reader,
            writer,
            self.handlers,
            session_id,
            self.authenticator,
            self.audit_logger
        )
        self.sessions[session_id] = session

        try:
            await session.handle()
        finally:
            if session_id in self.sessions:
                del self.sessions[session_id]
