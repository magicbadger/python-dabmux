# Output Module

Output destinations for ETI frames and EDI streams.

## Module: `dabmux.output`

Provides output implementations for writing ETI frames to files and streaming over networks.

## Base Class: `DabOutput`

Abstract base class for all outputs.

### Module: `dabmux.output.base`

```python
from abc import ABC, abstractmethod

class DabOutput(ABC):
    """Abstract base class for outputs."""

    @abstractmethod
    def open(self, *args, **kwargs) -> None:
        """Open the output."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the output."""
        pass

    @abstractmethod
    def write(self, data: bytes) -> None:
        """Write data to output."""
        pass

    @abstractmethod
    def get_info(self) -> str:
        """Get output information string."""
        pass
```

## File Output

### Module: `dabmux.output.file`

### Class: `FileOutput`

Write ETI frames to files in various formats.

```python
from dabmux.output.file import FileOutput, EtiFileType

# Create file output
output = FileOutput()
output.open('output.eti', file_type=EtiFileType.FRAMED)

# Write frame
output.write(frame_bytes)

output.close()
```

#### Constructor

##### `__init__()`

Create a file output instance.

**Example:**
```python
output = FileOutput()
```

#### Methods

##### `open(file_path: str | Path, file_type: EtiFileType = EtiFileType.FRAMED) -> None`

Open file for writing.

**Parameters:**
- `file_path: str | Path` - Output file path
- `file_type: EtiFileType` - File format (default: FRAMED)

**Raises:**
- `PermissionError` - If file can't be created
- `OSError` - If file operation fails

**Example:**
```python
output = FileOutput()
output.open('output.eti', file_type=EtiFileType.RAW)
```

##### `close() -> None`

Close output file.

**Example:**
```python
output.close()
```

##### `write(data: bytes) -> None`

Write ETI frame to file.

**Parameters:**
- `data: bytes` - ETI frame data (6144 or 6148 bytes)

**Example:**
```python
frame_bytes = frame.pack()
output.write(frame_bytes)
```

##### `get_info() -> str`

Get output information.

**Returns:** String describing output (e.g., "File: output.eti")

---

### Enum: `EtiFileType`

ETI file format types.

```python
from enum import Enum

class EtiFileType(Enum):
    RAW = 1      # Raw ETI frames
    STREAMED = 2 # Streamed ETI (with timing)
    FRAMED = 3   # Framed ETI (8-byte aligned)
```

**Format descriptions:**

| Type | Description | Use Case |
|------|-------------|----------|
| `RAW` | Plain ETI frames, no wrapper | Maximum compatibility, smallest files |
| `STREAMED` | Frames with timestamps | Timed playback, synchronization |
| `FRAMED` | 8-byte aligned with delimiters | Easy parsing, frame boundaries |

**Example:**
```python
from dabmux.output.file import FileOutput, EtiFileType

# Raw format
output = FileOutput()
output.open('output.eti', file_type=EtiFileType.RAW)

# Framed format (default)
output = FileOutput()
output.open('output.eti')  # Uses FRAMED by default
```

---

## Network Output (EDI)

### Module: `dabmux.output.edi`

### Class: `EdiOutput`

Stream ETI frames over network using EDI protocol.

```python
from dabmux.output.edi import EdiOutput
from dabmux.edi.pft import PFTConfig

# Create EDI output with PFT
pft_config = PFTConfig(fec=True, fec_m=2)
output = EdiOutput(
    dest_addr='239.1.2.3',
    dest_port=12000,
    enable_pft=True,
    pft_config=pft_config
)
output.open()

# Write frame (automatically encoded to EDI)
output.write_frame(frame)

output.close()
```

#### Constructor

##### `__init__(dest_addr: str, dest_port: int, enable_pft: bool = False, pft_config: Optional[PFTConfig] = None)`

Create an EDI network output.

**Parameters:**
- `dest_addr: str` - Destination IP address (unicast or multicast)
- `dest_port: int` - Destination UDP port
- `enable_pft: bool` - Enable PFT (Protection, Fragmentation and Transport)
- `pft_config: Optional[PFTConfig]` - PFT configuration (required if `enable_pft=True`)

