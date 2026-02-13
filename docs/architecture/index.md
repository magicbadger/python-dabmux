# Architecture Overview

This section explains the internal architecture of python-dabmux with detailed diagrams showing how the system works.

## Key Components

python-dabmux is organized into layers:

1. **Configuration Layer**: Parses YAML and creates ensemble structure
2. **Input Layer**: Handles file and network audio sources
3. **Core Layer**: Multiplexes audio and generates FIGs
4. **Output Layer**: Writes ETI files or sends EDI over network

## Architecture Diagrams

### [System Design](system-design.md)

High-level architecture showing module structure and data flow:

- Configuration → Inputs → Multiplexer → FIG Generation → Outputs
- Module responsibilities
- Interface boundaries

**Mermaid diagram included**

[View System Design →](system-design.md)

### [ETI Frame Structure](eti-frames.md)

Detailed byte layout of ETI frames:

- SYNC, FC, STC headers
- FIC (Fast Information Channel)
- MST (Main Service Transport)
- EOF, TIST

**Mermaid diagram included**

[View ETI Frames →](eti-frames.md)

### [FIG Carousel](fig-carousel.md)

How FIG types rotate based on repetition rates:

- FIG priority system
- Timing (96ms, 1s, etc.)
- Buffer management
- Sequence diagram

**Mermaid diagram included**

[View FIG Carousel →](fig-carousel.md)

### [Data Flow](data-flow.md)

Complete pipeline from inputs to outputs:

- Input buffers → Multiplexer
- FIG generation (parallel)
- Frame assembly
- Output formatting

**Mermaid diagram included**

[View Data Flow →](data-flow.md)

### [EDI Protocol Stack](edi-protocol.md)

Layer-by-layer EDI protocol:

- TAG items (*ptr, deti, estN)
- AF packets
- PFT fragmentation
- UDP/TCP transport

**Mermaid diagram included**

[View EDI Protocol →](edi-protocol.md)

### [Configuration Hierarchy](configuration-hierarchy.md)

Relationship between configuration elements:

- Ensemble → Services → Components → Subchannels → Inputs
- ID linkages
- Tree structure

**Mermaid diagram included**

[View Configuration Hierarchy →](configuration-hierarchy.md)

### [Module Breakdown](modules.md)

Detailed description of each Python module:

- Purpose and responsibilities
- Key classes and functions
- Dependencies
- Usage patterns

[View Module Breakdown →](modules.md)

## Design Principles

### Separation of Concerns

Each module has a clear responsibility:

- **core/**: Data structures only (no business logic)
- **input/**: Input handling only (no multiplexing)
- **output/**: Output handling only (no frame generation)
- **mux.py**: Orchestrates everything

### Type Safety

- Full type annotations on all public APIs
- mypy validation for type correctness
- Clear interfaces between modules

### Testability

- Unit tests for each module (389 tests total)
- Mocking for external dependencies
- Test coverage: 71%

### Extensibility

- Abstract base classes for inputs/outputs
- Plugin-style architecture for FIG types
- Easy to add new features

## Data Structures

### Core Types

```python
# Ensemble configuration
DabEnsemble
  ├─ DabService[]
  ├─ DabSubchannel[]
  └─ DabComponent[]

# ETI frame structures
EtiFrame
  ├─ Sync
  ├─ FrameCharacterization
  ├─ SubChannelStreamChar[]
  ├─ EndOfHeader
  ├─ FastInformationChannel
  ├─ MainServiceTransport
  ├─ EndOfFrame
  └─ TimeStamp (optional)
```

### Input/Output Abstractions

```python
# Input abstraction
class InputBase(ABC):
    def open() -> None
    def read() -> bytes
    def close() -> None

# Output abstraction
class DabOutput(ABC):
    def open() -> None
    def write(data: bytes) -> None
    def close() -> None
```

## Processing Flow

### Initialization

1. Load YAML configuration
2. Parse into DabEnsemble
3. Create DabMultiplexer
4. Initialize inputs and outputs
5. Validate configuration

### Frame Generation

1. **Read audio data** from all inputs
2. **Generate FIGs** for current frame
3. **Encode FIC** (Fast Information Channel)
4. **Populate MST** (Main Service Transport)
5. **Calculate CRCs** for headers and frame
6. **Add TIST** (timestamp) if enabled
7. **Pack frame** to binary

### Output Writing

1. **Serialize frame** to bytes
2. **For file output**: Write to file
3. **For EDI output**: Convert to TAG items → AF packet → PFT (optional) → UDP/TCP

## Key Algorithms

### FIG Carousel Scheduling

FIGs repeat at different rates:
- **FIG 0/0**: Every 96ms (10 frames)
- **FIG 0/1, 0/2**: Every 1 second (~10 frames)
- **FIG 1/0, 1/1**: Every 1 second
- **Other FIGs**: Every 10 seconds

**Algorithm:**
1. Each FIG has a counter
2. Decrement counter each frame
3. When counter reaches 0, FIG is included
4. Reset counter to repetition interval

### Capacity Unit Allocation

Subchannels use Capacity Units (CUs) based on bitrate and protection:

**Formula:**
```
CUs = f(bitrate, protection_level, form)
```

**Allocation:**
1. Sort subchannels by start_address
2. Assign contiguous CU ranges
3. Verify total doesn't exceed mode capacity (864 CUs for Mode I)

### Reed-Solomon FEC

For PFT error correction:

**GF(2^8) arithmetic:**
- Generator polynomial construction
- Systematic encoding
- Parity calculation

**Parameters:**
- (N, K) = (N, K-2M) where M is error recovery capability
- Example: (255, 251) can recover 2 errors

## Performance Characteristics

### CPU Usage

- **Frame generation**: O(N) where N = number of services
- **FIG encoding**: O(F) where F = number of FIG types
- **CRC calculation**: O(L) where L = frame length
- **Overall**: ~10-20% of one core for typical ensemble

### Memory Usage

- **Ensemble config**: ~10 KB
- **Frame buffer**: ~6 KB per frame
- **Input buffers**: Configurable (default: 10 frames per input)
- **Total**: ~5-10 MB for typical operation

### I/O Performance

- **File I/O**: Limited by disk speed
- **Network I/O**: Limited by network bandwidth
- **Bottleneck**: Usually input sources, not python-dabmux

## Thread Safety

python-dabmux is **single-threaded** by design:

- No locks or mutexes needed
- Simpler code and debugging
- Sufficient performance for DAB multiplexing

**For multi-core:** Run multiple instances with different configurations.

## Error Handling

### Validation Layers

1. **Configuration parsing**: YAML syntax, required fields
2. **Ensemble validation**: ID uniqueness, capacity limits
3. **Input validation**: File existence, format checks
4. **Runtime validation**: Buffer underruns, CRC errors

### Graceful Degradation

- Missing input: Zero-filled frames
- Network error: Retry with exponential backoff
- Buffer underrun: Warning logged, continue with available data

## See Also

- [System Design](system-design.md): High-level architecture
- [Data Flow](data-flow.md): Complete processing pipeline
- [Module Breakdown](modules.md): Detailed module descriptions
- [API Reference](../api-reference/index.md): Code documentation
