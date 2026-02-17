# Core Module

Core data structures for ETI frames and ensemble configuration.

## Module: `dabmux.core.eti`

ETI (Ensemble Transport Interface) frame structures with binary-accurate layout.

### Classes

#### `EtiFrame`

Complete ETI frame structure (6144 bytes for Mode I).

```python
from dabmux.core.eti import EtiFrame, TransmissionMode

frame = EtiFrame.create_empty(
    mode=TransmissionMode.MODE_I,
    with_tist=True
)
```

**Attributes:**

- `sync: EtiSync` - SYNC header (4 bytes)
- `fc: EtiFC` - Frame characterization (4 bytes)
- `stc_headers: List[EtiSTC]` - Subchannel headers (4 bytes each)
- `eoh: EtiEOH` - End of header (4 bytes)
- `fic_data: bytes` - Fast Information Channel data (96/32 bytes depending on mode)
- `mst_data: bytes` - Main Service Channel data (variable)
- `eof: EtiEOF` - End of frame (4 bytes)
- `tist: Optional[EtiTIST]` - Timestamp (4 bytes, optional)

**Methods:**

##### `create_empty(mode: int, with_tist: bool = False) -> EtiFrame`

Create an empty ETI frame for the given transmission mode.

**Parameters:**
- `mode: int` - Transmission mode (1=Mode I, 2=Mode II, 3=Mode III, 4=Mode IV)
- `with_tist: bool` - Include TIST field (default: False)

**Returns:** Empty `EtiFrame` with correct size for mode

**Example:**
```python
frame = EtiFrame.create_empty(mode=1, with_tist=True)
assert len(frame.pack()) == 6148  # 6144 + 4 for TIST
```

##### `pack() -> bytes`

Serialize frame to binary format.

**Returns:** Complete ETI frame as bytes (6144 or 6148 bytes with TIST)

**Example:**
```python
frame_bytes = frame.pack()
with open('output.eti', 'wb') as f:
    f.write(frame_bytes)
```

##### `pack_into(buffer: bytearray) -> None`

Pack frame directly into a pre-allocated buffer (zero-copy).

**Parameters:**
- `buffer: bytearray` - Target buffer (must be at least 6144 bytes)

**Example:**
```python
buffer = bytearray(6144)
frame.pack_into(buffer)
socket.send(buffer)  # Zero-copy send
```

---

#### `EtiSync`

ETI SYNC header (4 bytes).

**Binary Layout:**
```
Bits 0-7:   ERR   (Error indicator)
Bits 8-31:  FSYNC (Frame sync word, constant 0x49C5F8)
```

**Attributes:**

- `err: int` - Error indicator (0xFF = no error)
- `fsync: int` - Frame sync word (constant `0x49C5F8`)

**Methods:**

- `pack() -> bytes` - Pack to 4 bytes (little-endian)
- `unpack(data: bytes) -> EtiSync` - Unpack from 4 bytes (class method)

**Example:**
```python
from dabmux.core.eti import EtiSync

sync = EtiSync(err=0xFF, fsync=0x49C5F8)
packed = sync.pack()
assert len(packed) == 4
```

---

#### `EtiFC`

Frame Characterization (4 bytes).

**Binary Layout:**
```
Bits 0-7:   FCT     (Frame count, 0-255)
Bits 8-14:  NST     (Number of subchannels, 0-64)
Bit 15:     FICF    (FIC flag, always 1)
Bits 16-18: FL_high (Frame length high 3 bits)
Bits 19-20: MID     (Transmission mode)
Bits 21-23: FP      (Frame phase, 0-7)
Bits 24-31: FL_low  (Frame length low 8 bits)
```

**Attributes:**

- `fct: int` - Frame count (0-255, wraps around)
- `nst: int` - Number of subchannels (0-64)
- `ficf: int` - FIC flag (always 1)
- `mid: int` - Transmission mode (1=Mode I, 2=Mode II, 3=Mode III, 4=Mode IV)
- `fp: int` - Frame phase (0-7)
- `fl: int` - Frame length in 64-bit words (11 bits, 0-2047)

