# Python DAB Multiplexer Implementation Plan

## Context

This plan outlines the complete recreation of ODR-DabMux (a C++ DAB/DAB+ multiplexer) in Python at `/Users/ben/git/python-dabmux`. The C++ version is a production-grade, standards-compliant DAB multiplexer (~31,000 lines) that implements ETSI EN 300 401. The goal is to create a feature-complete Python version that:

1. Maintains full ETSI EN 300 401 compliance
2. Supports all input types (File, UDP, ZMQ, EDI, PRBS)
3. Supports all output types (File, FIFO, UDP, TCP, ZMQ, Raw, Simul)
4. Implements all 23+ FIG (Fast Information Group) types
5. Provides remote control and monitoring capabilities
6. Supports SFN (Single Frequency Networks) with accurate timestamps

This recreation is motivated by Python's advantages: easier deployment, simpler maintenance, better testing infrastructure, and wider accessibility for contributors.

## Project Structure

```
python-dabmux/
├── dabmux/
│   ├── core/              # Multiplexer engine, ETI frames, data structures
│   ├── inputs/            # File, UDP, ZMQ, EDI, PRBS input handlers
│   ├── outputs/           # ETI, EDI, ZMQ, TCP/UDP output handlers
│   ├── fig/               # 23+ FIG implementations and carousel scheduler
│   ├── edi/               # EDI protocol (AF packets, PFT, tags)
│   ├── config/            # Configuration parsing and validation
│   ├── remote/            # Remote control (Telnet, ZMQ)
│   ├── management/        # Statistics server
│   ├── utils/             # CRC, sockets, logging, PRBS
│   └── fec/               # Reed-Solomon for PFT
├── tests/
│   ├── unit/              # Component tests (80-100 tests)
│   ├── integration/       # End-to-end scenarios (15-20 tests)
│   ├── compliance/        # ETSI standard validation (20-25 tests)
│   ├── performance/       # Benchmarks
│   └── fixtures/          # Test data, configs, reference frames
├── examples/              # Example configurations and scripts
├── docs/                  # MkDocs documentation
└── setup.py, pyproject.toml, requirements.txt
```

## Technology Stack

**Core:**
- Python 3.11+ (modern type hints, better performance)
- pyzmq (ZeroMQ for inputs/outputs/remote control)
- pydantic (configuration validation)
- structlog (structured logging)
- asyncio (I/O operations)

**FEC/Encoding:**
- reedsolo (Reed-Solomon for PFT)
- numpy (efficient array operations for interleaving)

**Testing:**
- pytest, pytest-asyncio, pytest-cov (90%+ coverage target)

**Documentation:**
- MkDocs with Material theme
- mkdocstrings for API documentation

## Implementation Phases

### Phase 0: Foundation (Weeks 1-2)
**Goal: Core infrastructure**

**Tasks:**
1. Project scaffolding (setup.py, pyproject.toml, directory structure)
2. ETI data structures (`dabmux/core/eti.py`) - PACKED structs as dataclasses
3. MuxElements (`dabmux/core/mux_elements.py`) - Ensemble, Service, Subchannel, Component
4. CRC-16-CCITT (`dabmux/utils/crc.py`)
5. Logging infrastructure
6. Basic unit tests

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/src/Eti.h` - ETI frame structures
- `/Users/ben/git/ODR-DabMux/src/MuxElements.h` - Core data structures
- `/Users/ben/git/ODR-DabMux/lib/crc.c` - CRC implementation

**Milestone:** Can create and serialize empty ETI frames

### Phase 1: File I/O (Week 3)
**Goal: Minimal end-to-end pipeline**

**Tasks:**
1. InputBase abstract class (`dabmux/inputs/base.py`)
2. File input for audio files
3. DabOutput abstract class (`dabmux/outputs/base.py`)
4. File output (raw/framed/streamed ETI)
5. Basic DabMultiplexer skeleton
6. Minimal config parser (.mux format)

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/src/input/inputs.h` - Input interface
- `/Users/ben/git/ODR-DabMux/src/input/File.cpp` - File input
- `/Users/ben/git/ODR-DabMux/src/dabOutput/dabOutputFile.cpp` - File output
- `/Users/ben/git/ODR-DabMux/src/DabMultiplexer.cpp` - Multiplexer core

