"""
FIG Type 0 implementations.

FIG Type 0 contains multiplex configuration information (MCI).
This module implements the most important FIG 0 variants.
"""
import struct
import structlog
import time
from datetime import datetime
from typing import List
from dabmux.fig.base import FIGBase, FIGRate, FillStatus, FIGPriority

logger = structlog.get_logger()
from dabmux.core.mux_elements import (
    DabEnsemble,
    DabSubchannel,
    DabService,
    ProtectionForm,
    SubchannelType,
)

# Announcement types mapping for FIG 0/18 and 0/19
ANNOUNCEMENT_TYPES = {
    'alarm': 0,
    'traffic': 1,
    'transport': 2,
    'warning': 3,
    'news': 4,
    'weather': 5,
    'event': 6,
    'special': 7,
    'programme_info': 8,
    'sport': 9,
    'financial': 10,
}


def calculate_mjd(year: int, month: int, day: int) -> int:
    """
    Calculate Modified Julian Date (MJD) from Gregorian calendar date.

    Per ETSI EN 300 401 Section 8.1.3.3.

    Args:
        year: Year (e.g., 2026)
        month: Month (1-12)
        day: Day (1-31)

    Returns:
        MJD value (17-bit)
    """
    # Convert to Julian Date first
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3

    jd = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

    # Convert to Modified Julian Date (MJD = JD - 2400000.5)
    mjd = jd - 2400001  # Integer version

    return mjd & 0x1FFFF  # 17 bits


def calculate_lto_auto() -> int:
    """
    Calculate Local Time Offset automatically from system timezone.

    Returns LTO in half-hours relative to UTC (-24 to +24).

    Returns:
        LTO value in half-hours
    """
    # Get local timezone offset in seconds
    if time.daylight:
        # DST is in effect
        offset_seconds = -time.altzone
    else:
        # Standard time
        offset_seconds = -time.timezone

    # Convert to half-hours
    offset_half_hours = offset_seconds // 1800

    # Clamp to valid range (-24 to +24)
    return max(-24, min(24, offset_half_hours))


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
        length = 4    # 4 bytes of data after header
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

    def priority(self) -> FIGPriority:
        """FIG 0/0 is CRITICAL - must be in every frame."""
        return FIGPriority.CRITICAL

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
            # UEP uses short form (3 bytes), EEP uses long form (4 bytes)
            # DAB+ always uses EEP because it has Reed-Solomon FEC
            is_uep = (subchannel.protection.form == ProtectionForm.UEP)

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
                # Byte 2: Form (1 bit) | Table Switch (1 bit) | Table Index (6 bits)
                # According to ETSI EN 300 799, bit layout is: Bit 7=Form, Bit 6=Switch, Bits 5-0=Table Index
                start_addr = subchannel.start_address
                table_index = subchannel.protection.to_tpl(subchannel.bitrate) & 0x3F
                table_switch = 0  # Always 0 for now
                form = 0  # 0 = short form (UEP)

                buf[pos] = (subchannel.id << 2) | ((start_addr >> 8) & 0x03)
                buf[pos + 1] = start_addr & 0xFF
                buf[pos + 2] = (form << 7) | (table_switch << 6) | table_index

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

                logger.debug(
                    "Encoding EEP subchannel",
                    subchan_id=subchannel.id,
                    subchan_type=subchannel.type,
                    start_addr=start_addr,
                    size_cu=size_cu,
                    protection_level=protection_level,
                    option=option,
                    form=form
                )

                buf[pos] = (subchannel.id << 2) | ((start_addr >> 8) & 0x03)
                buf[pos + 1] = start_addr & 0xFF
                buf[pos + 2] = (form << 7) | ((option & 0x07) << 4) | ((protection_level & 0x03) << 2) | ((size_cu >> 8) & 0x03)
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

    def priority(self) -> FIGPriority:
        """FIG 0/1 is HIGH - subchannel organization needed for initial tuning."""
        return FIGPriority.HIGH

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
                # Byte 1: SubChId (6) | PS (1) | CA (1)
                # Note: Byte layout matches dablin's parser (bits 7-2: SubChId, bit 1: PS, bit 0: CA)

                # Determine ASCTy based on subchannel type
                # ETSI EN 300 401 Section 6.3.3:
                #   ASCTy = 0: DAB (MPEG Layer II)
                #   ASCTy = 63: DAB+ (HE-AAC)
                ascty = 0  # Default to DAB

                # Look up subchannel to determine audio type
                subchannel = None
                for sc in self.ensemble.subchannels:
                    if sc.id == component.subchannel_id:
                        subchannel = sc
                        break

                if subchannel:
                    if subchannel.type == SubchannelType.DABPlusAudio:
                        ascty = 63  # DAB+ (HE-AAC)
                    elif subchannel.type == SubchannelType.DABAudio:
                        ascty = 0   # DAB (MPEG Layer II)

                tmid = 0  # Stream mode (MSC stream)
                ps = 1    # Primary/Secondary: 1 = primary
                ca = 0    # CA flag: 0 = not conditional access

                buf[pos] = (tmid << 6) | (ascty & 0x3F)
                buf[pos + 1] = ((component.subchannel_id & 0x3F) << 2) | (ps << 1) | ca
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

    def priority(self) -> FIGPriority:
        """FIG 0/2 is HIGH - service organization needed for service discovery."""
        return FIGPriority.HIGH

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


