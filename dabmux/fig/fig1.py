"""
FIG Type 1 implementations.

FIG Type 1 contains labels for ensemble, services, and components.
This module implements FIG 1/0 (ensemble label) and FIG 1/1 (service labels).
"""
import struct
from dabmux.fig.base import FIGBase, FIGRate, FillStatus
from dabmux.core.mux_elements import DabEnsemble


class FIG1_0(FIGBase):
    """
    FIG 1/0: Ensemble label.

    Provides the ensemble label (name) that receivers display.
    - Ensemble ID
    - Label (16 characters, EBU Latin)
    - Label flag (indicates short label)
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 1/0.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 1/0 data.

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        # Check if we have a label
        if not self.ensemble.label.text:
            status.complete_fig_transmitted = True
            return status

        # FIG 1/0 size: 2 (header) + 2 (EId) + 16 (label) + 2 (flag) = 22 bytes
        if max_size < 22:
            return status

        # FIG header (2 bytes)
        fig_type = 1
        length = 21  # 21 bytes of data after header
        oe = 0       # This ensemble
        charset = 0  # EBU Latin charset
        extension = 0

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (charset << 4) | (oe << 3) | (extension & 0x07)

        # Ensemble ID (2 bytes, big-endian)
        struct.pack_into('>H', buf, 2, self.ensemble.id)

        # Label (16 bytes)
        label_bytes = self.ensemble.label.to_ebu_latin()
        buf[4:20] = label_bytes

        # Short label flag (2 bytes, big-endian)
        struct.pack_into('>H', buf, 20, self.ensemble.label.flag)

        status.num_bytes_written = 22
        status.complete_fig_transmitted = True
        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 1/0 transmitted at rate B (once per second)."""
        return FIGRate.B

    def fig_type(self) -> int:
        """FIG type 1."""
        return 1

    def fig_extension(self) -> int:
        """Extension 0."""
        return 0


class FIG1_1(FIGBase):
    """
    FIG 1/1: Programme service label.

    Provides labels for programme services (audio services).
    - Service ID (16-bit for programme services)
    - Label (16 characters, EBU Latin)
    - Label flag
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 1/1.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble
        self.service_index = 0

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 1/1 data.

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        # Get programme services (16-bit SId)
        programme_services = [s for s in self.ensemble.services if s.id < 0x10000]

        if not programme_services:
            status.complete_fig_transmitted = True
            return status

        if max_size < 2:
            return status

        # Reserve space for header
        pos = 2
        bytes_written_data = 0

        # Each service label: 2 (SId) + 16 (label) + 2 (flag) = 20 bytes
        while self.service_index < len(programme_services):
            service = programme_services[self.service_index]

            # Check if service has a label
            if not service.label.text:
                self.service_index += 1
                continue

            # Need 20 bytes for service label
            if pos + 20 > max_size:
                break

            # Service ID (2 bytes, big-endian)
            struct.pack_into('>H', buf, pos, service.id & 0xFFFF)
            pos += 2

            # Label (16 bytes)
            label_bytes = service.label.to_ebu_latin()
            buf[pos:pos+16] = label_bytes
            pos += 16

            # Short label flag (2 bytes, big-endian)
            struct.pack_into('>H', buf, pos, service.label.flag)
            pos += 2

            bytes_written_data += 20
            self.service_index += 1

        if bytes_written_data == 0:
            return status

        # Fill header
        fig_type = 1
        length = bytes_written_data + 1  # +1 for second header byte
        oe = 0
        charset = 0
        extension = 1

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (charset << 4) | (oe << 3) | (extension & 0x07)

        status.num_bytes_written = 2 + bytes_written_data

        # Check if complete
        if self.service_index >= len(programme_services):
            self.service_index = 0
            status.complete_fig_transmitted = True

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 1/1 transmitted at rate A_B."""
        return FIGRate.A_B

    def fig_type(self) -> int:
        """FIG type 1."""
        return 1

    def fig_extension(self) -> int:
        """Extension 1."""
        return 1


class FIG1_4(FIGBase):
    """
    FIG 1/4: Service component label.

    Provides labels for service components.
    - Service Component ID
    - Label (16 characters, EBU Latin)
    - Label flag
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 1/4.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble
        self.component_index = 0

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 1/4 data.

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        if not self.ensemble.components:
            status.complete_fig_transmitted = True
            return status

        if max_size < 2:
            return status

        # Reserve space for header
        pos = 2
        bytes_written_data = 0

        # Each component label: 1 (PD) + 2 (SCIdS + SubChId) + 16 (label) + 2 (flag) = 21 bytes
        while self.component_index < len(self.ensemble.components):
            component = self.ensemble.components[self.component_index]

            # Check if component has a label
            if not component.label.text:
                self.component_index += 1
                continue

            # Need 21 bytes for component label
            if pos + 21 > max_size:
                break

            # PD flag and SCIdS (1 byte)
            # PD: 0 = programme, 1 = data
            pd = 0  # Assume programme for now
            scids = component.scids & 0x0F

            buf[pos] = (pd << 7) | (scids & 0x0F)
            pos += 1

            # SubChId or other identifier (1 byte)
            buf[pos] = component.subchannel_id & 0xFF
            pos += 1

            # Label (16 bytes)
            label_bytes = component.label.to_ebu_latin()
            buf[pos:pos+16] = label_bytes
            pos += 16

            # Short label flag (2 bytes, big-endian)
            struct.pack_into('>H', buf, pos, component.label.flag)
            pos += 2

            bytes_written_data += 21
            self.component_index += 1

        if bytes_written_data == 0:
            return status

        # Fill header
        fig_type = 1
        length = bytes_written_data + 1
        oe = 0
        charset = 0
        extension = 4

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (charset << 4) | (oe << 3) | (extension & 0x07)

        status.num_bytes_written = 2 + bytes_written_data

        # Check if complete
        if self.component_index >= len(self.ensemble.components):
            self.component_index = 0
            status.complete_fig_transmitted = True

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 1/4 transmitted at rate C (once every 10 seconds)."""
        return FIGRate.C

    def fig_type(self) -> int:
        """FIG type 1."""
        return 1

    def fig_extension(self) -> int:
        """Extension 4."""
        return 4