**Milestone:** Read audio file → generate ETI frames → write to file

### Phase 2: FIG Generation (Weeks 4-5)
**Goal: Standards-compliant FIB generation**

**Tasks:**
1. IFIG interface and FIG_rate enum (`dabmux/fig/base.py`)
2. Critical FIGs: FIG0/0, FIG0/1, FIG0/2, FIG1/0, FIG1/1
3. FIGCarousel scheduler with deadline management
4. Integrate into DabMultiplexer

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/src/fig/FIG.h` - IFIG interface
- `/Users/ben/git/ODR-DabMux/src/fig/FIG0_0.cpp` - Ensemble info (most critical)
- `/Users/ben/git/ODR-DabMux/src/fig/FIG0_1.cpp` - Subchannel organization
- `/Users/ben/git/ODR-DabMux/src/fig/FIGCarousel.cpp` - Scheduling algorithm

**Milestone:** Generate standards-compliant FIBs with correct repetition rates

### Phase 3: Complete FIG Set (Weeks 6-7)
**Goal: All 23+ FIG types**

**Tasks:**
1. Remaining FIG0 types (3, 5, 6, 7, 8, 9, 10, 13, 14, 17, 18, 19, 21, 24)
2. Remaining FIG1 types (4, 5)
3. FIG2 types (0, 1, 4, 5)
4. TransitionHandler for graceful reconfigurations

**Reference Files:**
- Each FIG implementation in `/Users/ben/git/ODR-DabMux/src/fig/FIG0_*.cpp`
- `/Users/ben/git/ODR-DabMux/src/fig/TransitionHandler.h`

**Milestone:** Full FIG compliance with ETSI EN 300 401

### Phase 4: Network Inputs (Weeks 8-9)
**Goal: Live input support**

**Tasks:**
1. UDP input with buffer management
2. ZMQ input (ZmqAAC, ZmqMPEG) with CURVE authentication
3. EDI decoder (AF packet, PFT, tag parsing)
4. EDI input (TCP/UDP)
5. PRBS generator input
6. Buffer management (prebuffering vs timestamped modes)

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/src/input/Udp.cpp`
- `/Users/ben/git/ODR-DabMux/src/input/Zmq.cpp` - ZMQ with CURVE
- `/Users/ben/git/ODR-DabMux/src/input/Edi.cpp`
- `/Users/ben/git/ODR-DabMux/lib/edi/STIDecoder.cpp` - EDI decoder
- `/Users/ben/git/ODR-DabMux/src/PrbsGenerator.cpp`

**Milestone:** Accept live streams from encoders

### Phase 5: Network Outputs (Week 10)
**Goal: Stream to modulators**

**Tasks:**
1. UDP output
2. TCP output with multi-client support (TCPDataDispatcher)
3. ZMQ output (4-frame batching with metadata)
4. FIFO output
5. Simul output (timing simulation)

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/src/dabOutput/dabOutputUdp.cpp`
- `/Users/ben/git/ODR-DabMux/src/dabOutput/dabOutputTcp.cpp`
- `/Users/ben/git/ODR-DabMux/src/dabOutput/dabOutputZMQ.cpp`
- `/Users/ben/git/ODR-DabMux/src/dabOutput/metadata.h`

**Milestone:** Stream ETI to ODR-DabMod

### Phase 6: EDI Output (Weeks 11-12)
**Goal: EDI over UDP/TCP with PFT**

**Tasks:**
1. TagItems implementation (all ETSI TS 102 693 tags)
2. TagPacket assembly
3. AFPacket framing
4. Reed-Solomon FEC (using reedsolo library)
5. PFT implementation (fragmentation, interleaving)
6. UDP/TCP transport

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/lib/edioutput/TagItems.cpp` - All TAG items
- `/Users/ben/git/ODR-DabMux/lib/edioutput/AFPacket.cpp`
- `/Users/ben/git/ODR-DabMux/lib/edioutput/PFT.cpp` - Forward error correction
- `/Users/ben/git/ODR-DabMux/lib/edioutput/Transport.cpp`

