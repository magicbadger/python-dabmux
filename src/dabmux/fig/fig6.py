"""
FIG Type 6 implementations.

FIG Type 6 contains Conditional Access (CA) information for encrypted services.
This module implements FIG 6/0 and 6/1 for signaling CA systems and services.

Per ETSI EN 300 401 Section 11.
"""
import struct
import structlog
from typing import List
from dabmux.fig.base import FIGBase, FIGRate, FillStatus, FIGPriority
from dabmux.core.mux_elements import DabEnsemble

logger = structlog.get_logger()


class FIG6_0(FIGBase):
    """
    FIG 6/0: Conditional Access Organization.

    Declares which CA (Conditional Access) systems are used in the ensemble.
    Each CA system is identified by a 16-bit CAId (CA System Identifier).

    Byte Structure:
        Header (2 bytes) + CA Org entries (2 bytes each)

        FIG Header:
          Byte 0: Type (3) = 6 | Length (5)
          Byte 1: CN (1) = 0 | OE (1) = 0 | PD (1) = 0 | Extension (5) = 0

        Per CA Organization:
          CAId (16 bits): CA system identifier

    Common CAId values:
        0x5501 - Viaccess
        0x5601 - Nagravision (Kudelski)
        0x5901 - VideoGuard
        0x4A10 - DigitalRadio CA

    Per ETSI EN 300 401 Section 11.2.1.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 6/0 data.

        Args:
            buf: Output buffer
            max_size: Maximum bytes available

        Returns:
            FillStatus indicating bytes written and completion
        """
        status = FillStatus()

        # Check if CA is enabled
        if not self.ensemble.conditional_access or not self.ensemble.conditional_access.enabled:
            status.complete_fig_transmitted = True
            return status

        systems = self.ensemble.conditional_access.systems
        if not systems:
            status.complete_fig_transmitted = True
            return status

        # Calculate required size: 2 (header) + 2 * num_systems
        required = 2 + (len(systems) * 2)
        if max_size < required:
            return status

        # Encode header
        fig_type = 6
        length = (len(systems) * 2) + 1  # Data bytes + byte 1
        cn = 0
        oe = 0
        pd = 0
        extension = 0

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        # Encode CA system IDs
        pos = 2
        for caid in systems:
            struct.pack_into('>H', buf, pos, caid & 0xFFFF)
            pos += 2

        status.num_bytes_written = pos
        status.complete_fig_transmitted = True

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 6/0 transmitted at rate C (once per second)."""
        return FIGRate.C

    def priority(self) -> FIGPriority:
        """FIG 6/0 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 6."""
        return 6

    def fig_extension(self) -> int:
        """Extension 0."""
        return 0


class FIG6_1(FIGBase):
    """
    FIG 6/1: Conditional Access Service.

    Indicates which services use Conditional Access and which CA system
    each service uses.

    Byte Structure:
        Header (2 bytes) + Service entries (variable)

        FIG Header:
          Byte 0: Type (3) = 6 | Length (5)
          Byte 1: CN (1) = 0 | OE (1) = 0 | PD (1) | Extension (5) = 1

        Per Service Entry:
          SId (16 or 32 bits): Service ID (size depends on PD flag)
          CAId (16 bits): CA system identifier for this service

        PD Flag:
          0 = Programme services (16-bit SId)
          1 = Data services (32-bit SId)

    Per ETSI EN 300 401 Section 11.2.2.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        super().__init__()
        self.ensemble = ensemble
        self.service_index = 0

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 6/1 data.

        Supports iterative transmission for multiple services.

        Args:
            buf: Output buffer
            max_size: Maximum bytes available

        Returns:
            FillStatus indicating bytes written and completion
        """
        status = FillStatus()

        # Get services with CA
        ca_services = [s for s in self.ensemble.services if s.ca_system is not None]

        if not ca_services:
            status.complete_fig_transmitted = True
            return status

        if max_size < 4:  # Minimum: header(2) + entry(2 for 16-bit SId)
            return status

        # Reserve space for header
        pos = 2
        services_written = 0

        # Write service entries
        while self.service_index < len(ca_services) and pos < max_size:
            service = ca_services[self.service_index]

            # Determine SId size (data services use 32-bit SId)
            is_data = service.id >= 0x10000
            sid_size = 4 if is_data else 2
            entry_size = sid_size + 2  # SId + CAId

            if pos + entry_size > max_size:
                break  # Not enough space

            # Encode SId
            if is_data:
                struct.pack_into('>I', buf, pos, service.id)
                pos += 4
            else:
                struct.pack_into('>H', buf, pos, service.id)
                pos += 2

            # Encode CAId
            struct.pack_into('>H', buf, pos, service.ca_system & 0xFFFF)
            pos += 2

            services_written += 1
            self.service_index += 1

        if services_written == 0:
            return status

        # Determine PD flag (1 if any data services in this transmission)
        start_idx = self.service_index - services_written
        pd = 1 if any(ca_services[i].id >= 0x10000
                      for i in range(start_idx, self.service_index)) else 0

        # Fill header
        fig_type = 6
        length = (pos - 2) + 1  # Data bytes + byte 1
        cn = 0
        oe = 0
        extension = 1

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        status.num_bytes_written = pos

        # Check if complete
        if self.service_index >= len(ca_services):
            status.complete_fig_transmitted = True
            self.service_index = 0

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 6/1 transmitted at rate C (once per second)."""
        return FIGRate.C

    def priority(self) -> FIGPriority:
        """FIG 6/1 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 6."""
        return 6

    def fig_extension(self) -> int:
        """Extension 1."""
        return 1