class FIG0_9(FIGBase):
    """
    FIG 0/9: Extended Country Code and Local Time Offset.

    Provides Extended Country Code (ECC) and Local Time Offset (LTO) information
    for services. Required for FIG 0/10 LTO support.

    Per ETSI EN 300 401 Section 8.1.3.2.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 0/9.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble
        self.service_index = 0

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 0/9 data.

        Long form encoding (5 bytes per service):
        - Byte 0: LTO sign + LTO value (6 bits)
        - Bytes 1-2: Service ID (16 bits, big-endian)
        - Byte 3: Extended Country Code (8 bits)
        - Byte 4: International table ID (8 bits)

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        if max_size < 2:
            return status

        start_pos = 0
        pos = 2  # Reserve space for header

        services = self.ensemble.services
        if not services:
            return status

        # Calculate LTO for ensemble
        if self.ensemble.lto_auto:
            lto = calculate_lto_auto()
        else:
            lto = self.ensemble.lto

        # Encode LTO for long form (6 bits: 1 sign + 5 value)
        lto_sign = 0 if lto >= 0 else 1
        lto_value = abs(lto) & 0x1F

        while self.service_index < len(services):
            service = services[self.service_index]

            # Long form: 5 bytes per service
            if pos + 5 > max_size:
                break

            # Byte 0: Long form flag (1) + LTO sign (1) + LTO value (5 bits) + spare (1)
            buf[pos] = 0x80 | (lto_sign << 5) | (lto_value & 0x1F)
            pos += 1

            # Bytes 1-2: Service ID (big-endian)
            struct.pack_into('>H', buf, pos, service.id)
            pos += 2

            # Byte 3: ECC (use service-specific or ensemble ECC)
            ecc = service.ecc if service.ecc != 0 else self.ensemble.ecc
            buf[pos] = ecc & 0xFF
            pos += 1

            # Byte 4: International table ID
            buf[pos] = self.ensemble.international_table & 0xFF
            pos += 1

            self.service_index += 1

        bytes_written = pos - 2

        if bytes_written == 0:
            return status

        # Fill header
        fig_type = 0
        length = bytes_written + 1
        cn = 0
        oe = 0
        pd = 0
        extension = 9

        buf[start_pos] = (fig_type << 5) | (length & 0x1F)
        buf[start_pos + 1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        status.num_bytes_written = 2 + bytes_written

        # Check if complete
        if self.service_index >= len(services):
            status.complete_fig_transmitted = True
            self.service_index = 0

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 0/9 transmitted at rate B (once per second)."""
        return FIGRate.B

    def priority(self) -> FIGPriority:
        """FIG 0/9 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 9."""
        return 9


