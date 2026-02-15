# Python DAB Multiplexer

A pure Python implementation of a DAB/DAB+ multiplexer, recreating the functionality of ODR-DabMux.

## Installation

```bash
# Development installation
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick Start

### Super Simple (1 Command!)

Use the simple script to loop any audio file:

```bash
# Loop an MP3 file as a DAB service
python simple_loop.py yourmusic.mp3

# Custom station name and bitrate
python simple_loop.py yourmusic.mp3 --station-name "Rock FM" --bitrate 160

# Stream to network modulator
python simple_loop.py yourmusic.mp3 --edi udp://192.168.1.100:12000
```

See [SIMPLE_EXAMPLES.md](SIMPLE_EXAMPLES.md) for more examples and options.

### Manual Setup (3 steps)

### 1. Prepare Audio

```bash
# Convert any audio to MPEG Layer II (DAB format)
ffmpeg -i input.wav -c:a mp2 -ar 48000 -b:a 128k audio.mp2
```

### 2. Create Configuration

Create `config.yaml`:

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'My First DAB'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    protection:
      level: 2
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'Radio One'

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
```

### 3. Run Multiplexer

```bash
# Generate ETI file
python -m dabmux.cli -c config.yaml -o output.eti

# Or stream over network with EDI + PFT
python -m dabmux.cli -c config.yaml --edi udp://239.1.2.3:12000 --pft
```

**📚 [Full Documentation](https://python-dabmux.readthedocs.io)** | **🚀 [Tutorials](docs/tutorials/index.md)**

## Documentation

**📚 [Complete Documentation](docs/index.md)** - Comprehensive guides, tutorials, and API reference

- **[Getting Started](docs/getting-started/index.md)** - Installation and first multiplex
- **[User Guide](docs/user-guide/index.md)** - CLI reference, configuration, inputs/outputs
- **[Tutorials](docs/tutorials/index.md)** - Step-by-step guides for common scenarios
- **[Architecture](docs/architecture/index.md)** - System design with Mermaid diagrams
- **[Troubleshooting](docs/troubleshooting/index.md)** - Common errors and solutions
- **[FAQ](docs/faq.md)** - Frequently asked questions

## Testing

```bash
# Run all tests with coverage
pytest --cov=dabmux --cov-report=term-missing

# Run specific test categories
pytest tests/unit/core -v        # Core ETI tests
pytest tests/unit/fig -v         # FIG generation tests
pytest tests/unit/edi -v         # EDI protocol tests
```

## Project Structure

```
python-dabmux/
├── src/
│   └── dabmux/        # Source code
│       ├── audio/     # Audio frame parsing (MPEG Layer II, DAB+)
│       ├── core/      # Core data structures (ETI frames, ensemble config)
│       ├── edi/       # EDI protocol (TAG items, PFT, encoder)
│       ├── fec/       # Forward error correction (Reed-Solomon)
│       ├── fig/       # Fast Information Group (FIG) generation
│       ├── input/     # File input abstractions
│       ├── network/   # Network inputs (UDP, TCP)
│       ├── output/    # Output abstractions (file, network, EDI)
│       ├── utils/     # Utilities (CRC, logging, timestamps, statistics)
│       └── mux.py     # Main multiplexer
├── tests/
│   └── unit/          # Unit tests
├── docs/              # Documentation
├── examples/          # Example configurations
└── pyproject.toml     # Project configuration
```

## References

- [ODR-DabMux](https://github.com/Opendigitalradio/ODR-DabMux) - C++ reference implementation
- [ETSI EN 300 799](https://www.etsi.org/deliver/etsi_en/300700_300799/300799/01.02.01_60/en_300799v010201p.pdf) - ETI specification
