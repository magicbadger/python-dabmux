"""
EDI output over UDP.

This module implements EDI packet transmission over UDP with optional PFT.
"""
import socket
import struct
from typing import Optional
from dabmux.output.base import DabOutput
from dabmux.edi.protocol import AFPacket
from dabmux.edi.pft import PFTConfig, PFTFragmenter
import structlog

logger = structlog.get_logger(__name__)


class EdiOutput(DabOutput):
    """
    EDI output over UDP.

    Sends AF packets (or PF fragments) via UDP to a specified destination.
    """

    def __init__(
        self,
        dest_addr: str = "127.0.0.1",
        dest_port: int = 12000,
        source_addr: str = "",
        source_port: int = 0,
        enable_pft: bool = False,
        pft_config: Optional[PFTConfig] = None
    ) -> None:
        """
        Initialize EDI output.

        Args:
            dest_addr: Destination IP address
            dest_port: Destination UDP port
            source_addr: Source IP address (for binding)
            source_port: Source UDP port
            enable_pft: Enable PFT fragmentation
            pft_config: PFT configuration (if enable_pft=True)
        """
        super().__init__()
        self.dest_addr = dest_addr
        self.dest_port = dest_port
        self.source_addr = source_addr
        self.source_port = source_port
        self.enable_pft = enable_pft

        # Create socket
        self._socket: Optional[socket.socket] = None

        # PFT fragmenter
        self._pft_fragmenter: Optional[PFTFragmenter] = None
        if enable_pft:
            config = pft_config or PFTConfig()
            self._pft_fragmenter = PFTFragmenter(config)

        # Statistics
        self._packets_sent = 0
        self._bytes_sent = 0
        self._fragments_sent = 0

    def open(self) -> None:
        """Open UDP socket."""
        try:
            # Create UDP socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Bind to source if specified
            if self.source_addr or self.source_port:
                bind_addr = self.source_addr if self.source_addr else "0.0.0.0"
                self._socket.bind((bind_addr, self.source_port))

            # Set socket options
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Enable multicast if destination is multicast
            if self._is_multicast(self.dest_addr):
                # Set multicast TTL
                self._socket.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_MULTICAST_TTL,
                    struct.pack('b', 2)
                )

            self._is_open = True

            logger.info(
                "EDI output opened",
                dest=f"{self.dest_addr}:{self.dest_port}",
                pft=self.enable_pft
            )

        except OSError as e:
            raise RuntimeError(f"Failed to open EDI output: {e}")

    def close(self) -> None:
        """Close UDP socket."""
        if self._socket:
            self._socket.close()
            self._socket = None

        self._is_open = False

        logger.info(
            "EDI output closed",
            packets=self._packets_sent,
            bytes=self._bytes_sent,
            fragments=self._fragments_sent
        )

    def write(self, af_packet: AFPacket) -> None:
        """
        Write an AF packet to the output.

        Args:
            af_packet: AF packet to send

        Raises:
            RuntimeError: If output is not open
        """
        if not self._is_open or not self._socket:
            raise RuntimeError("EDI output not open")

        # Assemble AF packet
        af_data = af_packet.assemble()

        if self.enable_pft and self._pft_fragmenter:
            # Fragment with PFT
            fragments = self._pft_fragmenter.fragment(af_data)

            # Send each fragment
            for fragment in fragments:
                fragment_data = fragment.assemble()
                self._socket.sendto(fragment_data, (self.dest_addr, self.dest_port))
                self._fragments_sent += 1
                self._bytes_sent += len(fragment_data)

            self._packets_sent += 1

        else:
            # Send AF packet directly
            self._socket.sendto(af_data, (self.dest_addr, self.dest_port))
            self._packets_sent += 1
            self._bytes_sent += len(af_data)

    def get_info(self) -> str:
        """
        Get output information string.

        Returns:
            Information string describing this output
        """
        pft_info = " (PFT enabled)" if self.enable_pft else ""
        return f"edi://{self.dest_addr}:{self.dest_port}{pft_info}"

    def _is_multicast(self, addr: str) -> bool:
        """
        Check if an IP address is multicast.

        Args:
            addr: IP address string

        Returns:
            True if multicast (224.0.0.0 - 239.255.255.255)
        """
        try:
            ip_int = struct.unpack('!I', socket.inet_aton(addr))[0]
            # Multicast range: 224.0.0.0/4 (0xE0000000 - 0xEFFFFFFF)
            return (ip_int & 0xF0000000) == 0xE0000000
        except:
            return False

    def get_statistics(self) -> dict:
        """
        Get output statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'packets_sent': self._packets_sent,
            'bytes_sent': self._bytes_sent,
            'fragments_sent': self._fragments_sent,
            'pft_enabled': self.enable_pft
        }
