# Multiplexer Module

Main multiplexer class that combines audio/data streams into ETI frames.

## Module: `dabmux.mux`

### Class: `DabMultiplexer`

The core multiplexer that generates ETI frames from ensemble configuration and input sources.

```python
from dabmux.config import load_config
from dabmux.mux import DabMultiplexer

# Load ensemble configuration
ensemble = load_config('config.yaml')

# Create multiplexer
mux = DabMultiplexer(ensemble)

# Generate frames
frame = mux.generate_frame()
```

## Constructor

### `__init__(ensemble: DabEnsemble)`

Create a new multiplexer instance.

**Parameters:**
- `ensemble: DabEnsemble` - Ensemble configuration with services, subchannels, and components

**Example:**
```python
from dabmux.core.mux_elements import DabEnsemble
from dabmux.mux import DabMultiplexer

ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    transmission_mode=1,
    label_text='My DAB'
)
mux = DabMultiplexer(ensemble)
```

## Attributes

### `ensemble: DabEnsemble`

The ensemble configuration (read-only after initialization).

**Type:** `DabEnsemble`

**Example:**
```python
print(f"Ensemble: {mux.ensemble.label.text}")
print(f"Services: {len(mux.ensemble.services)}")
```

### `frame_count: int`

Current frame count (increments with each generated frame).

**Type:** `int`

**Range:** 0-255 (wraps around)

**Example:**
```python
frame = mux.generate_frame()
print(f"Generated frame #{mux.frame_count}")
```

### `fic_encoder: FICEncoder`

Fast Information Channel encoder instance.

**Type:** `FICEncoder`

**Example:**
```python
fic_data = mux.fic_encoder.encode_fic(frame_number=0)
```

## Methods

### `generate_frame() -> EtiFrame`

Generate a single ETI frame.

Reads data from all configured inputs, generates FIC (Fast Information Channel) data containing service information, and assembles a complete ETI frame.

**Returns:** Complete `EtiFrame` ready for output

**Raises:**
- `RuntimeError` - If frame generation fails
- `InputError` - If input source fails to provide data

**Example:**
```python
# Generate one frame
frame = mux.generate_frame()
assert len(frame.pack()) == 6144

# Frame count auto-increments
assert mux.frame_count == 1
```

**Frame Structure:**

The generated frame contains:

1. **SYNC** (4 bytes) - Frame synchronization
2. **FC** (4 bytes) - Frame characterization
3. **STC** (4 bytes × N) - Subchannel headers
4. **EOH** (4 bytes) - End of header + CRC
5. **FIC** (96 bytes Mode I) - Fast Information Channel
6. **MST** (variable) - Main Service Channel (audio/data)
7. **EOF** (4 bytes) - End of frame + CRC
8. **TIST** (4 bytes, optional) - Timestamp

**Timing:**

- Mode I: One frame every 96 ms (10.416̄ frames/second)
- Mode II: One frame every 24 ms (41.6̄ frames/second)
- Mode III: One frame every 24 ms (41.6̄ frames/second)
- Mode IV: One frame every 96 ms (10.416̄ frames/second)

---

### `add_input(subchannel_uid: str, input_source: InputBase) -> None`

Register an input source for a subchannel.

**Parameters:**
- `subchannel_uid: str` - UID of the subchannel (must exist in ensemble)
- `input_source: InputBase` - Input source instance

**Raises:**
- `ValueError` - If subchannel doesn't exist or input already registered

**Example:**
```python
from dabmux.input.file import FileInput

# Create input for audio subchannel
input_source = FileInput('audio.mp2')
input_source.open()

# Register input
mux.add_input('audio1', input_source)
```

---

### `add_output(output: DabOutput) -> None`

Register an output destination.

**Parameters:**
- `output: DabOutput` - Output destination instance

**Example:**
```python
from dabmux.output.file import FileOutput

# Create file output
output = FileOutput()
output.open('output.eti')

# Register output
mux.add_output(output)
```

**Note:** Outputs are registered but not automatically written to. Use them in your main loop:

```python
while running:
    frame = mux.generate_frame()
    for output in mux.outputs:
        output.write(frame.pack())
```

---

## Complete Usage Example

### Basic Single-Service Multiplex

```python
from dabmux.config import load_config
from dabmux.mux import DabMultiplexer
from dabmux.output.file import FileOutput

# Load configuration
ensemble = load_config('config.yaml')

# Create multiplexer
mux = DabMultiplexer(ensemble)

# Create output
output = FileOutput()
output.open('output.eti')

try:
    # Generate 100 frames
    for _ in range(100):
        frame = mux.generate_frame()
        output.write(frame.pack())

    print(f"Generated {mux.frame_count} frames")

finally:
    output.close()
```

### Continuous Operation

```python
import signal
from dabmux.mux import DabMultiplexer
from dabmux.output.file import FileOutput

running = True

def signal_handler(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, signal_handler)

# Setup
mux = DabMultiplexer(ensemble)
output = FileOutput()
output.open('output.eti')

try:
    print("Generating frames... Press Ctrl+C to stop")

    while running:
        frame = mux.generate_frame()
        output.write(frame.pack())

        # Optional: Add timing to match real-time
        # time.sleep(0.096)  # 96ms for Mode I

    print(f"\nGenerated {mux.frame_count} frames")

finally:
    output.close()
```

### Multiple Outputs

