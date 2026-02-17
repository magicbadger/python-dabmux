"""
Ensemble configuration and MUX elements.

This module defines all data structures used to represent ensemble data,
including services, components, subchannels, and the ensemble itself.
"""
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Optional


# Protection levels and bitrates for UEP (Unequal Error Protection)
PROTECTION_LEVEL_TABLE = [
    4, 3, 2, 1, 0,
    4, 3, 2, 1, 0,
    4, 3, 2, 1,
    4, 3, 2, 1, 0,
    4, 3, 2, 1, 0,
    4, 3, 2, 1, 0,
    4, 3, 2, 1,
    4, 3, 2, 1, 0,
    4, 3, 2, 1, 0,
    4, 3, 2, 1, 0,
    4, 3, 2, 1, 0,
    4, 3, 2, 1, 0,
    4, 3, 1,
    4, 2, 0
]

BITRATE_TABLE = [
    32, 32, 32, 32, 32,
    48, 48, 48, 48, 48,
    56, 56, 56, 56,
    64, 64, 64, 64, 64,
    80, 80, 80, 80, 80,
    96, 96, 96, 96, 96,
    112, 112, 112, 112,
    128, 128, 128, 128, 128,
    160, 160, 160, 160, 160,
    192, 192, 192, 192, 192,
    224, 224, 224, 224, 224,
    256, 256, 256, 256, 256,
    320, 320, 320,
    384, 384, 384
]

# UEP (Unequal Error Protection) table index mapping
# Based on ETSI EN 300 401 and ODR-DabMux tables
# Key: (bitrate_kbps, protection_level)
# Value: table_index for Sub_Channel_SizeTable lookup
# Note: Protection level in DAB uses 0-4 (not 1-5)
UEP_TABLE_INDEX = {
    # 32 kbps
    (32, 4): 0, (32, 3): 1, (32, 2): 2, (32, 1): 3, (32, 0): 4,
    # 48 kbps
    (48, 4): 5, (48, 3): 6, (48, 2): 7, (48, 1): 8, (48, 0): 9,
    # 56 kbps
    (56, 4): 10, (56, 3): 11, (56, 2): 12, (56, 1): 13,
    # 64 kbps
    (64, 4): 14, (64, 3): 15, (64, 2): 16, (64, 1): 17, (64, 0): 18,
    # 80 kbps
    (80, 4): 19, (80, 3): 20, (80, 2): 21, (80, 1): 22, (80, 0): 23,
    # 96 kbps
    (96, 4): 24, (96, 3): 25, (96, 2): 26, (96, 1): 27, (96, 0): 28,
    # 112 kbps
    (112, 4): 29, (112, 3): 30, (112, 2): 31, (112, 1): 32,
    # 128 kbps
    (128, 4): 33, (128, 3): 34, (128, 2): 35, (128, 1): 36, (128, 0): 37,
    # 160 kbps
    (160, 4): 38, (160, 3): 39, (160, 2): 40, (160, 1): 41, (160, 0): 42,
    # 192 kbps
    (192, 4): 43, (192, 3): 44, (192, 2): 45, (192, 1): 46, (192, 0): 47,
    # 224 kbps
    (224, 4): 48, (224, 3): 49, (224, 2): 50, (224, 1): 51, (224, 0): 52,
    # 256 kbps
    (256, 4): 53, (256, 3): 54, (256, 2): 55, (256, 1): 56, (256, 0): 57,
    # 320 kbps
    (320, 4): 58, (320, 3): 59, (320, 1): 60,
    # 384 kbps
    (384, 4): 61, (384, 2): 62, (384, 0): 63,
}

# Sub_Channel_SizeTable from ETSI EN 300 401 / ODR-DabMux
# Index is the UEP table index, value is size in Capacity Units (CU)
SUB_CHANNEL_SIZE_TABLE_CU = [
    16, 21, 24, 29, 35, 24, 29, 35,
    42, 52, 29, 35, 42, 52, 32, 42,
    48, 58, 70, 40, 52, 58, 70, 84,
    48, 58, 70, 84, 104, 58, 70, 84,
    104, 64, 84, 96, 116, 140, 80, 104,
    116, 140, 168, 96, 116, 140, 168, 208,
    116, 140, 168, 208, 232, 128, 168, 192,
    232, 280, 160, 208, 280, 192, 280, 416
]


class SubchannelType(Enum):
    """Subchannel content type."""
    DABAudio = "audio"
    DABPlusAudio = "dabplus"
    DataDmb = "dmb"
    Packet = "packet"


