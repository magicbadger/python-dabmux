"""
Ensemble configuration and MUX elements.

This module defines all data structures used to represent ensemble data,
including services, components, subchannels, and the ensemble itself.
"""
from dataclasses import dataclass, field
from datetime import datetime
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
class DynamicLabel:
    """
    Dynamic label for FIG 2 transmission.

    Differs from static DabLabel:
    - Variable length (0-128 chars vs fixed 16)
    - Toggle mechanism for change detection
    - Segmented transmission
    - Multiple charset support (EBU Latin, UTF-8, UCS-2)

    Used for "now playing" text on DAB receivers.
    """
    text: str = ""
    charset: int = 2  # 0=EBU Latin, 1=UCS-2, 2=UTF-8
    toggle: bool = False
    _segments: List[bytes] = field(default_factory=list, repr=False)
    _segment_index: int = field(default=0, repr=False)

    def __post_init__(self):
        """Initialize segments after creation."""
        if self.text:
            # Encode and segment initial text
            encoded = self._encode_text()
            self._segments = self._create_segments(encoded)

    def update_text(self, new_text: str) -> bool:
        """
        Update text and regenerate segments.

        Args:
            new_text: New text to display

        Returns:
            True if text changed, False otherwise
        """
        if new_text == self.text:
            return False

        self.toggle = not self.toggle
        self.text = new_text

        # Encode and segment
        encoded = self._encode_text()
        self._segments = self._create_segments(encoded)
        self._segment_index = 0

        return True

    def _encode_text(self) -> bytes:
        """
        Encode text per charset.

        Returns:
            Encoded text bytes (max 128 bytes)
        """
        if self.charset == 0:  # EBU Latin
            from dabmux.utils.charset import utf8_to_ebu_latin
            return utf8_to_ebu_latin(self.text, max_length=128, pad=False)
        elif self.charset == 1:  # UCS-2 (UTF-16 BE)
            return self.text.encode('utf-16-be')[:128]
        elif self.charset == 2:  # UTF-8
            return self.text.encode('utf-8')[:128]
        else:
            raise ValueError(f"Unsupported charset: {self.charset}")

    def _create_segments(self, data: bytes) -> List[bytes]:
        """
        Split data into 16-byte segments.

        Args:
            data: Encoded text data

        Returns:
            List of segments (max 8 segments for 128 bytes)
        """
        if len(data) == 0:
            return []  # Empty segments list for empty text

        segments = []
        for i in range(0, len(data), 16):
            segments.append(data[i:i+16])

        return segments  # Max 8 segments (128/16)

    def get_next_segment(self) -> Optional[bytes]:
        """
        Get next segment for transmission (circular).

        Returns:
            Next segment bytes, or None if no segments
        """
        if not self._segments:
            return None

        segment = self._segments[self._segment_index]
        self._segment_index = (self._segment_index + 1) % len(self._segments)
        return segment

    def get_current_segment_number(self) -> int:
        """Get current segment number (0-7)."""
        if not self._segments:
            return 0
        # Return the index that will be transmitted next time
        # (we already advanced it in get_next_segment)
        return (self._segment_index - 1) % len(self._segments)

    def is_last_segment(self) -> bool:
        """Check if current segment is the last one."""
        if not self._segments:
            return True
        current = (self._segment_index - 1) % len(self._segments)
        return current == len(self._segments) - 1


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
class DLSConfig:
    """
    DLS (Dynamic Label Segment) configuration.

    DLS provides text information (song titles, station info, etc.)
    displayed on DAB receivers.
    """
    enabled: bool = False
    input_type: str = 'file'  # 'file', 'fifo', or 'zeromq'
    input_path: str = ''
    charset: str = 'utf8'  # 'utf8' or 'ebu-latin'
    default_label: str = ''
    poll_interval: float = 1.0  # For file/fifo monitoring (seconds)