```python
from dabmux.mux import DabMultiplexer
from dabmux.output.file import FileOutput
from dabmux.output.edi import EdiOutput
from dabmux.edi.pft import PFTConfig

# Create multiplexer
mux = DabMultiplexer(ensemble)

# Create file output
file_output = FileOutput()
file_output.open('output.eti')

# Create network output with PFT
pft_config = PFTConfig(fec=True, fec_m=2)
edi_output = EdiOutput(
    dest_addr='239.1.2.3',
    dest_port=12000,
    enable_pft=True,
    pft_config=pft_config
)
edi_output.open()

# Register both outputs
mux.add_output(file_output)
mux.add_output(edi_output)

try:
    while running:
        frame = mux.generate_frame()

        # Write to both outputs
        for output in mux.outputs:
            if isinstance(output, FileOutput):
                output.write(frame.pack())
            elif isinstance(output, EdiOutput):
                output.write_frame(frame)

finally:
    file_output.close()
    edi_output.close()
```

### With Timestamps (TIST)

```python
from dabmux.mux import DabMultiplexer
from dabmux.core.eti import EtiTIST
from datetime import datetime

# Enable TIST in ensemble configuration
ensemble.enable_tist = True
ensemble.tist_offset = 0.0  # Offset in milliseconds

mux = DabMultiplexer(ensemble)

# Generate frame with timestamp
frame = mux.generate_frame()

# TIST is automatically added if enabled
if frame.tist:
    print(f"Frame timestamp: {frame.tist.tist}")

# Frame size includes TIST
assert len(frame.pack()) == 6148  # 6144 + 4 for TIST
```

### Error Handling

```python
from dabmux.mux import DabMultiplexer
from dabmux.input.base import InputError
from dabmux.core.eti import EtiError

mux = DabMultiplexer(ensemble)

try:
    frame = mux.generate_frame()
except InputError as e:
    print(f"Input error: {e}")
    # Handle missing input data
except EtiError as e:
    print(f"ETI generation error: {e}")
    # Handle frame generation error
except RuntimeError as e:
    print(f"Multiplexer error: {e}")
    # Handle general multiplexer error
```

## Internal Operation

### Frame Generation Pipeline

```mermaid
graph LR
    A[generate_frame] --> B[Create Empty Frame]
    B --> C[Generate FIC Data]
    C --> D[Read Subchannel Data]
    D --> E[Assemble MST]
    E --> F[Calculate CRCs]
    F --> G[Return Frame]
```

1. **Create empty frame** based on transmission mode
2. **Update frame count** (FCT field)
3. **Generate FIC data** using FICEncoder
4. **Read audio/data** from registered inputs
5. **Assemble Main Service Channel** (MST)
6. **Calculate CRCs** for header and data
7. **Return complete frame**

### FIC Generation

The multiplexer uses a `FICEncoder` to generate Fast Information Channel data. The FIC carousel rotates through different FIG (Fast Information Group) types:

- **FIG 0/0**: Ensemble configuration (every frame)
- **FIG 0/1**: Subchannel organization (every 1 second)
- **FIG 0/2**: Service organization (every 1 second)
- **FIG 1/0**: Service labels (every 2 seconds)
- **FIG 1/1**: Subchannel labels (every 2 seconds)

See [FIG Carousel](../architecture/fig-carousel.md) for detailed diagram.

### Input Management

Inputs are read in subchannel ID order:

```python
for subchannel in sorted(ensemble.subchannels, key=lambda s: s.id):
    if subchannel.uid in mux.inputs:
        input_source = mux.inputs[subchannel.uid]
        data = input_source.read_frame(frame_size)
        # Add to MST
```

If an input has no data available, the subchannel is filled with silence/padding.

## Performance

### Memory Usage

- **Per frame**: ~6-7 KB (6144 bytes frame + overhead)
- **FIC encoder**: ~10 KB (carousel state)
- **Input buffers**: Varies by input type
- **Total steady state**: < 50 MB

### CPU Usage

Typical CPU usage on modern hardware:

- **Frame generation**: < 1ms (Mode I)
- **FIC encoding**: < 0.1ms
- **CRC calculation**: < 0.05ms
- **Total**: 10-20% of one core @ real-time speed

### Optimization Tips

1. **Reuse frame buffers:**
   ```python
   frame_buffer = bytearray(6144)
   while running:
       frame = mux.generate_frame()
       frame.pack_into(frame_buffer)
       output.write(frame_buffer)
   ```

2. **Minimize FIG types:**
   ```python
   mux.fic_encoder.set_enabled_figs([0, 1])  # Only essential FIGs
   ```

3. **Batch output writes:**
   ```python
   buffer = bytearray(6144 * 100)  # 100 frames
   for i in range(100):
       frame = mux.generate_frame()
       frame.pack_into(buffer[i*6144:(i+1)*6144])
   output.write(buffer)  # Single write
   ```

## Thread Safety

`DabMultiplexer` is **not thread-safe**. Do not call `generate_frame()` from multiple threads simultaneously.

For multi-threaded applications, use one multiplexer per thread or add locking:

```python
import threading

lock = threading.Lock()

def generate_worker():
    with lock:
        frame = mux.generate_frame()
        # Process frame
```

## Limitations

- **Single multiplexer per ensemble**: Each instance maintains frame count and state
- **Sequential operation**: Frames must be generated in order
- **Input synchronization**: All inputs must provide data when requested
- **No frame buffering**: Frames are generated on-demand, not buffered

## See Also

- [Core API](core.md) - ETI frame structures and ensemble configuration
- [Input API](input.md) - Input source implementations
- [Output API](output.md) - Output destination implementations
- [FIC API](fig.md) - Fast Information Channel encoding
- [Architecture: System Design](../architecture/system-design.md) - High-level architecture
- [Architecture: Data Flow](../architecture/data-flow.md) - Input to output pipeline