**Methods:**

- `get_frame_length() -> int` - Get 11-bit frame length
- `set_frame_length(length: int) -> None` - Set 11-bit frame length
- `pack() -> bytes` - Pack to 4 bytes
- `unpack(data: bytes) -> EtiFC` - Unpack from 4 bytes (class method)

**Example:**
```python
from dabmux.core.eti import EtiFC

fc = EtiFC(fct=42, nst=3, mid=1, fl=96)
assert fc.get_frame_length() == 96
```

---

#### `EtiSTC`

Sub-Channel header (4 bytes).

**Binary Layout:**
```
Bits 0-1:   startAddress_high (Start address high 2 bits)
Bits 2-7:   SCID              (Subchannel ID, 0-63)
Bits 8-15:  startAddress_low  (Start address low 8 bits)
Bits 16-17: STL_high          (Length high 2 bits)
Bits 18-23: TPL               (Protection level)
Bits 24-31: STL_low           (Length low 8 bits)
```

**Attributes:**

- `scid: int` - Subchannel ID (0-63)
- `start_address: int` - Start address in CU (Capacity Units, 10 bits, 0-1023)
- `tpl: int` - Protection level (6 bits)
- `stl: int` - Subchannel length in 64-bit words (10 bits, 0-1023)

**Methods:**

- `get_stl() -> int` - Get 10-bit subchannel length
- `set_stl(length: int) -> None` - Set 10-bit subchannel length
- `get_start_address() -> int` - Get 10-bit start address
- `set_start_address(address: int) -> None` - Set 10-bit start address
- `pack() -> bytes` - Pack to 4 bytes
- `unpack(data: bytes) -> EtiSTC` - Unpack from 4 bytes (class method)

**Example:**
```python
from dabmux.core.eti import EtiSTC

stc = EtiSTC(scid=0, start_address=0, tpl=0x10, stl=84)
```

---

#### `EtiEOH`

End of Header (4 bytes).

**Binary Layout:**
```
Bits 0-15:  (reserved, set to 0xFFFF)
Bits 16-31: CRC (CRC-16 of SYNC + FC + STC headers)
```

**Attributes:**

- `crc: int` - CRC-16 checksum (16 bits)

**Methods:**

- `pack() -> bytes` - Pack to 4 bytes
- `unpack(data: bytes) -> EtiEOH` - Unpack from 4 bytes (class method)

---

#### `EtiEOF`

End of Frame (4 bytes).

**Binary Layout:**
```
Bits 0-15:  CRC (CRC-16 of FIC + MST data)
Bits 16-31: RFU (Reserved for future use, set to 0xFFFF)
```

**Attributes:**

- `crc: int` - CRC-16 checksum (16 bits)
- `rfu: int` - Reserved (16 bits, always `0xFFFF`)

**Methods:**

- `pack() -> bytes` - Pack to 4 bytes
- `unpack(data: bytes) -> EtiEOF` - Unpack from 4 bytes (class method)

---

#### `EtiTIST`

Timestamp (4 bytes, optional).

**Binary Layout:**
```
Bits 0-31:  TIST (Timestamp in 16.384 MHz ticks)
```

**Attributes:**

- `tist: int` - Timestamp value (32 bits)

**Methods:**

- `pack() -> bytes` - Pack to 4 bytes
- `unpack(data: bytes) -> EtiTIST` - Unpack from 4 bytes (class method)
- `from_datetime(dt: datetime) -> EtiTIST` - Create from Python datetime (class method)

**Example:**
```python
from dabmux.core.eti import EtiTIST
from datetime import datetime

tist = EtiTIST.from_datetime(datetime.now())
tist_bytes = tist.pack()
```

---

### Enums

#### `TransmissionMode`

DAB transmission modes.

```python
class TransmissionMode(IntEnum):
    MODE_I = 1    # Mode I (most common)
    MODE_II = 2   # Mode II
    MODE_III = 3  # Mode III
    MODE_IV = 4   # Mode IV
```

