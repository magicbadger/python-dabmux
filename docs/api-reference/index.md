# API Reference

Complete API documentation for python-dabmux.

## Overview

python-dabmux is organized into several modules, each handling a specific aspect of DAB multiplexing:

- **[core](core.md)**: Core data structures (ETI frames, ensemble configuration)
- **[mux](mux.md)**: Main multiplexer class (`DabMultiplexer`)
- **[config](config.md)**: Configuration parser and validation
- **[input](input.md)**: Input sources (file, UDP, TCP)
- **[output](output.md)**: Output destinations (ETI file, EDI network)
- **[fig](fig.md)**: FIG (Fast Information Group) generation
- **[edi](edi.md)**: EDI (Ensemble Data Interface) protocol
- **[audio](audio.md)**: Audio frame parsing (MPEG Layer II, DAB+)
- **[fec](fec.md)**: Forward error correction (Reed-Solomon)
- **[utils](utils.md)**: Utility functions (CRC, charset, timestamps)

## Quick Start

### Basic Usage

```python
from dabmux.config import load_config
from dabmux.mux import DabMultiplexer
from dabmux.output.file import FileOutput

# Load configuration
ensemble = load_config('config.yaml')

# Create multiplexer
mux = DabMultiplexer(ensemble)

# Generate ETI frame
frame = mux.generate_frame()

# Write to file
output = FileOutput()
output.open('output.eti')
output.write(frame.pack())
output.close()
```

### Creating an Ensemble Programmatically

```python
from dabmux.core.mux_elements import DabEnsemble, DabService, DabSubchannel, DabComponent
from dabmux.core.eti import TransmissionMode

# Create ensemble
ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    transmission_mode=TransmissionMode.MODE_I,
    label_text='My DAB',
    label_short='DAB'
)

# Create subchannel
subchannel = DabSubchannel(
    uid='audio1',
    id=0,
    bitrate=128,
    start_address=0,
    protection_level=2,
    input_uri='file://audio.mp2'
)
ensemble.add_subchannel(subchannel)

# Create service
service = DabService(
    uid='service1',
    id=0x5001,
    label_text='Radio One',
    label_short='R1',
    pty=10,  # Pop Music
    language=9  # English
)
ensemble.add_service(service)

# Create component to link service and subchannel
component = DabComponent(
    uid='comp1',
    service_id=0x5001,
    subchannel_id=0
)
ensemble.add_component(component)
```

## Module Organization

```
dabmux/
├── audio/          # Audio frame parsing
│   ├── mpeg.py    # MPEG Layer II frame parser
│   └── dabplus.py # DAB+ (HE-AAC) frame parser
├── config/         # Configuration
│   ├── parser.py  # YAML configuration parser
│   └── schema.py  # Configuration validation
├── core/           # Core data structures
│   ├── eti.py     # ETI frame structures
│   └── mux_elements.py  # Ensemble, service, subchannel
├── edi/            # EDI protocol
│   ├── encoder.py # EDI encoder
│   ├── tags.py    # EDI TAG items
│   └── pft.py     # PFT (fragmentation + FEC)
├── fec/            # Forward error correction
│   └── reed_solomon.py  # Reed-Solomon encoder
├── fig/            # FIG generation
│   ├── carousel.py  # FIG carousel
│   ├── fic.py      # FIC encoder
│   ├── fig0.py     # FIG Type 0 (MCI)
│   ├── fig1.py     # FIG Type 1 (Labels)
│   └── fig5.py     # FIG Type 5 (FIDC)
├── input/          # Input sources
│   ├── base.py    # Abstract input base class
│   ├── file.py    # File input
│   └── network.py # UDP/TCP network input
├── network/        # Network utilities
│   ├── udp.py     # UDP socket wrapper
│   └── tcp.py     # TCP socket wrapper
├── output/         # Output destinations
│   ├── base.py    # Abstract output base class
│   ├── file.py    # ETI file output
│   └── edi.py     # EDI network output
├── utils/          # Utilities
│   ├── crc.py     # CRC calculations
│   ├── charset.py # EBU Latin character set
│   ├── timestamp.py  # TIST timestamps
│   └── stats.py   # Statistics tracking
└── mux.py          # Main multiplexer
```

## Type Annotations

python-dabmux uses comprehensive type annotations throughout the codebase. All public APIs have type hints that are validated with mypy.