class FIG0_10(FIGBase):
    """
    FIG 0/10: Date and Time.

    Provides current date and time to receivers for display and logging.
    Can optionally include Local Time Offset (LTO).

    Per ETSI EN 300 401 Section 8.1.3.3.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 0/10.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 0/10 data.

        Without LTO (4 bytes data):
        - Bytes 0-1: MJD high (17 bits, upper 16)
        - Byte 2: MJD low (1 bit) + UTC flag + Hour (5 bits)
        - Byte 3: Minute (6 bits) + Spare (2 bits)

        With LTO (6 bytes data):
        - Bytes 0-3: As above
        - Byte 4: LTO sign + LTO value (5 bits) + Spare (2 bits)
        - Byte 5: Confidence (1 bit) + Spare (7 bits)

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        # Calculate size needed
        include_lto = self.ensemble.datetime.include_lto
        data_size = 6 if include_lto else 4
        total_size = 2 + data_size  # Header + data

        if max_size < total_size:
            return status

        # Get current datetime
        if self.ensemble.datetime.source == 'manual' and self.ensemble.datetime.manual_datetime:
            dt = self.ensemble.datetime.manual_datetime
        else:
            dt = datetime.utcnow() if self.ensemble.datetime.utc_flag else datetime.now()

        # Calculate MJD
        mjd = calculate_mjd(dt.year, dt.month, dt.day)

        # FIG header
        fig_type = 0
        length = data_size + 1
        cn = 0
        oe = 0
        pd = 0
        extension = 10

        buf[0] = (fig_type << 5) | (length & 0x1F)
        buf[1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        # Data bytes
        # Bytes 2-3: MJD high (upper 16 bits of 17-bit MJD)
        buf[2] = (mjd >> 9) & 0xFF
        buf[3] = (mjd >> 1) & 0xFF

        # Byte 4: MJD low bit + UTC flag + Hour
        mjd_low = mjd & 0x01
        utc_flag = 1 if self.ensemble.datetime.utc_flag else 0
        hour = dt.hour & 0x1F

        buf[4] = (mjd_low << 7) | (utc_flag << 6) | (hour & 0x1F)

        # Byte 5: Minute (upper 6 bits)
        minute = dt.minute & 0x3F
        buf[5] = (minute << 2)

        if include_lto:
            # Calculate LTO
            if self.ensemble.lto_auto:
                lto = calculate_lto_auto()
            else:
                lto = self.ensemble.lto

            # Byte 6: LTO sign + LTO value (5 bits)
            lto_sign = 0 if lto >= 0 else 1
            lto_value = abs(lto) & 0x1F
            buf[6] = (lto_sign << 5) | (lto_value & 0x1F)

            # Byte 7: Confidence indicator
            confidence = 1 if self.ensemble.datetime.confidence else 0
            buf[7] = (confidence << 7)

        status.num_bytes_written = total_size
        status.complete_fig_transmitted = True

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 0/10 transmitted at rate B (once per second)."""
        return FIGRate.B

    def priority(self) -> FIGPriority:
        """FIG 0/10 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 10."""
        return 10


class FIG0_18(FIGBase):
    """
    FIG 0/18: Announcement Support.

    Declares which announcement types each service supports.
    Required for Emergency Alert System (EAS) functionality.

    Per ETSI EN 300 401 Section 8.1.6.3.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 0/18.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble
        self.service_index = 0

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 0/18 data.

        Variable length per service:
        - Bytes 0-1: Service ID (16 bits)
        - Bytes 2-3: ASU flags (16 bits) - announcement types
        - Byte 4: Cluster count (5 bits) + New flag + Region flag
        - Bytes 5+: Cluster IDs (1 byte each)

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        if max_size < 2:
            return status

        start_pos = 0
        pos = 2  # Reserve space for header

        # Filter services with announcements enabled
        services_with_ann = [s for s in self.ensemble.services
                            if s.announcements.enabled]

        if not services_with_ann:
            return status

        while self.service_index < len(services_with_ann):
            service = services_with_ann[self.service_index]

            # Calculate size needed
            num_clusters = len(service.clusters)
            entry_size = 5 + num_clusters  # SId(2) + ASU(2) + flags(1) + clusters

            if pos + entry_size > max_size:
                break

            # Bytes 0-1: Service ID (big-endian)
            struct.pack_into('>H', buf, pos, service.id)
            pos += 2

            # Bytes 2-3: ASU flags (announcement support)
            # Combine configured types with pre-set asu field
            asu = service.asu  # Start with pre-set value
            for ann_type in service.announcements.types:
                bit_pos = ANNOUNCEMENT_TYPES.get(ann_type.lower())
                if bit_pos is not None:
                    asu |= (1 << bit_pos)

            struct.pack_into('>H', buf, pos, asu)
            pos += 2

            # Byte 4: Cluster count (5 bits) + New flag + Region flag
            cluster_count = num_clusters & 0x1F
            new_flag = 1 if service.announcements.new_flag else 0
            region_flag = 1 if service.announcements.region_flag else 0

            buf[pos] = (cluster_count << 3) | (new_flag << 2) | (region_flag << 1)
            pos += 1

            # Cluster IDs
            for cluster_id in service.clusters:
                buf[pos] = cluster_id & 0xFF
                pos += 1

            self.service_index += 1

        bytes_written = pos - 2

        if bytes_written == 0:
            return status

        # Fill header
        fig_type = 0
        length = bytes_written + 1
        cn = 0
        oe = 0
        pd = 0
        extension = 18

        buf[start_pos] = (fig_type << 5) | (length & 0x1F)
        buf[start_pos + 1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        status.num_bytes_written = 2 + bytes_written

        # Check if complete
        if self.service_index >= len(services_with_ann):
            status.complete_fig_transmitted = True
            self.service_index = 0

        return status

    def repetition_rate(self) -> FIGRate:
        """FIG 0/18 transmitted at rate B (once per second)."""
        return FIGRate.B

    def priority(self) -> FIGPriority:
        """FIG 0/18 is NORMAL priority."""
        return FIGPriority.NORMAL

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 18."""
        return 18