**Mode characteristics:**

| Mode | FIC Size | Frame Duration | Capacity (CU) |
|------|----------|----------------|---------------|
| I    | 96 bytes | 96 ms          | 864           |
| II   | 32 bytes | 24 ms          | 432           |
| III  | 32 bytes | 24 ms          | 864           |
| IV   | 32 bytes | 96 ms          | 432           |

---

## Module: `dabmux.core.mux_elements`

Ensemble configuration elements (services, subchannels, components).

### Classes

#### `DabEnsemble`

DAB ensemble configuration (top-level container).

```python
from dabmux.core.mux_elements import DabEnsemble, TransmissionMode

ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    transmission_mode=TransmissionMode.TM_I,
    label_text='My DAB',
    label_short='DAB'
)
```

**Attributes:**

- `id: int` - Ensemble ID (16 bits, e.g., `0xCE15`)
- `ecc: int` - Extended Country Code (8 bits, e.g., `0xE1` for Germany)
- `transmission_mode: TransmissionMode` - Transmission mode (I, II, III, or IV)
- `label: DabLabel` - Ensemble label (text + short)
- `services: List[DabService]` - List of services in ensemble
- `subchannels: List[DabSubchannel]` - List of subchannels
- `components: List[DabComponent]` - List of components (service↔subchannel links)
- `lto_auto: bool` - Automatic local time offset (default: True)

**Methods:**

##### `add_service(service: DabService) -> None`

Add a service to the ensemble.

**Parameters:**
- `service: DabService` - Service to add

**Raises:**
- `ValueError` - If service with same ID already exists

##### `add_subchannel(subchannel: DabSubchannel) -> None`

Add a subchannel to the ensemble.

**Parameters:**
- `subchannel: DabSubchannel` - Subchannel to add

**Raises:**
- `ValueError` - If subchannel with same ID already exists

##### `add_component(component: DabComponent) -> None`

Add a component (links service to subchannel).

**Parameters:**
- `component: DabComponent` - Component to add

##### `get_service(uid: str) -> Optional[DabService]`

Get service by UID.

**Parameters:**
- `uid: str` - Service UID

**Returns:** Service instance or None

##### `get_subchannel(uid: str) -> Optional[DabSubchannel]`

Get subchannel by UID.

**Parameters:**
- `uid: str` - Subchannel UID

**Returns:** Subchannel instance or None

---

#### `DabService`

DAB service (radio station).

```python
from dabmux.core.mux_elements import DabService

service = DabService(
    uid='service1',
    id=0x5001,
    label_text='Radio One',
    label_short='R1',
    pty=10,  # Pop Music
    language=9  # English
)
```

**Attributes:**

- `uid: str` - Unique identifier (internal use)
- `id: int` - Service ID (16 bits, e.g., `0x5001`)
- `label: DabLabel` - Service label (text + short)
- `pty: int` - Programme Type (0-31)
- `language: int` - Language code (0-127, 9=English)
- `country_id: int` - Country ID (default: 0)

**Programme Types (PTY):**

| Value | Type                  |
|-------|-----------------------|
| 0     | None/Undefined        |
| 1     | News                  |
| 10    | Pop Music             |
| 14    | Serious Classical     |
| 16    | Weather               |
| 29    | Documentary           |