**Milestone:** EDI output compatible with ODR-DabMod

### Phase 7: Timestamp Management (Week 13)
**Goal: SFN support**

**Tasks:**
1. ClockTAI implementation with leap-second management
2. TIST calculation (24ms granularity)
3. MNSC time encoding
4. Timestamp handling in inputs (ZMQ, EDI metadata)
5. Timestamp propagation to outputs

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/lib/ClockTAI.cpp` - TAI clock, bulletin download
- `/Users/ben/git/ODR-DabMux/src/DabMultiplexer.h` - MuxTime class
- `/Users/ben/git/ODR-DabMux/doc/TIMESTAMPS.rst` - Timestamp documentation

**Milestone:** SFN-ready with accurate timestamps

### Phase 8: Remote Control (Week 14)
**Goal: Runtime parameter control**

**Tasks:**
1. RemoteControllable base class
2. Command parsing (list, show, get, set)
3. Telnet server (asyncio-based)
4. ZMQ REQ/REP server
5. Parameter get/set for all controllable objects

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/lib/RemoteControl.h` - Base class
- `/Users/ben/git/ODR-DabMux/lib/RemoteControl.cpp` - Implementation
- `/Users/ben/git/ODR-DabMux/doc/remote_control.txt` - Protocol spec

**Milestone:** Dynamic parameter control via Telnet and ZMQ

### Phase 9: Management Server (Week 15)
**Goal: Statistics and monitoring**