**Example:**
```python
# Basic EDI (no PFT)
output = EdiOutput('239.1.2.3', 12000)

# EDI with PFT
pft_config = PFTConfig(fec=True, fec_m=2, max_fragment_size=1400)
output = EdiOutput('239.1.2.3', 12000, enable_pft=True, pft_config=pft_config)
```

#### Methods

##### `open() -> None`

Open UDP socket for EDI streaming.

**Raises:**
- `OSError` - If socket can't be created

**Example:**
```python
output = EdiOutput('239.1.2.3', 12000)
output.open()
```

##### `close() -> None`

Close UDP socket.

##### `write(data: bytes) -> None`

Write raw data to network (not recommended, use `write_frame`).

##### `write_frame(frame: EtiFrame) -> None`

Encode ETI frame to EDI and transmit.

**Parameters:**
- `frame: EtiFrame` - ETI frame to transmit

**Behavior:**
- Encodes frame to EDI TAG items
- Wraps in AF packet
- Applies PFT if enabled (fragmentation + optional FEC)
- Transmits via UDP

**Example:**
```python
from dabmux.mux import DabMultiplexer

mux = DabMultiplexer(ensemble)
output = EdiOutput('239.1.2.3', 12000, enable_pft=True, pft_config=pft_config)
output.open()

try:
    while running:
        frame = mux.generate_frame()
        output.write_frame(frame)
finally:
    output.close()
```

##### `get_info() -> str`

Get output information.

**Returns:** String describing output (e.g., "EDI: 239.1.2.3:12000 (PFT enabled)")

---

## PFT Configuration

### Module: `dabmux.edi.pft`

### Class: `PFTConfig`

Configuration for PFT (Protection, Fragmentation and Transport).

```python
from dabmux.edi.pft import PFTConfig

# PFT with FEC
pft_config = PFTConfig(
    fec=True,
    fec_m=2,
    max_fragment_size=1400
)
```

#### Constructor

##### `__init__(fec: bool = False, fec_m: int = 0, max_fragment_size: int = 1400)`

Create PFT configuration.

**Parameters:**
- `fec: bool` - Enable Forward Error Correction (Reed-Solomon)
- `fec_m: int` - Max recoverable fragments (0-20, higher = more recovery)
- `max_fragment_size: int` - Maximum fragment size in bytes (default: 1400)

**Example:**
```python
# No FEC (fragmentation only)
pft_config = PFTConfig(fec=False, max_fragment_size=1400)

# With FEC (can recover 2 lost fragments)
pft_config = PFTConfig(fec=True, fec_m=2, max_fragment_size=1400)

# Strong FEC (can recover 5 lost fragments)
pft_config = PFTConfig(fec=True, fec_m=5, max_fragment_size=1200)
```

#### Attributes

- `fec: bool` - FEC enabled
- `fec_m: int` - FEC recovery parameter
- `max_fragment_size: int` - Fragment size limit

---

## Usage Examples

### Writing to File (Raw)

```python
from dabmux.output.file import FileOutput, EtiFileType
from dabmux.mux import DabMultiplexer

# Setup
mux = DabMultiplexer(ensemble)
output = FileOutput()
output.open('output.eti', file_type=EtiFileType.RAW)

try:
    # Generate and write 1000 frames
    for _ in range(1000):
        frame = mux.generate_frame()
        output.write(frame.pack())
finally:
    output.close()
```

### Writing to File (Framed)

```python
from dabmux.output.file import FileOutput, EtiFileType

# Framed format (default)
output = FileOutput()
output.open('output.eti')  # Uses FRAMED by default

try:
    for _ in range(1000):
        frame = mux.generate_frame()
        output.write(frame.pack())
finally:
    output.close()
```

### Streaming EDI (Basic)

```python
from dabmux.output.edi import EdiOutput

# Create output
output = EdiOutput('239.1.2.3', 12000)
output.open()

try:
    while running:
        frame = mux.generate_frame()
        output.write_frame(frame)
finally:
    output.close()
```