@dataclass
class PADConfig:
    """
    PAD (Programme Associated Data) configuration.

    PAD carries supplementary data alongside audio, including DLS text,
    MOT Slideshow images, and other data services.
    """
    enabled: bool = False
    length: int = 58  # Total PAD length in bytes (F-PAD + X-PAD)
    dls: Optional[DLSConfig] = None

    def __post_init__(self):
        """Initialize DLS config if None."""
        if self.dls is None and self.enabled:
            self.dls = DLSConfig()


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
    pad: Optional[PADConfig] = None  # PAD configuration for this subchannel
    fec_scheme: int = 0  # FEC scheme code (0=none, 1=RS(204,188), 2-3=reserved)

    def get_size_cu(self) -> int:
        """
        Calculate subchannel size in Capacity Units (CU).

        Uses standard DAB formulas based on bitrate and protection level.
        The subchannel size is independent of FEC encoding - it represents
        the MST capacity allocation, not the RS-encoded data size.

        Formula from ETSI EN 300 401 and ODR-DabMux implementation.
        """
        if self.protection.form == ProtectionForm.UEP:
            # UEP: Use table lookup
            key = (self.bitrate, self.protection.level)
            table_idx = UEP_TABLE_INDEX.get(key, 0)
            if 0 <= table_idx < len(SUB_CHANNEL_SIZE_TABLE_CU):
                return SUB_CHANNEL_SIZE_TABLE_CU[table_idx]
        elif self.protection.form == ProtectionForm.EEP and self.protection.eep:
            # EEP: Calculate from bitrate and protection level
            if self.protection.eep.profile == EEPProfile.EEP_A:
                # EEP-A formulas (right shift = divide by 2^n)
                if self.protection.level == 0:  # EEP 1-A
                    return (self.bitrate * 12) >> 3  # bitrate * 1.5
                elif self.protection.level == 1:  # EEP 2-A
                    return self.bitrate
                elif self.protection.level == 2:  # EEP 3-A
                    return (self.bitrate * 6) >> 3  # bitrate * 0.75
                elif self.protection.level == 3:  # EEP 4-A
                    return self.bitrate >> 1  # bitrate * 0.5
            elif self.protection.eep.profile == EEPProfile.EEP_B:
                # EEP-B formulas
                if self.protection.level == 0:  # EEP 1-B
                    return (self.bitrate * 27) >> 5  # bitrate * 0.84375
                elif self.protection.level == 1:  # EEP 2-B
                    return (self.bitrate * 21) >> 5  # bitrate * 0.65625
                elif self.protection.level == 2:  # EEP 3-B
                    return (self.bitrate * 18) >> 5  # bitrate * 0.5625
                elif self.protection.level == 3:  # EEP 4-B
                    return (self.bitrate * 15) >> 5  # bitrate * 0.46875
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
class OtherEnsembleService:
    """Service in another ensemble (FIG 0/24)."""
    ecc: int = 0              # Extended Country Code
    ensemble_id: int = 0      # Other ensemble's EId
    service_id: int = 0       # Service ID in that ensemble
    ca_id: int = 0            # Conditional Access (0=none)
    is_32bit_sid: bool = False  # True if 32-bit service ID


@dataclass
class FrequencyEntry:
    """Single frequency entry (FIG 0/21)."""
    frequency_mhz: float = 0.0    # Frequency in MHz
    freq_type: str = 'dab'        # 'dab', 'fm', 'drm', 'amss'


@dataclass
class FrequencyList:
    """Complete frequency list for a service (FIG 0/21)."""
    list_id: int = 0              # 0-15
    continuity: int = 0           # 0-3
    r_flag: bool = True           # List complete
    frequencies: List[FrequencyEntry] = field(default_factory=list)


@dataclass
class ServiceLink:
    """Single service link (FIG 0/6)."""
    idlq: int = 0                 # 0=DAB, 1=RDS/FM, 2=DRM, 3=AMSS
    lsn: int = 0                  # Linkage Set Number (12 bits)
    hard_link: bool = False       # Hard vs soft linking
    ils: bool = False             # International linkage set

    # DAB targets (IdLQ=0)
    target_ecc: int = 0
    target_ensemble_id: int = 0
    target_service_id: int = 0

    # RDS/FM targets (IdLQ=1)
    rds_pi_code: int = 0          # RDS Programme Identification
    fm_frequency_mhz: float = 0.0 # FM frequency

    # DRM/AMSS targets (IdLQ=2/3)
    drm_service_id: int = 0


