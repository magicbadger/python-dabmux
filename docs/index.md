# Python DAB Multiplexer

Welcome to the documentation for **python-dabmux**, a pure Python implementation of a DAB/DAB+ multiplexer that recreates the functionality of ODR-DabMux.

## What is python-dabmux?

python-dabmux is a complete DAB (Digital Audio Broadcasting) multiplexer that combines multiple audio streams into a single DAB ensemble for transmission. It supports both traditional DAB (MPEG Layer II) and DAB+ (HE-AAC v2) audio formats, with full EDI (Ensemble Data Interface) network output capabilities.

## Key Features

- **Complete DAB/DAB+ Support**: Full implementation of ETI frame generation, FIG (Fast Information Group) encoding, and ensemble multiplexing
- **Multiple Input Sources**: File-based inputs (MPEG, raw), UDP/TCP network streaming, with automatic frame parsing and validation
- **Flexible Output Options**: ETI file formats (raw, framed, streamed), EDI network output with UDP/TCP support
- **PFT with FEC**: Protection, Fragmentation and Transport layer with Reed-Solomon forward error correction
- **Network Streaming**: UDP multicast and TCP server inputs for live audio streaming
- **Configuration Management**: YAML-based configuration with validation and comprehensive examples
- **Robust Architecture**: Well-tested (389 tests, 71% coverage), type-annotated, and production-ready

## Project Status

**🎉 python-dabmux is feature-complete!**

All core functionality has been implemented through 6 development phases:

- ✅ **Phase 0**: Foundation (ETI frames, CRC, ensemble configuration)
- ✅ **Phase 1**: Input/Output abstractions
- ✅ **Phase 2**: FIG generation and carousel
- ✅ **Phase 3**: Data input and encoding
- ✅ **Phase 4**: Network inputs and timestamps
- ✅ **Phase 5**: EDI protocol and DAB+ support
- ✅ **Phase 6**: Advanced features and usability

## Quick Start

Get started with python-dabmux in under 15 minutes:

```bash
# Install
pip install python-dabmux

# Create your first multiplex
python -m dabmux.cli -c config.yaml -o output.eti

# Or stream over the network with EDI
python -m dabmux.cli -c config.yaml --edi udp://239.1.2.3:12000 --pft
```

[Get Started →](getting-started/index.md){ .md-button .md-button--primary }

## Documentation Structure

### 📚 For New Users

- **[Getting Started](getting-started/index.md)**: Installation, first multiplex, and basic concepts
- **[Tutorials](tutorials/index.md)**: Hands-on guides for common scenarios
- **[FAQ](faq.md)**: Frequently asked questions

### 📖 For Regular Users

- **[User Guide](user-guide/index.md)**: Comprehensive configuration and CLI reference
- **[Configuration](user-guide/configuration/index.md)**: Complete parameter reference
- **[Troubleshooting](troubleshooting/index.md)**: Common errors and solutions

### 🏗️ For Developers

- **[Architecture](architecture/index.md)**: System design with Mermaid diagrams
- **[API Reference](api-reference/index.md)**: Complete API documentation
- **[Advanced Topics](advanced/index.md)**: Deep dives into FIG types, FEC, and more
- **[Development](development/index.md)**: Contributing, testing, and roadmap

### 📐 For Standards Implementers

- **[Standards](standards/index.md)**: ETSI compliance and references
- **[Glossary](glossary.md)**: DAB terminology and acronyms

## Key Capabilities

### Input Sources

- **File Inputs**: MPEG Layer II files, raw audio, packet data
- **Network Inputs**: UDP unicast/multicast, TCP server connections
- **Audio Formats**: MPEG Layer II (DAB), HE-AAC v2 (DAB+)

### Output Formats

- **ETI Files**: Raw ETI, streamed ETI (with timestamps), framed ETI
- **EDI Network**: UDP/TCP with TAG items, AF packets, optional PFT with FEC
- **Multiple Outputs**: Simultaneous file and network output

### Configuration

- **YAML Configuration**: Human-readable configuration files
- **Validation**: Automatic validation with helpful error messages
- **Examples**: Comprehensive examples for common scenarios

### Advanced Features

- **FIG Carousel**: Automatic rotation of FIG types with configurable timing
- **Character Encoding**: Full EBU Latin to UTF-8 conversion
- **Timestamps**: TIST (Time-Stamp) support for synchronization
- **Statistics**: Input buffer monitoring, underrun/overrun detection
- **Error Protection**: Configurable protection levels (0-4) with shortform/longform

## Why python-dabmux?

- **Pure Python**: Easy to install, modify, and integrate
- **Educational**: Clear code structure for learning DAB standards
- **Well-Tested**: 389 unit tests with 71% code coverage
- **Type-Safe**: Full type annotations with mypy validation
- **Standards-Compliant**: Follows ETSI EN 300 799 and related specifications
- **Production-Ready**: Feature-complete with robust error handling

## Example Usage

### Basic Single Service

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Test Ensemble'
    short: 'Test'

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
      short: 'Radio1'

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
```

Run it:

```bash
python -m dabmux.cli -c config.yaml -o output.eti
```

[More Examples →](user-guide/configuration/examples.md)

## Community and Support

- **GitHub**: [Report issues](https://github.com/python-dabmux/python-dabmux/issues)
- **Documentation**: You're reading it!
- **Examples**: Check the `examples/` directory in the repository

## License

python-dabmux is open source software. See the repository for license details.

---

Ready to get started? Head to the [Installation Guide](getting-started/installation.md) or dive into [Your First Multiplex](getting-started/first-multiplex.md)!