class TransmissionMode(IntEnum):
    """DAB transmission modes."""
    TM_I = 1
    TM_II = 2
    TM_III = 3
    TM_IV = 4


class ProtectionForm(Enum):
    """Protection scheme form."""
    UEP = "uep"  # Unequal Error Protection (Short form)
    EEP = "eep"  # Equal Error Protection (Long form)


class EEPProfile(Enum):
    """EEP protection profile."""
    EEP_A = "A"
    EEP_B = "B"


@dataclass
class DabLabel:
    """
    DAB service/ensemble label.

    Labels are max 16 characters for the long label and 8 for short label.
    In the full implementation, labels use EBU Latin charset, but for Phase 0
    we'll use UTF-8 and defer proper charset conversion to Phase 2.
    """
    text: str = ""
    short_text: str = ""
    flag: int = 0xFFFF  # Flag indicating which characters form short label

    def to_ebu_latin(self) -> bytes:
        """
        Convert label to EBU Latin charset (16 bytes).

        For Phase 0, this is a stub that just encodes as UTF-8 and pads.
        Proper EBU Latin conversion will be implemented in Phase 2.
        """
        encoded = self.text.encode('utf-8', errors='replace')[:16]
        return encoded.ljust(16, b' ')

    def validate(self) -> bool:
        """Validate label length constraints."""
        return len(self.text) <= 16 and len(self.short_text) <= 8


@dataclass
class DabProtectionUEP:
    """Unequal Error Protection parameters."""
    table_index: int = 0


@dataclass
class DabProtectionEEP:
    """Equal Error Protection parameters."""
    profile: EEPProfile = EEPProfile.EEP_A

    def get_option(self) -> int:
        """Get 3-bit option field (0 for EEP-A, 1 for EEP-B)."""
        return 0 if self.profile == EEPProfile.EEP_A else 1


@dataclass
class DabProtection:
    """
    Protection scheme configuration.

    DAB supports two protection forms:
    - UEP (Unequal Error Protection): Uses table lookup
    - EEP (Equal Error Protection): Uses profile (A or B) and level
    """
    level: int = 2  # Protection level (0-4)
    form: ProtectionForm = ProtectionForm.UEP
    uep: Optional[DabProtectionUEP] = None
    eep: Optional[DabProtectionEEP] = None

    def to_tpl(self, bitrate: int) -> int:
        """
        Convert to TPL (Type and Protection Level) field.

        According to ETSI EN 300 799 5.4.1.2.
        For UEP, returns the table index from UEP_TABLE_INDEX.
        For EEP, encodes profile and level (not yet implemented).

        Args:
            bitrate: Subchannel bitrate in kbps

        Returns:
            6-bit TPL value
        """
        if self.form == ProtectionForm.UEP:
            # Look up UEP table index
            key = (bitrate, self.level)
            table_idx = UEP_TABLE_INDEX.get(key, 0)
            return table_idx & 0x3F
        else:
            # EEP encoding (not yet fully implemented)
            # Format: 1 bit (1=EEP) + 2 bits profile + 3 bits level
            return 0x20 | (self.level & 0x1F)


@dataclass
class DabSubchannel:
    """
    DAB subchannel (audio or data stream).

    Each subchannel occupies a specific portion of the transmission capacity.
    """
    uid: str
    id: int = 0  # Subchannel ID (0-63)
    type: SubchannelType = SubchannelType.DABAudio
    start_address: int = 0  # Start address in Capacity Units (CU)
    bitrate: int = 0  # Bitrate in kbps
    protection: DabProtection = field(default_factory=DabProtection)
    input_uri: str = ""

    def get_size_cu(self) -> int:
        """
        Calculate subchannel size in Capacity Units (CU).

        Uses the UEP table index to look up the size in SUB_CHANNEL_SIZE_TABLE_CU.
        """
        if self.protection.form == ProtectionForm.UEP:
            # Get UEP table index
            key = (self.bitrate, self.protection.level)
            table_idx = UEP_TABLE_INDEX.get(key, 0)
            # Look up size in CU
            if 0 <= table_idx < len(SUB_CHANNEL_SIZE_TABLE_CU):
                return SUB_CHANNEL_SIZE_TABLE_CU[table_idx]
        return 0

    def get_size_byte(self) -> int:
        """Calculate subchannel size in bytes."""
        # Each CU is 4 bytes (32 bits / 1 word) in all modes
        return self.get_size_cu() * 4

    def validate(self) -> bool:
        """Validate subchannel configuration."""
        return (
            0 <= self.id <= 63 and
            self.bitrate > 0 and
            0 <= self.protection.level <= 4
        )