```python
from typing import Optional
from dabmux.core.eti import EtiFrame

def generate_frame(
    frame_number: int,
    enable_tist: bool = False,
    tist_offset: float = 0.0
) -> EtiFrame:
    """Generate an ETI frame."""
    ...
```

## Error Handling

python-dabmux defines custom exceptions for different error types:

```python
from dabmux.config import ConfigurationError
from dabmux.core.eti import EtiError
from dabmux.input.base import InputError

try:
    ensemble = load_config('config.yaml')
except ConfigurationError as e:
    print(f"Configuration error: {e}")

try:
    frame = mux.generate_frame()
except EtiError as e:
    print(f"ETI generation error: {e}")

try:
    data = input_source.read_frame()
except InputError as e:
    print(f"Input error: {e}")
```

## Logging

python-dabmux uses `structlog` for structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("Frame generated",
           frame_number=1234,
           services=3,
           size=6144)
```

### Configure Logging

```python
import logging
import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
```

## Testing

python-dabmux has comprehensive test coverage (71% overall, 90-100% for core modules).

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dabmux --cov-report=term-missing

# Run specific module tests
pytest tests/unit/test_eti.py
pytest tests/unit/fig/
```

### Writing Tests

```python
import pytest
from dabmux.core.eti import EtiFrame, TransmissionMode

def test_eti_frame_creation():
    """Test ETI frame creation."""
    frame = EtiFrame(
        mode=TransmissionMode.MODE_I,
        frame_number=0
    )
    assert frame.mode == TransmissionMode.MODE_I
    assert frame.frame_number == 0
    assert len(frame.pack()) == 6144
```

## Performance Considerations

### Memory Usage

- **ETI frames**: 6144 bytes per frame (Mode I)
- **FIG carousel**: ~10 KB for typical ensemble
- **Input buffers**: Configurable per input source
- **Total**: Typically < 50 MB for typical ensemble

### CPU Usage

- **Frame generation**: 10-20% of one CPU core @ 10.4 fps (Mode I)
- **FIG generation**: < 5% overhead
- **PFT with FEC**: +10-15% overhead
- **Total**: Suitable for Raspberry Pi 3+

### Optimization Tips

1. **Use generator pattern for continuous operation:**
   ```python
   while True:
       frame = mux.generate_frame()
       output.write(frame.pack())
   ```

2. **Reuse buffers where possible:**
   ```python
   frame_buffer = bytearray(6144)
   frame.pack_into(frame_buffer)
   ```

3. **Minimize FIG types:**
   ```python
   # Only generate essential FIGs
   fic_encoder.enable_fig_types([0, 1])
   ```

## Common Patterns

### Continuous Multiplexing

```python
from dabmux.mux import DabMultiplexer
from dabmux.output.file import FileOutput
import signal

running = True

def signal_handler(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, signal_handler)

mux = DabMultiplexer(ensemble)
output = FileOutput()
output.open('output.eti')

try:
    while running:
        frame = mux.generate_frame()
        output.write(frame.pack())
finally:
    output.close()
```

### Network Streaming

```python
from dabmux.output.edi import EdiOutput
from dabmux.edi.pft import PFTConfig

# Configure PFT with FEC
pft_config = PFTConfig(
    fec=True,
    fec_m=2,
    max_fragment_size=1400
)

# Create EDI output
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
        # EDI encoding happens internally
        output.write_frame(frame)
finally:
    output.close()
```

### Custom Input Source

```python
from dabmux.input.base import InputSource
from typing import Optional

class CustomInput(InputSource):
    """Custom input source implementation."""

    def open(self) -> None:
        """Open input source."""
        # Initialize your source
        pass

    def close(self) -> None:
        """Close input source."""
        # Cleanup
        pass

    def read_frame(self, frame_size: int) -> Optional[bytes]:
        """Read one audio frame."""
        # Return frame data or None if no data available
        return self._get_next_frame()

    def seek(self, position: int) -> None:
        """Seek to position (optional)."""
        pass
```

## See Also

- [User Guide](../user-guide/index.md): High-level usage documentation
- [Tutorials](../tutorials/index.md): Step-by-step guides
- [Architecture](../architecture/index.md): System design and diagrams
- [Development](../development/index.md): Contributing guidelines
