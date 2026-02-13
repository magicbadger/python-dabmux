# Python DAB Multiplexer

A pure Python implementation of a DAB/DAB+ multiplexer, recreating the functionality of ODR-DabMux.

## Project Status

**Phase 0: Foundation** - ✅ Complete (112 tests, 98% coverage)

- ✅ Project structure created with modern Python packaging
- ✅ CRC utilities (CRC-8, CRC-16-CCITT, CRC-32) matching C++ implementation
- ✅ ETI frame structures (SYNC, FC, STC, EOH, EOF, TIST, MNSC)
- ✅ Ensemble configuration (DabEnsemble, DabService, DabComponent, DabSubchannel)
- ✅ Empty ETI frame generation with correct binary layout

**Phase 1: Input/Output Abstractions** - ✅ Complete (164 tests, 93% coverage)

- ✅ InputBase abstract class with buffer management
- ✅ File input implementations (Raw, MPEG, Packet)
- ✅ DabOutput abstract class
- ✅ FileOutput with multiple formats (RAW, STREAMED, FRAMED)
- ✅ DabMultiplexer combines inputs and generates ETI frames

**Phase 2: FIG Generation** - ✅ Complete (195 tests, 100% FIG coverage)

- ✅ FIG 0/0 (Ensemble information)
- ✅ FIG 0/1 (Sub-channel organization)
- ✅ FIG 0/2 (Service organization)
- ✅ FIG 1/0 (Ensemble label)
- ✅ FIG 1/1 (Service labels)
- ✅ FIG carousel with time-based rotation
- ✅ FIC encoder for Mode I (96 bytes)
- ✅ Integration with multiplexer

**Phase 3: Data Input and Encoding** - ✅ Complete (235 tests, 88% coverage)

- ✅ MPEG audio frame parsing (Layer II)
- ✅ Reed-Solomon error correction (GF(2^8))
- ✅ Enhanced packet mode with RS(204, 188)
- ✅ MPEG file input with frame validation
- ✅ Packet file input with FEC
- ✅ MST (Main Service Transport) population
- ✅ Complete ETI generation with audio data and CRCs

**Phase 4: Network Inputs & Timestamps** - ✅ Complete (280 tests, 76% coverage)

- ✅ UDP network input with multicast support
- ✅ TCP server input with client management
- ✅ Frame timestamp handling (EDI epoch, TIST)
- ✅ Timestamp-based synchronization
- ✅ Input statistics (buffer, underrun/overrun, audio levels)
- ✅ State monitoring (no_data, streaming, unstable, silence)

**Phase 5: EDI Protocol & DAB+ Support** - ✅ Complete (348 tests, 71% coverage)

- ✅ EDI TAG items (*ptr, deti, estN)
- ✅ AF packet (Application Framing) with CRC validation
- ✅ PFT (Protection, Fragmentation and Transport) layer
- ✅ PF fragments with Reed-Solomon FEC
- ✅ EDI encoder (ETI → EDI conversion)
- ✅ EDI output over UDP with multicast
- ✅ DAB+ configuration infrastructure
- ✅ DAB+ superframe handling

**Phase 6: Advanced Features & Usability** - ✅ Complete (389 tests, 71% coverage)

- ✅ Character set handling (UTF-8 ↔ EBU Latin)
- ✅ Label validation and short label masks
- ✅ Configuration file parser (YAML)
- ✅ Additional FIG types (FIG 0/5, 0/8, 0/13, 0/17)
- ✅ Command-line interface with argument parsing
- ✅ Example configurations (basic and multi-service)

**🎉 The python-dabmux project is now feature-complete!**

## Installation

```bash
# Development installation
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Testing

```bash
# Run all tests with coverage
pytest tests/unit -v --cov=dabmux

# Verify Phase 0 milestone
python verify_phase0.py

# Verify Phase 1 milestone
python verify_phase1.py

# Verify Phase 2 milestone
python verify_phase2.py

# Verify Phase 3 milestone
python verify_phase3.py

# Verify Phase 4 milestone
python verify_phase4.py

# Verify Phase 5 milestone
python verify_phase5.py

# Verify Phase 6 milestone
python verify_phase6.py
```

## Usage

```bash
# Run the multiplexer with a configuration file
python -m dabmux.cli -c examples/basic_config.yaml -o output.eti

# Output EDI over UDP
python -m dabmux.cli -c examples/multi_service_config.yaml --edi udp://239.1.2.3:12000

# Continuous multiplexing with PFT
python -m dabmux.cli -c config.yaml --edi udp://239.1.2.3:12000 --pft --continuous
```

## Project Structure

```
python-dabmux/
├── dabmux/
│   ├── audio/         # Audio frame parsing (MPEG Layer II, DAB+)
│   ├── core/          # Core data structures (ETI frames, ensemble config)
│   ├── edi/           # EDI protocol (TAG items, PFT, encoder)
│   ├── fec/           # Forward error correction (Reed-Solomon)
│   ├── fig/           # Fast Information Group (FIG) generation
│   ├── input/         # File input abstractions
│   ├── network/       # Network inputs (UDP, TCP)
│   ├── output/        # Output abstractions (file, network, EDI)
│   ├── utils/         # Utilities (CRC, logging, timestamps, statistics)
│   └── mux.py         # Main multiplexer
└── tests/
    └── unit/          # Unit tests
```

## References

- [ODR-DabMux](https://github.com/Opendigitalradio/ODR-DabMux) - C++ reference implementation
- [ETSI EN 300 799](https://www.etsi.org/deliver/etsi_en/300700_300799/300799/01.02.01_60/en_300799v010201p.pdf) - ETI specification
