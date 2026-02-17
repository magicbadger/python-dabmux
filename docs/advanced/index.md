# Advanced Topics

In-depth technical documentation for advanced users and developers.

## Overview

This section covers advanced DAB multiplexing concepts, low-level implementation details, and extension mechanisms for python-dabmux.

## Topics

### [FIG Types](fig-types.md)
Complete reference for all Fast Information Group (FIG) types used in DAB. Covers FIG 0 (MCI), FIG 1 (Labels), FIG 2 (Dynamic labels), FIG 5 (FIDC), and more.

**You should read this if:**
- You want to understand DAB service information
- You're implementing custom FIG generation
- You need to debug FIC data

### [Character Encoding](character-encoding.md)
EBU Latin character set and UTF-8 conversion for DAB labels and text.

**You should read this if:**
- You're using non-ASCII characters in labels
- You need to understand label encoding
- You're implementing international services

### [Timestamps & Synchronization](timestamps-sync.md)
TIST (Timestamp) implementation for Single Frequency Networks (SFN) and synchronized transmission.

**You should read this if:**
- You're building an SFN network
- You need precise frame timing
- You're synchronizing multiple transmitters

### [Reed-Solomon FEC](reed-solomon.md)
Forward Error Correction using Reed-Solomon codes in PFT protocol.

**You should read this if:**
- You're using PFT with FEC
- You want to understand packet recovery
- You're optimizing network transmission

### [Transmission Modes](transmission-modes.md)
Detailed comparison of DAB transmission modes (I, II, III, IV) with frame structures, timing, and capacity calculations.

**You should read this if:**
- You're choosing a transmission mode
- You need to understand mode differences
- You're calculating ensemble capacity

### [Extending python-dabmux](extending.md)
Creating custom inputs, outputs, and FIG generators. Plugin architecture and extension points.

**You should read this if:**
- You're building custom input sources
- You want to add new output formats
- You're implementing custom FIG types

## Prerequisites

These topics assume you're familiar with:
- Basic DAB concepts ([Getting Started](../getting-started/index.md))
- ETI frame structure ([Architecture](../architecture/index.md))
- Configuration and operation ([User Guide](../user-guide/index.md))

## When to Read Advanced Topics

**Read these topics if you:**
- Need deep technical understanding
- Are extending python-dabmux
- Are debugging low-level issues
- Are implementing specialized features

**Skip these topics if you:**
- Just want to run the multiplexer (see [Quick Setup](../getting-started/quick-setup.md))
- Need configuration help (see [User Guide](../user-guide/index.md))
- Are learning DAB basics (see [Basic Concepts](../getting-started/basic-concepts.md))

## Related Resources

- [API Reference](../api-reference/index.md) - Complete API documentation
- [Architecture](../architecture/index.md) - System design and diagrams
- [Standards](../standards/index.md) - ETSI specifications and compliance
- [Development](../development/index.md) - Contributing to python-dabmux

## External References

- [ETSI EN 300 401](https://www.etsi.org/deliver/etsi_en/300400_300499/300401/) - DAB standard
- [ETSI EN 300 799](https://www.etsi.org/deliver/etsi_en/300700_300799/300799/) - ETI specification
- [ETSI TS 102 563](https://www.etsi.org/deliver/etsi_ts/102500_102599/102563/) - DAB+ specification
- [ODR-DabMux Documentation](https://github.com/Opendigitalradio/ODR-DabMux) - Reference implementation