@dataclass
class ServiceLinkage:
    """Service linkage configuration (FIG 0/6)."""
    enabled: bool = False
    links: List[ServiceLink] = field(default_factory=list)


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
    """Packet component data (for FIG 0/3)."""
    id: int = 0
    address: int = 0  # Packet address (10 bits, 0-1023)
    ua_types: List[UserApplication] = field(default_factory=list)
    datagroup: bool = False  # Data group flag
    dscty: int = 0  # Data Service Component Type (6 bits)
    ca_org: int = 0  # Conditional Access Organization


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
    is_packet_mode: bool = False  # True if TMid=01 (packet mode)

    # Type-specific data
    audio: DabAudioComponent = field(default_factory=DabAudioComponent)
    data: DabDataComponent = field(default_factory=DabDataComponent)
    packet: DabPacketComponent = field(default_factory=DabPacketComponent)

    # Dynamic label (Priority 4 - FIG 2/1)
    dynamic_label: Optional[DynamicLabel] = None

    def validate(self) -> bool:
        """Validate component configuration."""
        return self.label.validate()


@dataclass
class PtySettings:
    """Programme Type settings."""
    pty: int = 0  # Programme type code (0 means disabled)
    dynamic_no_static: bool = False


@dataclass
class DateTimeConfig:
    """
    Date and Time configuration for FIG 0/10.

    Provides time information to receivers for display and logging.
    """
    enabled: bool = False
    source: str = 'system'  # 'system' or 'manual'
    include_lto: bool = True  # Include Local Time Offset
    utc_flag: bool = True  # UTC flag (True = UTC, False = local time)
    confidence: bool = True  # Confidence indicator
    manual_datetime: Optional['datetime'] = None  # For manual source


@dataclass
class AnnouncementConfig:
    """
    Announcement configuration for a service (FIG 0/18).

    Declares which announcement types a service supports.
    """
    enabled: bool = False
    types: List[str] = field(default_factory=list)  # e.g., ['alarm', 'news']
    new_flag: bool = False
    region_flag: bool = False


@dataclass
class ActiveAnnouncement:
    """
    Active announcement for FIG 0/19.

    Represents a currently broadcasting announcement.
    """
    cluster_id: int
    types: List[str]
    subchannel_id: int
    new_flag: bool = True
    region_flag: bool = False
    region_id: int = 0


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
    announcements: AnnouncementConfig = field(default_factory=AnnouncementConfig)
    frequency_lists: List[FrequencyList] = field(default_factory=list)
    linkage: Optional[ServiceLinkage] = None

    def validate(self) -> bool:
        """Validate service configuration."""
        return self.label.validate() and self.id > 0


@dataclass
class EdiOutputConfig:
    """
    EDI output configuration (Priority 5).

    Configures EDI (Ensemble Data Interface) output for IP-based
    distribution to transmitters.
    """
    enabled: bool = False
    protocol: str = "udp"  # "udp" or "tcp"
    destination: str = "127.0.0.1:12000"  # host:port

    # UDP-specific options
    enable_pft: bool = False  # Enable PFT fragmentation (UDP only)
    pft_fec: int = 0  # FEC level 0-5 (UDP/PFT only)
    pft_fragment_size: int = 1400  # Max fragment size in bytes

    # TCP-specific options
    tcp_mode: str = "client"  # "client" or "server" (TCP only)

    # Common options
    enable_tist: bool = True  # Include timestamps
    source_port: int = 0  # Source port (0=auto)


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

    # Configuration Information (Priority 4 - FIG 0/7)
    configuration_count: int = 0  # FIG 0/7 configuration counter (0-1023)

    # Date/time and announcements
    datetime: DateTimeConfig = field(default_factory=DateTimeConfig)
    active_announcements: List[ActiveAnnouncement] = field(default_factory=list)

    # Service management and navigation (Priority 2)
    other_ensemble_services: List[OtherEnsembleService] = field(default_factory=list)

    # EDI output configuration (Priority 5)
    edi_output: Optional[EdiOutputConfig] = None

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

    def calculate_configuration_hash(self) -> int:
        """
        Calculate hash of ensemble configuration for FIG 0/7.

        Hash includes structural elements that affect receiver parsing:
        - Ensemble ID, ECC
        - Subchannel configurations (ID, type, bitrate, protection, FEC)
        - Service IDs
        - Component mappings

        Returns:
            10-bit hash value (0-1023)
        """
        config_tuple = (
            self.id,
            self.ecc,
            tuple((s.id, s.type.value, s.bitrate, s.protection.level,
                   s.protection.form.value, s.fec_scheme)
                  for s in self.subchannels),
            tuple((svc.id,) for svc in self.services),
            tuple((c.service_id, c.subchannel_id, c.is_packet_mode)
                  for c in self.components)
        )
        return abs(hash(config_tuple)) % 1024
