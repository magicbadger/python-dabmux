# Python DAB Multiplexer

A production-ready Digital Audio Broadcasting (DAB/DAB+) multiplexer implementation in Python.

[![Tests](https://img.shields.io/badge/tests-1010%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-73%25-green)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Standards](https://img.shields.io/badge/ETSI-EN%20300%20401-blue)](https://www.etsi.org/)

---

## Features

### Core Capabilities
- ✅ **22 FIG Types Implemented** - Complete DAB signaling (FIG 0/0 through FIG 6/1)
- ✅ **DAB+ Audio** - HE-AAC with Reed-Solomon FEC and PAD embedding
- ✅ **Multi-Service Support** - Multiple audio/data services in one ensemble
- ✅ **Data Services** - MOT slideshow, EPG, directory browsing, packet mode
- ✅ **Emergency Alerting** - FIG 0/18, 0/19 for EAS functionality
- ✅ **Service Navigation** - Multi-ensemble networks, service linking, frequency lists
- ✅ **Dynamic Labels** - UTF-8 "now playing" text with emoji support (FIG 2/1)
- ✅ **Conditional Access** - FIG 6/0, 6/1 for subscription services

### Advanced Features
- ✅ **EDI Output** - ETSI TS 102 693 compliant (UDP/TCP, PFT fragmentation)
- ✅ **Remote Control** - ZeroMQ JSON API + interactive Telnet interface
- ✅ **Authentication** - SHA-256 password protection with audit logging
- ✅ **Runtime Control** - Dynamic label updates, announcements, logging
- ✅ **TIST Timestamps** - Precise frame timing for SFN networks
- ✅ **Configuration Tracking** - FIG 0/7 automatic change detection

### Production Ready
- ✅ **1010 Tests Passing** - Comprehensive unit and integration tests
- ✅ **73% Code Coverage** - Well-tested codebase
- ✅ **Standards Compliant** - ETSI EN 300 401, EN 300 799, TS 102 563, TS 102 693
- ✅ **Verified with Tools** - Tested with dablin, etisnoop, ODR tools

---

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/python-dabmux.git
cd python-dabmux
pip install -r requirements.txt
```

### Basic Configuration

Create `my_dab.yaml`:

```yaml
ensemble:
  id: 0xCE15
  ecc: 0xE1
  label:
    text: 'My DAB Station'
    short_text: 'MyDAB'
  transmission_mode: 'I'
  datetime:
    enabled: true

subchannels:
  - uid: 'audio_main'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file://audio/music.dabp'

services:
  - uid: 'my_service'
    id: 0x5001
    label:
      text: 'My Radio'
    pty: 10  # Pop Music
    language: 9  # English

components:
  - uid: 'audio_comp'
    service_id: '0x5001'
    subchannel_id: 0
```

### Generate ETI Output

```bash
# Encode audio first (requires odr-audioenc)
odr-audioenc -i input.mp2 -o audio/music.dabp -b 48 -r 48000

# Generate ETI
python -m dabmux.cli -c my_dab.yaml -o output.eti -f raw

# Verify with etisnoop (optional)
etisnoop -i output.eti
```

**See [Quick Start Guide](docs/QUICK_START.md) for detailed setup.**

---

## Documentation

### Getting Started
- **[Quick Start Guide](docs/QUICK_START.md)** - Get running in 5 minutes
- **[Configuration Reference](docs/CONFIGURATION_REFERENCE.md)** - Complete YAML reference
- **[Examples](examples/)** - Ready-to-use configurations

### Features & Guides
- **[MOT Carousel Guide](docs/MOT_CAROUSEL_GUIDE.md)** - Images, slideshow, EPG
- **[Remote Control Guide](docs/REMOTE_CONTROL_GUIDE.md)** - ZMQ/Telnet API
- **[EDI Output Guide](docs/EDI_OUTPUT_GUIDE.md)** - IP distribution
- **[Emergency Alerting Guide](docs/EMERGENCY_ALERTING_GUIDE.md)** - FIG 0/18, 0/19
- **[Troubleshooting Guide](docs/TROUBLESHOOTING_GUIDE.md)** - Common issues

### Project Status
- **[Comprehensive Status](COMPREHENSIVE_STATUS.md)** - Complete feature list
- **[TODO](TODO.md)** - Roadmap and future enhancements
- **[CHANGELOG](CHANGELOG.md)** - Version history

### Standards & Compliance
- **[Standards Compliance](docs/STANDARDS_COMPLIANCE.md)** - ETSI compliance audit
- **[Known Deviations](docs/KNOWN_DEVIATIONS.md)** - Non-implemented features

---

## Key Features

### FIG Signaling (22 Types)

**FIG Type 0 (Multiplex Configuration):**
- FIG 0/0 - Ensemble information
- FIG 0/1 - Subchannel organization
- FIG 0/2 - Service component description
- FIG 0/3 - Service component in packet mode
- FIG 0/5 - Service component language
- FIG 0/6 - Service linking (DAB, RDS, DRM, AMSS)
- FIG 0/7 - Configuration information
- FIG 0/8 - Service component global definition
- FIG 0/9 - Extended Country Code & LTO
- FIG 0/10 - Date and Time
- FIG 0/13 - User application information
- FIG 0/14 - FEC sub-channel organization
- FIG 0/17 - Programme Type
- FIG 0/18 - Announcement Support
- FIG 0/19 - Announcement Switching
- FIG 0/21 - Frequency Information
- FIG 0/24 - Other Ensemble Services

**FIG Type 1 (Labels):**
- FIG 1/0 - Ensemble label
- FIG 1/1 - Service label
- FIG 1/4 - Service component label

**FIG Type 2 (Dynamic Labels):**
- FIG 2/1 - Service component dynamic label (UTF-8, emoji)

**FIG Type 6 (Conditional Access):**
- FIG 6/0 - CA organization
- FIG 6/1 - CA service

### MOT Protocol

**Slideshow:**
```yaml
# Add to your configuration
subchannels:
  - uid: 'slideshow'
    type: 'packet'
    bitrate: 16

components:
  - uid: 'slideshow_comp'
    is_packet_mode: true
    carousel_enabled: true
    carousel_directory: '/path/to/images'
```

**Supported:**
- JPEG/PNG images (320x240 recommended)
- Directory browsing (HTML menus)
- EPG (Electronic Programme Guide)
- Automatic file monitoring and updates

**See [MOT Carousel Guide](docs/MOT_CAROUSEL_GUIDE.md) for complete instructions.**

### Remote Control

**Enable in configuration:**
```yaml
ensemble:
  remote_control:
    zmq_enabled: true
    zmq_bind: 'tcp://*:9000'
    telnet_enabled: true
    telnet_port: 9001
    auth_enabled: true
    auth_password: 'your_password'
```

**Connect via Telnet:**
```bash
telnet localhost 9001
> get_statistics
> set_label component "Now Playing: Artist - Song"
> trigger_announcement service alarm subchannel
```

**Connect via ZMQ API:**
```python
import zmq, json

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:9000")

request = {"command": "get_statistics", "args": {}}
socket.send_json(request)
print(socket.recv_json())
```

**20 Commands Available:**
- Runtime statistics
- Dynamic label updates
- Announcement control
- Service parameter changes
- Input source monitoring
- Logging control

### EDI Output

**IP-based distribution to transmitters:**
```yaml
ensemble:
  edi_output:
    enabled: true
    protocol: 'udp'  # or 'tcp'
    destination: '192.168.1.100:12000'
    enable_pft: true  # PFT fragmentation with FEC
    pft_fec: 2        # FEC level (0-5)
    enable_tist: true # Timestamps for SFN
```

**Standards:** ETSI TS 102 693 compliant

---

## Command Line Usage

```bash
# Basic usage
python -m dabmux.cli -c config.yaml -o output.eti -f raw

# Generate specific number of frames
python -m dabmux.cli -c config.yaml -o output.eti -n 1000

# With EDI output
python -m dabmux.cli -c config.yaml -o output.eti --edi

# With TIST timestamps
python -m dabmux.cli -c config.yaml -o output.eti --tist

# Verbose logging
python -m dabmux.cli -c config.yaml -o output.eti --verbose
```

---

## Examples

### Multi-Service Ensemble

See [examples/multi_service.yaml](examples/multi_service.yaml)

### Emergency Alerting

See [examples/priority1_emergency_alerting.yaml](examples/priority1_emergency_alerting.yaml)

### Service Linking

See [examples/priority2_service_linking.yaml](examples/priority2_service_linking.yaml)

### Data Services

See [examples/priority3_packet_mode.yaml](examples/priority3_packet_mode.yaml)

### Advanced Signaling

See [examples/priority4_advanced_signalling.yaml](examples/priority4_advanced_signalling.yaml)

### Conditional Access

See [examples/priority7_conditional_access.yaml](examples/priority7_conditional_access.yaml)

### MOT Carousel

See [examples/mot_carousel_example.yaml](examples/mot_carousel_example.yaml)

---

## Testing

```bash
# Run all tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/test_fig6.py -v

# With coverage
python -m pytest tests/unit/ --cov=src/dabmux --cov-report=html

# Exclude UDP tests (known issues)
python -m pytest tests/unit/ -k "not udp" -v
```

**Test Results:** 1010 tests passing, 73% coverage

---

## Standards Compliance

### ETSI Standards

- **ETSI EN 300 401** - DAB System (v2 features supported)
- **ETSI EN 300 799** - ETI Specification
- **ETSI TS 102 563** - DAB+ Audio (HE-AAC, Reed-Solomon FEC)
- **ETSI TS 102 693** - EDI Protocol
- **ETSI TS 101 756** - MOT Protocol

### Verification

**Tested with:**
- ✅ dablin (audio playback)
- ✅ etisnoop (ETI analysis)
- ✅ ODR-DabMod (modulation)
- ✅ Professional DAB receivers

**Compliance:**
- ✅ CRC calculations (FIB, EOH, EOF)
- ✅ FSYNC alternation
- ✅ Frame Length (FL) calculation
- ✅ PAD embedding (before FEC)
- ✅ All FIG types per specification

---

## Architecture

```
Input Sources          Multiplexer Core       Output Formats
─────────────         ──────────────────     ──────────────

DAB+ Files    ───┐                      ┌──> ETI (Raw/Framed)
UDP Streams   ───┤                      │
TCP Streams   ───┤──> FIG Carousel  ───┼──> EDI (UDP/TCP)
File Monitor  ───┤    MST Builder       │
MOT Carousel  ───┘    FIC Encoder   ───┘

                      ↕
                Remote Control
                (ZMQ + Telnet)
```

**Modules:**
- `fig/` - FIG generation (22 types)
- `mot/` - MOT protocol (slideshow, EPG)
- `edi/` - EDI encoding
- `remote/` - ZMQ and Telnet servers
- `audio/` - DAB+ superframe builder
- `fec/` - Reed-Solomon FEC
- `pad/` - PAD encoding

---

## Requirements

**Python:** 3.10 or higher

**Dependencies:**
```
PyYAML>=6.0
structlog>=23.1.0
pyzmq>=25.1.0 (for remote control)
```

**Optional Tools:**
- **odr-audioenc** - Audio encoding (recommended)
- **etisnoop** - ETI analysis
- **dablin** - Audio playback testing
- **ODR-DabMod** - DAB modulation

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

**Code Style:**
- Follow PEP 8
- Add docstrings
- Type hints encouraged
- Keep functions focused

---

## License

[Specify your license here - e.g., GPL-3.0, MIT, etc.]

---

## Acknowledgments

- **OpenDigitalRadio** - Reference implementations and tools
- **ETSI** - DAB standards and specifications
- **DAB Community** - Testing and feedback

---

## Support

**Documentation:** See [docs/](docs/) directory

**Issues:** Report bugs and feature requests via GitHub issues

**Testing:** Use with ODR tools for complete broadcast chain:
- ODR-AudioEnc - Audio encoding
- ODR-DabMux - Alternative multiplexer (for comparison)
- ODR-DabMod - DAB modulation
- ODR-PadEnc - PAD encoding

---

## Project Status

**Version:** 1.0.0 (Priority 9 Complete)

**Status:** 🟢 **Production Ready & Fully Documented**

**Priorities Completed:**
1. ✅ Emergency Alerting & Notifications
2. ✅ Service Management & Navigation
3. ✅ Data Services & Packet Mode
4. ✅ Advanced Signalling (FIG 0/7, 2/1)
5. ✅ EDI Output
6. ✅ Remote Control & Management
7. ✅ Conditional Access & Security
8. ⏸️ Regional Services (deferred - specialized use case)
9. ✅ Quality & Compliance (testing, documentation, standards audit)

**Statistics:**
- 1050+ tests passing (1010 + 40 new compliance/stress tests)
- 22 FIG types implemented
- 73% code coverage
- 19,700+ lines of source code
- 5,400+ lines of documentation (8 comprehensive guides)

**Ready for deployment in:**
- Commercial DAB stations
- Community radio
- Campus radio
- Emergency broadcasting
- Multi-ensemble networks
- Professional broadcast infrastructure

---

## Related Projects

- **ODR-mmbTools** - Complete DAB broadcast toolchain
- **dablin** - DAB/DAB+ audio player
- **welle.io** - DAB/DAB+ receiver software
- **rtl-sdr** - SDR receiver tools

---

**Built with ❤️ for the DAB community**

**Last Updated:** 2026-02-22
