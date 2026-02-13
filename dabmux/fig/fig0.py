"""
FIG Type 0 implementations.

FIG Type 0 contains multiplex configuration information (MCI).
This module implements the most important FIG 0 variants.
"""
import struct
from typing import List
from dabmux.fig.base import FIGBase, FIGRate, FillStatus
from dabmux.core.mux_elements import DabEnsemble, DabSubchannel, DabService, ProtectionForm


class FIG0_0(FIGBase):
    """
    FIG 0/0: Ensemble information.

    Provides basic ensemble information including:
    - Ensemble ID (EId)
    - Change flags
    - Alarm flag
    - CIF counter

    This FIG must be transmitted every 96ms (once per transmission frame in Mode I).
    """

    def __init__(self, ensemble: DabEnsemble, current_frame: int = 0) -> None:
        """
        Initialize FIG 0/0.

        Args:
            ensemble: Ensemble configuration
            current_frame: Current frame number
        """
        super().__init__()
        self.ensemble = ensemble
        self.current_frame = current_frame

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 0/0 data.

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        if max_size < 6:
            return status

        # FIG header (2 bytes)
        # Byte 0: FIG type (3 bits) | Length (5 bits)
        # Byte 1: CN | OE | PD | Extension
        fig_type = 0  # Type 0
        length = 5    # 5 bytes of data after header
        cn = 0        # Current/Next: 0 = current
        oe = 0        # Other Ensemble: 0 = this ensemble
        pd = 0        # Programme/Data: 0 = programme services

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (cn << 7) | (oe << 6) | (pd << 5) | 0  # Extension = 0

        # FIG 0/0 data (4 bytes)
        # EId (2 bytes, big-endian)
        struct.pack_into('>H', buf, 2, self.ensemble.id)

        # Change flags and CIF counter (2 bytes)
        change = 0       # Change flags: 00 = no change
        al = 1 if self.ensemble.alarm_flag else 0  # Alarm flag
        cif_count = self.current_frame % 5000  # CIF counter (0-4999)
        cif_count_high = (cif_count // 250) % 20  # High 5 bits
        cif_count_low = cif_count % 250            # Low 8 bits

        buf[4] = (cif_count_high << 3) | (al << 2) | (change & 0x03)
        buf[5] = cif_count_low & 0xFF

        status.num_bytes_written = 6
        status.complete_fig_transmitted = True
        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 0/0 has special rate (every 96ms)."""
        return FIGRate.FIG0_0

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 0."""
        return 0


class FIG0_1(FIGBase):
    """
    FIG 0/1: Basic sub-channel organization.

    Provides information about sub-channels:
    - Sub-channel ID
    - Start address
    - Protection level
    - Size

    Supports both UEP (Unequal Error Protection) and EEP (Equal Error Protection).
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 0/1.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble
        self.subchannel_index = 0

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 0/1 data.

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        if max_size < 2:
            return status

        # Start position for FIG header
        start_pos = 0

        # Reserve space for header (will be filled later)
        pos = 2
        bytes_written_data = 0

        # Iterate through subchannels
        subchannels = self.ensemble.subchannels
        if not subchannels:
            return status

        while self.subchannel_index < len(subchannels):
            subchannel = subchannels[self.subchannel_index]

            # Determine if UEP or EEP
            is_uep = subchannel.protection.form == ProtectionForm.UEP

            # UEP = 3 bytes, EEP = 4 bytes
            entry_size = 3 if is_uep else 4

            if pos + entry_size > max_size:
                # No more space
                break

            # Write subchannel entry
            if is_uep:
                # Short form (UEP): 3 bytes
                # Byte 0: SubChId (6 bits) | Start Address high (2 bits)
                # Byte 1: Start Address low (8 bits)
                # Byte 2: Table Index (6 bits) | Table Switch (1) | Form (1)
                start_addr = subchannel.start_address
                table_index = subchannel.protection.level & 0x3F
                table_switch = 0  # Always 0 for now
                form = 0  # 0 = short form (UEP)

                buf[pos] = (subchannel.id << 2) | ((start_addr >> 8) & 0x03)
                buf[pos + 1] = start_addr & 0xFF
                buf[pos + 2] = (table_index << 2) | (table_switch << 1) | form

                pos += 3
                bytes_written_data += 3
            else:
                # Long form (EEP): 4 bytes
                # Byte 0: SubChId (6 bits) | Start Address high (2 bits)
                # Byte 1: Start Address low (8 bits)
                # Byte 2: Sub-channel size high (2) | Protection level (2) | Option (3) | Form (1)
                # Byte 3: Sub-channel size low (8 bits)
                start_addr = subchannel.start_address
                size_cu = subchannel.get_size_cu()
                protection_level = subchannel.protection.level
                option = subchannel.protection.eep.get_option() if subchannel.protection.eep else 0
                form = 1  # 1 = long form (EEP)

                buf[pos] = (subchannel.id << 2) | ((start_addr >> 8) & 0x03)
                buf[pos + 1] = start_addr & 0xFF
                buf[pos + 2] = ((size_cu >> 8) & 0x03) << 6 | (protection_level & 0x03) << 4 | (option & 0x07) << 1 | form
                buf[pos + 3] = size_cu & 0xFF

                pos += 4
                bytes_written_data += 4

            self.subchannel_index += 1

        # Check if we wrote anything
        if bytes_written_data == 0:
            return status

        # Fill header
        fig_type = 0
        length = bytes_written_data + 1  # +1 for second header byte
        cn = 0
        oe = 0
        pd = 0  # Programme services
        extension = 1  # Extension 1

        buf[start_pos] = (fig_type << 5) | (length & 0x1F)
        buf[start_pos + 1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        status.num_bytes_written = 2 + bytes_written_data

        # Check if we've transmitted all subchannels
        if self.subchannel_index >= len(subchannels):
            status.complete_fig_transmitted = True
            self.subchannel_index = 0  # Reset for next cycle

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 0/1 transmitted at rate B (once per second)."""
        return FIGRate.B

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 1."""
        return 1


class FIG0_2(FIGBase):
    """
    FIG 0/2: Basic service and service component definition.

    Provides information about services and their components:
    - Service ID
    - Number of components
    - Component types (audio/data/packet)
    - Sub-channel assignments

    Separates programme and data services.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 0/2.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble
        self.service_index = 0
        self.transmitting_audio = True  # Alternate between audio and data services

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 0/2 data.

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        if max_size < 2:
            return status

        # Separate programme and data services
        services = self._get_current_service_list()

        if not services:
            status.complete_fig_transmitted = True
            return status

        # Reserve space for header
        pos = 2
        bytes_written_data = 0

        while self.service_index < len(services):
            service = services[self.service_index]

            # Count components for this service
            components = [c for c in self.ensemble.components if c.service_id == service.id]
            num_components = len(components)

            if num_components == 0:
                self.service_index += 1
                continue

            # Calculate size needed
            # Service header: 3 or 5 bytes (depending on SId size)
            # Each component: 2 bytes
            is_programme = self.transmitting_audio
            service_header_size = 3 if is_programme else 5
            total_size = service_header_size + (num_components * 2)

            if pos + total_size > max_size:
                break

            # Write service header
            if is_programme:
                # Programme service (16-bit SId): 3 bytes
                # Bytes 0-1: SId (16-bit, big-endian)
                # Byte 2: Local flag (1) | CAId (3) | NbServiceComp (4)
                struct.pack_into('>H', buf, pos, service.id & 0xFFFF)
                buf[pos + 2] = (0 << 7) | (0 << 4) | (num_components & 0x0F)  # Local=0, CAId=0
                pos += 3
                bytes_written_data += 3
            else:
                # Data service (32-bit SId): 5 bytes
                # Bytes 0-3: SId (32-bit, big-endian)
                # Byte 4: Local flag (1) | CAId (3) | NbServiceComp (4)
                struct.pack_into('>I', buf, pos, service.id)
                buf[pos + 4] = (0 << 7) | (0 << 4) | (num_components & 0x0F)
                pos += 5
                bytes_written_data += 5

            # Write components
            for component in components:
                # Component: 2 bytes
                # Byte 0: TMid (2) | ASCTy/DSCTy (6)
                # Byte 1: PS (1) | CA (1) | SubChId (6)
                tmid = 0  # Stream mode (MSC stream)
                ascty = 0  # Audio Service Component Type
                ps = 1    # Primary/Secondary: 1 = primary
                ca = 0    # CA flag: 0 = not conditional access

                buf[pos] = (tmid << 6) | (ascty & 0x3F)
                buf[pos + 1] = (ps << 7) | (ca << 6) | (component.subchannel_id & 0x3F)
                pos += 2
                bytes_written_data += 2

            self.service_index += 1

        if bytes_written_data == 0:
            return status

        # Fill header
        fig_type = 0
        length = bytes_written_data + 1
        cn = 0
        oe = 0
        pd = 0 if self.transmitting_audio else 1  # 0 = programme, 1 = data
        extension = 2

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        status.num_bytes_written = 2 + bytes_written_data

        # Check if complete
        if self.service_index >= len(services):
            self.service_index = 0

            # Alternate between audio and data
            if not self._get_other_service_list():
                # No services of other type, mark complete
                status.complete_fig_transmitted = True
            else:
                # Switch to other type
                self.transmitting_audio = not self.transmitting_audio
                if self.transmitting_audio:
                    # Completed full cycle
                    status.complete_fig_transmitted = True

        return status

    def _get_current_service_list(self) -> List[DabService]:
        """Get current service list (audio or data)."""
        if self.transmitting_audio:
            return [s for s in self.ensemble.services if s.id < 0x10000]  # Programme services
        else:
            return [s for s in self.ensemble.services if s.id >= 0x10000]  # Data services

    def _get_other_service_list(self) -> List[DabService]:
        """Get other service list (opposite of current)."""
        if not self.transmitting_audio:
            return [s for s in self.ensemble.services if s.id < 0x10000]
        else:
            return [s for s in self.ensemble.services if s.id >= 0x10000]

    def repetition_rate(self) -> FIGRate:
        """FIG 0/2 transmitted at rate A_B."""
        return FIGRate.A_B

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 2."""
        return 2


class FIG0_5(FIGBase):
    """
    FIG 0/5: Service component language.

    Specifies the language used by each service component.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """Initialize FIG 0/5."""
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> int:
        """
        Fill FIG 0/5 data.

        Format for short form (MSC sub-channel):
        - LS (1 bit): Long/Short form (0=short)
        - SubChId (6 bits): Sub-channel ID
        - Language (8 bits): Language code
        """
        start_size = len(buf)
        remaining = max_size

        # For each service, output language for its components
        for service in self.ensemble.services:
            if service.language == 0:
                continue  # Skip if no language specified

            # Find components for this service
            components = [c for c in self.ensemble.components if c.service_id == service.id]

            for comp in components:
                # Find subchannel for this component
                subchannels = [s for s in self.ensemble.subchannels if s.id == comp.subchannel_id]
                if not subchannels:
                    continue

                subchannel = subchannels[0]

                # Need 2 bytes for short form
                if remaining < 2:
                    break

                # Short form: LS=0, SubChId (6 bits)
                buf.append((0 << 7) | (subchannel.id & 0x3F))
                # Language code (8 bits)
                buf.append(service.language & 0xFF)

                remaining -= 2

            if remaining < 2:
                break

        return len(buf) - start_size

    def repetition_rate(self) -> FIGRate:
        """FIG 0/5 transmitted at rate B."""
        return FIGRate.B

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 5."""
        return 5


class FIG0_8(FIGBase):
    """
    FIG 0/8: Service component global definition.

    Provides additional attributes for service components.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """Initialize FIG 0/8."""
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> int:
        """
        Fill FIG 0/8 data.

        Format:
        - Ext (3 bits): Extension flag (0)
        - SCIdS (4 bits): Service Component Identifier within Service
        - LS (1 bit): Long/Short form (0=short)
        - SubChId (6 bits): Sub-channel ID
        - FIDCId (6 bits): Fast Information Data Channel Identifier
        """
        start_size = len(buf)
        remaining = max_size

        # For each service component
        scids = 0
        for service in self.ensemble.services:
            components = [c for c in self.ensemble.components if c.service_id == service.id]

            for comp in components:
                # Find subchannel
                subchannels = [s for s in self.ensemble.subchannels if s.id == comp.subchannel_id]
                if not subchannels:
                    continue

                subchannel = subchannels[0]

                # Need 2 bytes
                if remaining < 2:
                    break

                # Byte 1: Ext(3) + SCIdS(4) + LS(1)
                # Ext=0 (no extension), LS=0 (short form)
                buf.append((0 << 5) | ((scids & 0x0F) << 1) | 0)

                # Byte 2: SubChId(6) + FIDCId_high(2)
                # FIDCId is typically 0 for audio services
                buf.append((subchannel.id & 0x3F) << 2)

                remaining -= 2
                scids = (scids + 1) & 0x0F

            if remaining < 2:
                break

        return len(buf) - start_size

    def repetition_rate(self) -> FIGRate:
        """FIG 0/8 transmitted at rate B."""
        return FIGRate.B

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 8."""
        return 8


class FIG0_13(FIGBase):
    """
    FIG 0/13: User application information.

    Provides information about applications associated with services.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """Initialize FIG 0/13."""
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> int:
        """
        Fill FIG 0/13 data.

        Format:
        - SId (16 or 32 bits): Service Identifier
        - SCIdS (4 bits): Service Component Identifier within Service
        - No (4 bits): Number of user applications
        - For each application:
          - User application type (11 bits)
          - User application data length (5 bits)
          - User application data (variable)
        """
        start_size = len(buf)
        remaining = max_size

        # FIG 0/13 is complex and application-specific
        # For basic implementation, we'll skip it or provide minimal data
        # This is typically used for multimedia services and advanced features

        return len(buf) - start_size

    def repetition_rate(self) -> FIGRate:
        """FIG 0/13 transmitted at rate C."""
        return FIGRate.C

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 13."""
        return 13


class FIG0_17(FIGBase):
    """
    FIG 0/17: Programme Type.

    Provides programme type information for services.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """Initialize FIG 0/17."""
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> int:
        """
        Fill FIG 0/17 data.

        Format:
        - SId (16 or 32 bits): Service Identifier
        - SD (1 bit): Static/Dynamic (0=static)
        - PS (1 bit): Primary/Secondary (0=primary)
        - L/S (1 bit): Language/Spare
        - CC (1 bit): Closed Caption
        - Rfa (4 bits): Reserved
        - Int code (8 bits): International code (PTy)
        - Comp code (8 bits): Complementary code (optional)
        """
        start_size = len(buf)
        remaining = max_size

        for service in self.ensemble.services:
            if service.pty_settings.pty == 0:
                continue  # Skip if no PTy specified

            # Calculate size needed
            # 16-bit SId: 2 bytes + 2 bytes (flags + PTy)
            # 32-bit SId: 4 bytes + 2 bytes (flags + PTy)
            size_needed = 4 if service.id < 0x10000 else 6

            if remaining < size_needed:
                break

            # Service ID (16 or 32 bits)
            if service.id < 0x10000:
                # 16-bit SId
                buf.append((service.id >> 8) & 0xFF)
                buf.append(service.id & 0xFF)
            else:
                # 32-bit SId
                buf.append((service.id >> 24) & 0xFF)
                buf.append((service.id >> 16) & 0xFF)
                buf.append((service.id >> 8) & 0xFF)
                buf.append(service.id & 0xFF)

            # Flags byte: SD(1) + PS(1) + L/S(1) + CC(1) + Rfa(4)
            # SD=0 (static), PS=0 (primary), L/S=0, CC=0, Rfa=0
            buf.append(0x00)

            # International code (PTy)
            buf.append(service.pty_settings.pty & 0xFF)

            remaining -= size_needed

        return len(buf) - start_size

    def repetition_rate(self) -> FIGRate:
        """FIG 0/17 transmitted at rate B."""
        return FIGRate.B

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 17."""
        return 17
