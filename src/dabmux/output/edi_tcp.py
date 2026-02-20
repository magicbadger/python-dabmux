"""
EDI output over TCP.

Provides reliable EDI transmission over TCP connections.
Per ETSI TS 102 693 Section 6.
"""
import socket
import threading
from typing import Optional, List
from dabmux.output.base import DabOutput
from dabmux.edi.protocol import AFPacket
import structlog

logger = structlog.get_logger(__name__)


class EdiTcpOutput(DabOutput):
    """
    EDI output over TCP.

    Supports both client (connect) and server (listen/accept) modes.
    TCP provides reliable, ordered delivery without needing PFT.
    """

    def __init__(
        self,
        mode: str = "client",  # "client" or "server"
        host: str = "127.0.0.1",
        port: int = 12000,
        listen_backlog: int = 5,
    ) -> None:
        """
        Initialize EDI TCP output.

        Args:
            mode: "client" (connect) or "server" (listen/accept)
            host: Hostname/IP to connect to (client) or bind to (server)
            port: TCP port
            listen_backlog: Listen queue size (server mode only)
        """
        super().__init__()
        self.mode = mode
        self.host = host
        self.port = port
        self.listen_backlog = listen_backlog

        self._socket: Optional[socket.socket] = None
        self._clients: List[socket.socket] = []  # Server mode: connected clients
        self._lock = threading.Lock()
        self._accept_thread: Optional[threading.Thread] = None

        # Statistics
        self._packets_sent = 0
        self._bytes_sent = 0

    def open(self) -> None:
        """Open TCP connection."""
        if self.mode == "client":
            self._open_client()
        elif self.mode == "server":
            self._open_server()
        else:
            raise ValueError(f"Invalid mode: {self.mode} (must be 'client' or 'server')")

    def _open_client(self) -> None:
        """Connect to TCP server."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.host, self.port))
            logger.info("EDI TCP client connected", host=self.host, port=self.port)
        except Exception as e:
            logger.error("Failed to connect EDI TCP client", error=str(e))
            raise

    def _open_server(self) -> None:
        """Start TCP server (listen for connections)."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            self._socket.listen(self.listen_backlog)

            logger.info("EDI TCP server listening", host=self.host, port=self.port)

            # Start accept thread
            self._accept_thread = threading.Thread(
                target=self._accept_loop,
                daemon=True,
                name="EDI-TCP-Accept"
            )
            self._accept_thread.start()
        except Exception as e:
            logger.error("Failed to start EDI TCP server", error=str(e))
            raise

    def _accept_loop(self) -> None:
        """Accept incoming client connections (server mode)."""
        while self._socket:
            try:
                client_sock, client_addr = self._socket.accept()
                with self._lock:
                    self._clients.append(client_sock)
                logger.info("EDI TCP client connected", addr=client_addr)
            except OSError:
                # Socket closed
                break
            except Exception as e:
                logger.debug("Accept loop error", error=str(e))
                break

    def write(self, af_packet: AFPacket) -> None:
        """
        Write AF packet to TCP connection(s).

        Args:
            af_packet: AF packet to send
        """
        if not self.is_open():
            return

        # Assemble AF packet
        packet_data = af_packet.assemble()

        if self.mode == "client":
            self._send_to_socket(self._socket, packet_data)
        elif self.mode == "server":
            # Broadcast to all connected clients
            with self._lock:
                dead_clients = []
                for client in self._clients:
                    if not self._send_to_socket(client, packet_data):
                        dead_clients.append(client)

                # Remove dead clients
                for client in dead_clients:
                    self._clients.remove(client)
                    try:
                        client.close()
                    except:
                        pass

    def _send_to_socket(self, sock: socket.socket, data: bytes) -> bool:
        """
        Send data to socket.

        Args:
            sock: Socket to send to
            data: Data to send

        Returns:
            True if successful, False if connection dead
        """
        try:
            sock.sendall(data)
            self._packets_sent += 1
            self._bytes_sent += len(data)
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            logger.warning("TCP connection lost")
            return False

    def close(self) -> None:
        """Close TCP connection."""
        # Close all client connections (server mode)
        with self._lock:
            for client in self._clients:
                try:
                    client.close()
                except:
                    pass
            self._clients.clear()

        # Close main socket
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None

        # Wait for accept thread to finish
        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=1.0)

    def is_open(self) -> bool:
        """Check if TCP connection is open."""
        return self._socket is not None

    def get_statistics(self) -> dict:
        """
        Get output statistics.

        Returns:
            Dictionary with statistics
        """
        stats = {
            'packets_sent': self._packets_sent,
            'bytes_sent': self._bytes_sent,
            'mode': self.mode,
        }

        if self.mode == "server":
            with self._lock:
                stats['connected_clients'] = len(self._clients)

        return stats

    def get_info(self) -> str:
        """
        Get output information string.

        Returns:
            Information string describing this output
        """
        if self.mode == "client":
            return f"edi-tcp://{self.host}:{self.port} (client)"
        else:
            return f"edi-tcp://{self.host}:{self.port} (server)"