[See full PTY list](../user-guide/configuration/services.md#programme-types)

---

#### `DabSubchannel`

DAB subchannel (data stream).

```python
from dabmux.core.mux_elements import DabSubchannel, SubchannelType

subchannel = DabSubchannel(
    uid='audio1',
    id=0,
    type=SubchannelType.DABAudio,
    bitrate=128,
    start_address=0,
    protection_level=2,
    input_uri='file://audio.mp2'
)
```

**Attributes:**

- `uid: str` - Unique identifier
- `id: int` - Subchannel ID (0-63)
- `type: SubchannelType` - Content type (audio, dabplus, dmb, packet)
- `bitrate: int` - Bitrate in kbps (32-384)
- `start_address: int` - Start address in Capacity Units (0-863 for Mode I)
- `protection_level: int` - Protection level (0-4, higher = stronger)
- `input_uri: str` - Input source URI (file://, udp://, tcp://)

**Subchannel Types:**

```python
class SubchannelType(Enum):
    DABAudio = "audio"        # MPEG Layer II
    DABPlusAudio = "dabplus"  # HE-AAC v2
    DataDmb = "dmb"          # Data (DMB)
    Packet = "packet"        # Packet mode data
```

---

#### `DabComponent`

Component (links service to subchannel).

```python
from dabmux.core.mux_elements import DabComponent

component = DabComponent(
    uid='comp1',
    service_id=0x5001,
    subchannel_id=0,
    type=0  # Audio
)
```

**Attributes:**

- `uid: str` - Unique identifier
- `service_id: int` - Service ID (16 bits)
- `subchannel_id: int` - Subchannel ID (0-63)
- `type: int` - Component type (0=Audio, 1=Data)

---

#### `DabLabel`

DAB label (ensemble/service name).

```python
from dabmux.core.mux_elements import DabLabel

label = DabLabel(
    text='My Radio Station',  # Max 16 chars
    short='MyRadio'            # Max 8 chars
)
```

**Attributes:**

- `text: str` - Long label (max 16 characters)
- `short: str` - Short label (max 8 characters)

**Character encoding:** EBU Latin charset (subset of UTF-8 for common European characters)

---

## Usage Examples

### Creating an Ensemble

```python
from dabmux.core.mux_elements import (
    DabEnsemble, DabService, DabSubchannel, DabComponent,
    SubchannelType, TransmissionMode
)

# Create ensemble
ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    transmission_mode=TransmissionMode.TM_I,
    label_text='My DAB Network',
    label_short='DAB'
)

# Add subchannel (audio stream)
subchannel = DabSubchannel(
    uid='audio1',
    id=0,
    type=SubchannelType.DABAudio,
    bitrate=128,
    start_address=0,
    protection_level=2,
    input_uri='file://audio.mp2'
)
ensemble.add_subchannel(subchannel)

# Add service (radio station)
service = DabService(
    uid='service1',
    id=0x5001,
    label_text='Radio One',
    label_short='R1',
    pty=10,
    language=9
)
ensemble.add_service(service)

# Link service to subchannel
component = DabComponent(
    uid='comp1',
    service_id=0x5001,
    subchannel_id=0,
    type=0
)
ensemble.add_component(component)
```

### Generating ETI Frames

```python
from dabmux.core.eti import EtiFrame

# Create empty frame
frame = EtiFrame.create_empty(mode=1, with_tist=False)

# Set frame count
frame.fc.fct = 42
frame.fc.nst = 3  # 3 subchannels

# Add FIC data (96 bytes for Mode I)
frame.fic_data = b'\x00' * 96

# Add MST data (main service channel)
frame.mst_data = b'\x00' * 5760

# Serialize to binary
frame_bytes = frame.pack()
assert len(frame_bytes) == 6144
```

### Parsing ETI Frames

```python
from dabmux.core.eti import EtiFrame, EtiSync, EtiFC

# Read frame from file
with open('input.eti', 'rb') as f:
    frame_data = f.read(6144)

# Parse SYNC header
sync = EtiSync.unpack(frame_data[0:4])
assert sync.fsync == 0x49C5F8

# Parse FC header
fc = EtiFC.unpack(frame_data[4:8])
print(f"Frame {fc.fct}, Mode {fc.mid}, {fc.nst} subchannels")
```

## See Also

- [Architecture: ETI Frames](../architecture/eti-frames.md) - Detailed frame structure diagrams
- [Configuration Reference](../user-guide/configuration/index.md) - YAML configuration
- [Mux API](mux.md) - DabMultiplexer class
- [Standards](../standards/index.md) - ETSI EN 300 799 compliance