@dataclass
class UserApplication:
    """
    User Application descriptor for FIG 0/13.

    Identifies the application used to decode channel data.
    """
    ua_type: int = 0xFFFF  # 11-bit user application type
    xpad_app_type: int = 0  # 5-bit X-PAD application type


@dataclass
class DabAudioComponent:
    """Audio component data."""
    ua_types: List[UserApplication] = field(default_factory=list)


@dataclass
class DabDataComponent:
    """Data component data."""
    pass


@dataclass
class DabPacketComponent:
    """Packet component data."""
    id: int = 0
    address: int = 0
    ua_types: List[UserApplication] = field(default_factory=list)
    datagroup: bool = False


@dataclass
class DabComponent:
    """
    Service component.

    A component links a service to a subchannel and defines how the
    data should be interpreted.
    """
    uid: str
    label: DabLabel = field(default_factory=DabLabel)
    service_id: int = 0  # Parent service ID
    subchannel_id: int = 0  # Associated subchannel ID
    type: int = 0  # Component type (audio/data)
    scids: int = 0  # Service Component ID within Service

    # Type-specific data
    audio: DabAudioComponent = field(default_factory=DabAudioComponent)
    data: DabDataComponent = field(default_factory=DabDataComponent)
    packet: DabPacketComponent = field(default_factory=DabPacketComponent)

    def validate(self) -> bool:
        """Validate component configuration."""
        return self.label.validate()


@dataclass
class PtySettings:
    """Programme Type settings."""
    pty: int = 0  # Programme type code (0 means disabled)
    dynamic_no_static: bool = False


@dataclass
class DabService:
    """
    DAB service.

    A service represents a radio channel/program and can have multiple
    components (e.g., audio + data).
    """
    uid: str
    id: int = 0  # Service ID (16 or 32-bit)
    ecc: int = 0  # Extended Country Code (0 = same as ensemble)
    label: DabLabel = field(default_factory=DabLabel)
    pty_settings: PtySettings = field(default_factory=PtySettings)
    language: int = 0  # Language code
    asu: int = 0  # Announcement support flags (16-bit)
    clusters: List[int] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate service configuration."""
        return self.label.validate() and self.id > 0


@dataclass
class DabEnsemble:
    """
    Complete DAB ensemble/multiplex.

    An ensemble is the top-level container that includes all services,
    components, and subchannels that are multiplexed together.
    """
    id: int = 0  # Ensemble ID (EId)
    ecc: int = 0  # Extended Country Code
    label: DabLabel = field(default_factory=DabLabel)
    transmission_mode: TransmissionMode = TransmissionMode.TM_I

    # Local time offset configuration
    lto_auto: bool = True  # Automatically calculate LTO
    lto: int = 0  # Local time offset in half-hours (-24 to +24)

    international_table: int = 1  # PTy table (1=RDS, 2=North America)
    alarm_flag: bool = False

    # Collections
    services: List[DabService] = field(default_factory=list)
    components: List[DabComponent] = field(default_factory=list)
    subchannels: List[DabSubchannel] = field(default_factory=list)

    def get_service(self, uid: str) -> Optional[DabService]:
        """Get service by UID."""
        for service in self.services:
            if service.uid == uid:
                return service
        return None

    def get_component(self, uid: str) -> Optional[DabComponent]:
        """Get component by UID."""
        for component in self.components:
            if component.uid == uid:
                return component
        return None

    def get_subchannel(self, uid: str) -> Optional[DabSubchannel]:
        """Get subchannel by UID."""
        for subchannel in self.subchannels:
            if subchannel.uid == uid:
                return subchannel
        return None

    def validate(self) -> bool:
        """Validate complete ensemble configuration."""
        if not self.label.validate():
            return False

        # Validate all services
        for service in self.services:
            if not service.validate():
                return False

        # Validate all components
        for component in self.components:
            if not component.validate():
                return False

        # Validate all subchannels
        for subchannel in self.subchannels:
            if not subchannel.validate():
                return False

        return True

    def get_total_capacity_units(self) -> int:
        """Calculate total capacity units used by all subchannels."""
        total = 0
        for subchannel in self.subchannels:
            total += subchannel.get_size_cu()
        return total