**Tasks:**
1. Statistics collection framework
2. ManagementServer TCP interface
3. Input/output statistics (buffer levels, underruns, overruns)
4. Audio level monitoring
5. Munin-compatible output format

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/src/ManagementServer.cpp`
- `/Users/ben/git/ODR-DabMux/doc/STATS.md` - Statistics documentation

**Milestone:** Full monitoring integration

### Phase 10: Configuration (Week 16)
**Goal: Complete config support**

**Tasks:**
1. Complete .mux parser (all sections)
2. JSON configuration parser
3. Pydantic schemas for validation
4. Linkage set parsing
5. Announcement support
6. Configuration hot-reload capability

**Reference Files:**
- `/Users/ben/git/ODR-DabMux/src/ConfigParser.cpp` - Full parser (~1500 lines)
- `/Users/ben/git/ODR-DabMux/doc/example.mux` - Example config
- `/Users/ben/git/ODR-DabMux/doc/advanced.mux` - Advanced features

**Milestone:** Feature parity with C++ config

### Phase 11: Testing & Compliance (Weeks 17-18)
**Goal: Production quality**

**Testing Tasks:**
1. Unit tests (90%+ coverage, ~80-100 tests)
2. Integration tests (15-20 end-to-end scenarios)
3. Compliance tests (20-25 ETSI validation tests)
4. Performance benchmarks
5. Binary comparison with C++ output

**Test Structure:**
- `tests/unit/` - Component isolation
- `tests/integration/` - Full pipeline
- `tests/compliance/` - ETSI EN 300 401 validation
- `tests/fixtures/` - Reference data from C++ version

**Milestone:** >90% test coverage, ETSI compliant

### Phase 12: Documentation (Weeks 19-20)
**Goal: Complete documentation**

**Documentation Tasks:**
1. MkDocs setup with Material theme
2. Getting Started guides (installation, quickstart)
3. User guides (configuration, inputs, outputs, SFN)
4. API documentation (auto-generated from docstrings)
5. Developer guides (architecture, FIG system)
6. Migration guide from C++ version
7. Example configurations and scripts

**Documentation Structure:**
- `docs/getting-started/` - New user onboarding
- `docs/user-guide/` - Feature documentation
- `docs/api/` - API reference
- `docs/developer/` - Contributor guides
- `docs/reference/` - Standards and parameters
- `examples/` - Working configurations

**Milestone:** Comprehensive, searchable documentation

## Critical Implementation Details

### ETI Frame Structure
**Reference:** `/Users/ben/git/ODR-DabMux/src/Eti.h`

ETI frames must be byte-for-byte identical to C++ version:
- SYNC: 0x49C5F8 (3 bytes)
- FC (Frame Characterization): 4 bytes
- STC (Stream Characterization): Variable per subchannel
- EOH (End of Header): 4 bytes including CRC
- MSC (Main Service Channel): Subchannel data
- EOF (End of Frame): 4 bytes including CRC
- TIST (Timestamp): 3 bytes (optional)

### FIG Carousel Algorithm
**Reference:** `/Users/ben/git/ODR-DabMux/src/fig/FIGCarousel.cpp`

Critical scheduling requirements:
- FIG0/0 must appear in fixed position every 96ms
- Rate A FIGs: ≥10 times per second
- Rate B FIGs: Once per second
- Rate E FIGs: All within 2 minutes
- Deadline-based scheduling with dynamic adjustments

### Buffer Management Modes
**Reference:** `/Users/ben/git/ODR-DabMux/src/input/inputs.h`

Two distinct modes:
1. **Prebuffering**: Simple FIFO, no timestamp awareness
2. **Timestamped**: Wait for specified timestamp, required for SFN

### EDI Protocol
**Reference:** `/Users/ben/git/ODR-DabMux/lib/edioutput/`

ETSI TS 102 693 implementation:
- AF packets with TAG protocol
- PFT with Reed-Solomon RS(255,239)
- TCP and UDP transport
- Support for multiple destinations

## Testing Strategy

### Unit Tests (80-100 tests)
**Priority areas:**
- ETI frame structure serialization
- Each FIG type binary encoding
- CRC calculations
- Configuration parsing and validation
- Buffer management modes
- Character set conversion (UTF-8 to EBU Latin)

### Integration Tests (15-20 tests)
**Key scenarios:**
- File input → File output (ETI comparison)
- ZMQ input → ZMQ output (with real encoder if available)
- EDI input → EDI output
- Multi-service ensemble generation
- Runtime reconfiguration
- Error recovery (input failures, buffer overruns)

### Compliance Tests (20-25 tests)
**ETSI EN 300 401 validation:**
- Frame structure (size, CRC, padding)
- FIG repetition rates
- FIB allocation rules
- Subchannel capacity limits
- Protection level/bitrate tables
- Label encoding and length limits

### Test Data Sources
- Generate reference ETI frames from C++ version with known configs
- Compare Python output byte-for-byte with C++ output
- Use example configs from `/Users/ben/git/ODR-DabMux/doc/`

## Documentation Strategy

### MkDocs Structure
**Tool:** MkDocs with Material theme + mkdocstrings

**Tier 1 Documentation (Weeks 1-4):**
- README.md with quick start
- Installation guide
- Basic configuration guide
- Example configurations (basic.toml)
- API documentation (auto-generated from docstrings)

**Tier 2 Documentation (Weeks 5-8):**
- Complete user guides (inputs, outputs, SFN)
- Remote control API documentation
- Migration guide from C++ version
- Architecture overview
- Advanced examples

**Tier 3 Documentation (Weeks 9+):**
- DAB standard reference
- Developer deep dives (FIG system, EDI protocol)
- Troubleshooting guide
- Tutorial series
- Video content (optional)

### Docstring Standard
Google-style docstrings with full type hints:
```python
def create_service(
    service_id: int,
    label: str,
    short_label: str = ""
) -> Service:
    """Create a DAB service.

    Args:
        service_id: Unique service identifier (SId)
        label: Service label, max 16 characters
        short_label: Short label, max 8 characters

    Returns:
        Service: The created service object

    Raises:
        ValueError: If service_id is out of range
    """
