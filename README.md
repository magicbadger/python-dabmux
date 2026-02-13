# Python DAB Multiplexer

A pure Python implementation of a DAB/DAB+ multiplexer, recreating the functionality of ODR-DabMux.

## Project Status

**Phase 0: Foundation** - ✅ Complete

- ✅ Project structure created with modern Python packaging
- ✅ CRC utilities (CRC-8, CRC-16-CCITT, CRC-32) matching C++ implementation
- ✅ ETI frame structures (SYNC, FC, STC, EOH, EOF, TIST, MNSC)
- ✅ Ensemble configuration (DabEnsemble, DabService, DabComponent, DabSubchannel)
- ✅ Empty ETI frame generation with correct binary layout
- ✅ 112 unit tests passing with 98% code coverage

**Phase 1: Input/Output Abstractions** - Next

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
```

## Project Structure

```
python-dabmux/
├── dabmux/
│   ├── core/          # Core data structures (ETI frames, ensemble config)
│   └── utils/         # Utilities (CRC, logging)
└── tests/
    └── unit/          # Unit tests
```

## References

- [ODR-DabMux](https://github.com/Opendigitalradio/ODR-DabMux) - C++ reference implementation
- [ETSI EN 300 799](https://www.etsi.org/deliver/etsi_en/300700_300799/300799/01.02.01_60/en_300799v010201p.pdf) - ETI specification