### Streaming EDI with PFT + FEC

```python
from dabmux.output.edi import EdiOutput
from dabmux.edi.pft import PFTConfig

# Configure PFT with strong FEC
pft_config = PFTConfig(
    fec=True,
    fec_m=3,  # Can recover 3 lost fragments
    max_fragment_size=1400
)

# Create output
output = EdiOutput(
    dest_addr='239.1.2.3',
    dest_port=12000,
    enable_pft=True,
    pft_config=pft_config
)
output.open()

try:
    while running:
        frame = mux.generate_frame()
        output.write_frame(frame)
finally:
    output.close()
```

### Multiple Outputs

```python
from dabmux.output.file import FileOutput
from dabmux.output.edi import EdiOutput

# Create file output
file_output = FileOutput()
file_output.open('archive.eti')

# Create network output
edi_output = EdiOutput('239.1.2.3', 12000)
edi_output.open()

try:
    # Write to both outputs
    while running:
        frame = mux.generate_frame()
        frame_bytes = frame.pack()

        # Write to file
        file_output.write(frame_bytes)

        # Write to network
        edi_output.write_frame(frame)
finally:
    file_output.close()
    edi_output.close()
```

### Context Manager Pattern

```python
from contextlib import closing

with closing(FileOutput()) as output:
    output.open('output.eti')
    for _ in range(100):
        frame = mux.generate_frame()
        output.write(frame.pack())
    # Automatically closed
```

## Custom Output

### Creating a Custom Output

```python
from dabmux.output.base import DabOutput

class CustomOutput(DabOutput):
    """Custom output destination."""

    def __init__(self, target: str):
        self.target = target

    def open(self, *args, **kwargs) -> None:
        """Initialize output."""
        # Setup custom output
        pass

    def close(self) -> None:
        """Cleanup output."""
        # Teardown
        pass

    def write(self, data: bytes) -> None:
        """Write data to output."""
        # Process and output data
        pass

    def get_info(self) -> str:
        """Get output description."""
        return f"Custom: {self.target}"
```

### Using Custom Output

```python
# Create and use
custom_output = CustomOutput('destination')
custom_output.open()

try:
    frame = mux.generate_frame()
    custom_output.write(frame.pack())
finally:
    custom_output.close()
```

## Performance Considerations

### File Output

- **Buffering**: Use OS buffering (automatic)
- **Format**: RAW is fastest and smallest
- **I/O**: Sequential writes are fast

### Network Output

- **UDP overhead**: ~28 bytes per packet (IP + UDP headers)
- **PFT overhead**: ~10-20% additional bandwidth
- **FEC overhead**: Depends on `fec_m` parameter
- **Fragmentation**: Adjust `max_fragment_size` to match MTU

### Bandwidth Calculation

```
# Without PFT
Bandwidth = bitrate × 1.15

# With PFT (no FEC)
Bandwidth = bitrate × 1.25

# With PFT + FEC (m=2)
Bandwidth = bitrate × 1.40
```

**Example:**
- 6 services × 128 kbps = 768 kbps
- With PFT + FEC (m=2): ~1075 kbps network traffic

## Error Handling

```python
from dabmux.output.file import FileOutput
from dabmux.output.edi import EdiOutput

# File output errors
try:
    output = FileOutput()
    output.open('/read-only/output.eti')
except PermissionError:
    print("Permission denied")
except OSError as e:
    print(f"I/O error: {e}")

# Network output errors
try:
    output = EdiOutput('239.1.2.3', 12000)
    output.open()
except OSError as e:
    print(f"Network error: {e}")
```

## See Also

- [Input Module](input.md) - Input sources
- [User Guide: Outputs](../user-guide/outputs/index.md) - Detailed output guide
- [EDI Protocol](../architecture/edi-protocol.md) - EDI protocol details
- [PFT Fragmentation](../user-guide/outputs/pft-fragmentation.md) - PFT guide