```

## Verification & Validation

### Functional Verification
1. **Binary Comparison**: Generate ETI with Python, compare byte-for-byte with C++ output for identical configs
2. **Interoperability**: Test with ODR-AudioEnc (input) and ODR-DabMod (output)
3. **Receiver Testing**: Validate output with DAB receivers (hardware or software)

### Standards Compliance
1. **ETSI EN 300 401**: ETI frame structure, FIG encoding, timing requirements
2. **ETSI TS 102 693**: EDI protocol, AF/PFT packets
3. **Character Sets**: EBU Latin encoding, UTF-8 conversion

### Performance Benchmarks
- Frame generation must meet 24ms deadline consistently
- Memory usage comparable to C++ version
- CPU usage acceptable for production deployment

### Test Commands
```bash
# Unit tests with coverage
pytest tests/unit -v --cov=dabmux --cov-report=html

# Integration tests
pytest tests/integration -v

# Compliance tests
pytest tests/compliance -v --strict-markers

# Full test suite
pytest tests/ -v

# Performance benchmarks
pytest tests/performance --benchmark-only
```

### Binary Validation
```bash
# Generate reference with C++ version
odr-dabmux examples/basic.mux -o reference.eti --nbframes=100

# Generate with Python version
python-dabmux examples/basic.toml -o python.eti --nbframes=100

# Binary comparison
cmp reference.eti python.eti && echo "IDENTICAL" || echo "DIFFER"

# Detailed diff if different
hexdump -C reference.eti > ref.hex
hexdump -C python.eti > py.hex
diff ref.hex py.hex
```

## Success Criteria

### Phase 0-1 Complete:
- [ ] ETI frames generate correctly (empty)
- [ ] File input reads audio data
- [ ] File output writes valid ETI

### Phase 2-3 Complete:
- [ ] All 23+ FIG types implemented
- [ ] FIG carousel scheduling works correctly
- [ ] FIBs validate against ETSI requirements

### Phase 4-6 Complete:
- [ ] All input types functional
- [ ] All output types functional
- [ ] EDI input/output interoperable with ODR tools

### Phase 7-10 Complete:
- [ ] Timestamps accurate for SFN
- [ ] Remote control operational
- [ ] Statistics server functional
- [ ] Configuration parser handles all C++ configs

### Final Success Criteria:
- [ ] >90% test coverage
- [ ] All compliance tests pass
- [ ] Binary output matches C++ version
- [ ] Interoperable with ODR-AudioEnc and ODR-DabMod
- [ ] Documentation complete (Tier 1 & 2)
- [ ] Performance acceptable (meets 24ms frame deadline)
- [ ] Production-ready package (pip installable)

## Risk Mitigation

### Technical Risks
1. **Performance**: Python slower than C++
   - *Mitigation:* Profile early, use Cython for hot paths if needed, optimize with NumPy

2. **Binary Compatibility**: Subtle encoding differences
   - *Mitigation:* Extensive binary comparison testing, byte-for-byte validation

3. **Async Complexity**: Threading/asyncio model
   - *Mitigation:* Simple thread model for inputs, asyncio for I/O, keep main loop synchronous

### Project Risks
1. **Scope Creep**: ~31,000 lines to replicate
   - *Mitigation:* Strict phase-based approach, focus on MVP first

2. **Standards Compliance**: Complex ETSI specifications
   - *Mitigation:* Extensive reference to C++ implementation, compliance test suite

## Estimated Timeline

- **Phases 0-1 (Foundation & File I/O):** 3 weeks
- **Phases 2-3 (FIG Implementation):** 4 weeks
- **Phases 4-6 (Network I/O & EDI):** 5 weeks
- **Phases 7-10 (Advanced Features):** 4 weeks
- **Phases 11-12 (Testing & Docs):** 4 weeks

**Total: ~20 weeks for feature-complete, production-ready release**

Can be parallelized with multiple developers working on independent modules (inputs, outputs, FIGs).
