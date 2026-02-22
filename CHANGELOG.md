# Changelog

All notable changes to python-dabmux will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Priority 5: EDI Output ✅ COMPLETED

#### Phase 1: TIST & Timestamps (Complete)
- `TagTIST` class for EDI timestamp TAG encoding (56-bit timestamps)
- Unix timestamp to EDI epoch conversion (2000-01-01 base)
- 32-bit seconds + 24-bit ticks (1/16384 sec precision ~61μs)
- TIST TAG integration in EDI encoder
- 20 comprehensive unit tests for TIST functionality

#### Phase 2: TCP Transport (Complete)
- `EdiTcpOutput` class for reliable TCP streaming
- TCP client mode (connect to remote server)
- TCP server mode (listen for multiple client connections)
- Multi-client broadcasting with thread-safe connection management
- Automatic dead client detection and removal
- Connection statistics and monitoring
- 15 comprehensive unit tests for TCP transport

#### Phase 3: Multiplexer Integration (Complete)
- `EdiOutputConfig` dataclass for EDI configuration
- EDI output field added to `DabEnsemble`
- Automatic EDI encoder and output initialization
- Integrated EDI packet transmission in `generate_frame()`
- Support for both UDP and TCP protocols
- PFT fragmentation configuration support
- 14 comprehensive unit tests for multiplexer integration

#### Phase 4: CLI & Configuration (Complete)
- CLI arguments for EDI configuration:
  - `--edi URL` - Enable EDI output with UDP/TCP destination
  - `--edi-tcp-mode {client,server}` - TCP connection mode
  - `--edi-source-port PORT` - UDP source port
  - `--pft` - Enable PFT fragmentation
  - `--pft-fec DEPTH` - FEC depth (0-7)
  - `--pft-fragment-size SIZE` - Fragment size in bytes
  - `--tist` - Enable timestamp synchronization
- `configure_edi_output()` method in CLI for ensemble configuration
- Combined file and EDI output support (can output both simultaneously)
- 5 example YAML configuration files:
  - `edi_udp_unicast.yaml` - Simple UDP unicast
  - `edi_udp_multicast.yaml` - Multicast distribution
  - `edi_tcp_client.yaml` - TCP client to modulator
  - `edi_tcp_server.yaml` - TCP server mode
  - `edi_pft_fec.yaml` - PFT with Reed-Solomon FEC
- 16 comprehensive unit tests for CLI EDI configuration

#### Phase 5: Testing & Validation (Complete)
- 10 end-to-end integration tests (`test_edi_e2e.py`):
  - UDP unicast basic flow
  - UDP multicast
  - UDP with PFT fragmentation
  - TCP client mode
  - TCP server mode
  - Combined file + EDI output
  - Continuous frame generation
  - Full service configuration
  - Error handling and validation
- EDI validation tools:
  - `tools/edi_analyzer.py` - Analyze EDI packets from UDP/file (~400 LOC)
    - Parses AF and PFT packets
    - Decodes TAG items (*ptr, deti, tist, estN)
    - Statistics and monitoring
  - `tools/edi_generator.py` - Generate synthetic EDI packets (~300 LOC)
    - UDP/file output
    - PFT fragmentation
    - FEC support for testing
- Fixed EDI encoder bugs:
  - Corrected MST data extraction from concatenated blob
  - Fixed `stc_headers` attribute name (was `stc_list`)
  - Fixed STC start_address access (was `stl_h`)

#### Infrastructure & Bug Fixes
- Fixed MNSC field location in EDI encoder (from `frame.fc.mnsc` to `frame.eoh.mnsc`)
- Added `is_open()` method to `EdiOutput` class for consistency
- Improved TCP socket handling and error recovery
- Fixed subchannel data indexing in EDI encoder for estN TAGs
- CLI now supports both file and EDI output simultaneously (removed mutual exclusivity)

### Test Coverage
- Total: 763 passing tests (up from 647)
- EDI-related: 61 new tests
  - TIST: 20 tests
  - TCP: 15 tests
  - Multiplexer Integration: 14 tests
  - CLI Configuration: 16 tests
  - End-to-End Integration: 10 tests

### Documentation
- Updated TODO.md with Priority 5 complete (all 5 phases)
- Updated EDI documentation to reflect CLI availability
- Created 5 comprehensive example configuration files
- Added validation tool documentation (edi_analyzer, edi_generator)
- Updated CHANGELOG.md with complete Priority 5 implementation

---

## [Previous Releases]

### Priority 3: Data Services & Packet Mode (Complete)
- FIG 0/3: Service component in packet mode
- FIG 0/14: FEC sub-channel organization
- Packet addressing (10-bit, 0-1023)
- Reed-Solomon FEC (RS 204,188)
- 31 comprehensive tests

### Priority 2: Service Management & Navigation (Complete)
- FIG 0/6: Service linking
- FIG 0/21: Frequency information
- FIG 0/24: Other ensemble services
- Multi-ensemble network support
- 41 comprehensive tests

### Priority 1: Emergency Alerting & Notifications (Complete)
- FIG 0/9: Extended Country Code & LTO
- FIG 0/10: Date and Time
- FIG 0/18: Announcement support
- FIG 0/19: Announcement switching
- Emergency Alert System (EAS) ready
- 40 comprehensive tests

### Core Implementation (Complete)
- ETI frame generation (ETSI EN 300 799 compliant)
- FIG 0/0, 0/1, 0/2, 0/5, 0/8, 0/13, 0/17 signaling
- FIG 1/0, 1/1, 1/4 labels
- DAB and DAB+ audio encoding support
- Protection profiles (UEP and EEP)
- Multiple transmission modes (I, II, III, IV)
- File-based ETI output (RAW, FRAMED, STREAMED)
- Comprehensive test suite foundation

---

## Release Philosophy

python-dabmux follows these principles:
- **Stability first**: Existing features remain stable across releases
- **Incremental delivery**: Complete features in phases (as seen with Priority 5)
- **Test-driven**: All features require comprehensive test coverage
- **Standards compliance**: Full ETSI specification adherence
- **Documentation**: Clear docs with examples for all features

---

## Versioning Strategy

- **Major (X.0.0)**: Breaking API changes, major architectural updates
- **Minor (0.X.0)**: New features, backward-compatible enhancements
- **Patch (0.0.X)**: Bug fixes, documentation updates

**Current Status**: Pre-release development (0.x series)
- API may change between minor versions
- Production use possible but test thoroughly
- First stable release (1.0.0) planned after Priority 6 completion