class FIG0_19(FIGBase):
    """
    FIG 0/19: Announcement Switching.

    Signals active announcements and directs receivers to switch to
    announcement subchannels. Dynamic priority/rate based on active state.

    Per ETSI EN 300 401 Section 8.1.6.4.
    """

    def __init__(self, ensemble: DabEnsemble) -> None:
        """
        Initialize FIG 0/19.

        Args:
            ensemble: Ensemble configuration
        """
        super().__init__()
        self.ensemble = ensemble

    def fill(self, buf: bytearray, max_size: int) -> FillStatus:
        """
        Fill buffer with FIG 0/19 data.

        Variable length per announcement:
        - Byte 0: Cluster ID
        - Bytes 1-2: ASU flags (currently active types)
        - Byte 3: SubChId (6 bits) + Region flag + New flag
        - Byte 4: (Optional) Region ID if region flag set

        Args:
            buf: Buffer to write into
            max_size: Maximum bytes available

        Returns:
            Fill status
        """
        status = FillStatus()

        # Skip transmission if no active announcements
        if not self.ensemble.active_announcements:
            return status

        if max_size < 2:
            return status

        start_pos = 0
        pos = 2  # Reserve space for header

        for announcement in self.ensemble.active_announcements:
            # Calculate size needed
            entry_size = 4  # Cluster(1) + ASU(2) + flags(1)
            if announcement.region_flag:
                entry_size += 1  # Region ID

            if pos + entry_size > max_size:
                break

            # Byte 0: Cluster ID
            buf[pos] = announcement.cluster_id & 0xFF
            pos += 1

            # Bytes 1-2: ASU flags (active announcement types)
            asu = 0
            for ann_type in announcement.types:
                bit_pos = ANNOUNCEMENT_TYPES.get(ann_type.lower())
                if bit_pos is not None:
                    asu |= (1 << bit_pos)

            struct.pack_into('>H', buf, pos, asu)
            pos += 2

            # Byte 3: SubChId (6 bits) + Region flag + New flag
            subchan_id = announcement.subchannel_id & 0x3F
            region_flag = 1 if announcement.region_flag else 0
            new_flag = 1 if announcement.new_flag else 0

            buf[pos] = (subchan_id << 2) | (region_flag << 1) | new_flag
            pos += 1

            # Optional region ID
            if announcement.region_flag:
                buf[pos] = announcement.region_id & 0xFF
                pos += 1

        bytes_written = pos - 2

        if bytes_written == 0:
            return status

        # Fill header
        fig_type = 0
        length = bytes_written + 1
        cn = 0
        oe = 0
        pd = 0
        extension = 19

        buf[start_pos] = (fig_type << 5) | (length & 0x1F)
        buf[start_pos + 1] = (cn << 7) | (oe << 6) | (pd << 5) | (extension & 0x1F)

        status.num_bytes_written = 2 + bytes_written
        status.complete_fig_transmitted = True

        return status

    def repetition_rate(self) -> FIGRate:
        """
        FIG 0/19 uses dynamic rate.

        Rate A (100ms) when announcements active, Rate B otherwise.
        """
        if self.ensemble.active_announcements:
            return FIGRate.A  # Fast rate when active
        else:
            return FIGRate.B  # Slow rate when idle

    def priority(self) -> FIGPriority:
        """
        FIG 0/19 uses dynamic priority.

        HIGH priority when announcements active, NORMAL otherwise.
        """
        if self.ensemble.active_announcements:
            return FIGPriority.HIGH  # Urgent when active
        else:
            return FIGPriority.NORMAL  # Normal when idle

    def fig_type(self) -> int:
        """FIG type 0."""
        return 0

    def fig_extension(self) -> int:
        """Extension 19."""
        return 19
