# Standards and Compliance

DAB standards compliance and ETSI specification references.

## Overview

python-dabmux implements the following ETSI standards for Digital Audio Broadcasting:

- **ETSI EN 300 401** - Radio Broadcasting Systems; Digital Audio Broadcasting (DAB) to mobile, portable and fixed receivers
- **ETSI EN 300 799** - Digital Audio Broadcasting (DAB); Distribution interfaces; Ensemble Transport Interface (ETI)
- **ETSI TS 102 563** - Digital Audio Broadcasting (DAB); Transport of DAB audio signals in MPEG-2 for DAB+ services

## Key Standards

### ETSI EN 300 401 (DAB System)

The core DAB specification defining:
- Transmission modes (I, II, III, IV)
- Frame structure and timing
- FIC (Fast Information Channel) format
- FIG (Fast Information Group) types
- Service and ensemble organization
- Character encoding (EBU Latin)

**python-dabmux compliance:**
- ✅ All four transmission modes supported
- ✅ Complete FIC/FIG generation
- ✅ EBU Latin character set
- ✅ Service and ensemble configuration

**Reference:** [ETSI EN 300 401](https://www.etsi.org/deliver/etsi_en/300400_300499/300401/)

### ETSI EN 300 799 (ETI)

Ensemble Transport Interface specification:
- ETI frame format (NI, G.703, G.704)
- SYNC, FC, STC, EOH structures
- MST data organization
- EOF and TIST fields
- CRC calculations

**python-dabmux compliance:**
- ✅ Complete ETI frame generation
- ✅ All ETI structures implemented
- ✅ CRC-16 for header and data
- ✅ TIST support for SFN networks
- ✅ Raw, streamed, and framed formats

**Reference:** [ETSI EN 300 799](https://www.etsi.org/deliver/etsi_en/300700_300799/300799/)

### ETSI TS 102 563 (DAB+)

DAB+ audio transport specification:
- HE-AAC v2 audio codec
- Audio superframes
- Error protection
- Reed-Solomon FEC

**python-dabmux compliance:**
- ✅ DAB+ subchannel support
- ✅ HE-AAC frame parsing
- ⚠️ Full DAB+ encoder not included (use external encoder)

**Reference:** [ETSI TS 102 563](https://www.etsi.org/deliver/etsi_ts/102500_102599/102563/)

## EDI Protocol

### ETSI TS 102 693 (EDI)

EDI (Ensemble Data Interface) protocol for network transmission:
- TAG items (*ptr, deti, estN)
- AF (Application Fragment) packets
- PFT (Protection, Fragmentation and Transport)
- Reed-Solomon FEC

**python-dabmux compliance:**
- ✅ EDI TAG item generation
- ✅ AF packet format
- ✅ PFT with fragmentation
- ✅ Reed-Solomon FEC (RS(255,207))

**Reference:** [ETSI TS 102 693](https://www.etsi.org/deliver/etsi_ts/102600_102699/102693/)

## Compliance Status

### Implemented Features

| Feature | Standard | Status |
|---------|----------|--------|
| ETI Frame Generation | EN 300 799 | ✅ Complete |
| Transmission Mode I-IV | EN 300 401 | ✅ Complete |
| FIC/FIG Generation | EN 300 401 | ✅ Complete |
| DAB Audio (MPEG Layer II) | EN 300 401 | ✅ Complete |
| DAB+ Audio Support | TS 102 563 | ✅ Complete |
| EDI Protocol | TS 102 693 | ✅ Complete |
| PFT with FEC | TS 102 693 | ✅ Complete |
| TIST Timestamps | EN 300 799 | ✅ Complete |
| EBU Latin Charset | EN 300 401 | ✅ Complete |

### Known Limitations

- **No built-in audio encoder**: External encoder required for MPEG Layer II and HE-AAC
- **FIG types**: Core FIG types implemented, some rarely-used types not included
- **Dynamic labels**: DLS (Dynamic Label Segment) not yet implemented

## Validation

### Test Suite

python-dabmux includes comprehensive tests for standards compliance:

```bash
# Run compliance tests
pytest tests/unit/test_eti.py          # ETI frame structure
pytest tests/unit/fig/                 # FIG generation
pytest tests/unit/test_edi.py          # EDI protocol
pytest tests/unit/test_reed_solomon.py # FEC
```

### Verification Tools

Compare output with reference implementation:

```bash
# Generate ETI with python-dabmux
python -m dabmux.cli -c config.yaml -o python_out.eti -n 100

# Generate ETI with ODR-DabMux (reference)
odr-dabmux -c config.yaml -o odr_out.eti -n 100

# Compare (should be nearly identical)
cmp python_out.eti odr_out.eti
```

## Interoperability

### Tested With

python-dabmux ETI output has been tested with:

- **ODR-DabMod** - DAB modulator ✅
- **Various DAB receivers** - Consumer radios ✅
- **Professional broadcast equipment** - Industry hardware ✅

### Compatibility

- **ETI format**: Compatible with all standard ETI consumers
- **EDI protocol**: Compatible with IP-based modulators and transmission equipment
- **Configuration**: YAML format (not compatible with ODR-DabMux .mux format)

## Standards Documents

### Primary Standards

1. **ETSI EN 300 401 v2.1.1** (2017-01)
   - Digital Audio Broadcasting (DAB); Radio Broadcasting Systems
   - [Download PDF](https://www.etsi.org/deliver/etsi_en/300400_300499/300401/02.01.01_60/en_300401v020101p.pdf)

2. **ETSI EN 300 799 v1.3.1** (2003-12)
   - Digital Audio Broadcasting (DAB); Distribution interfaces; Ensemble Transport Interface (ETI)
   - [Download PDF](https://www.etsi.org/deliver/etsi_en/300700_300799/300799/01.03.01_60/en_300799v010301p.pdf)

3. **ETSI TS 102 563 v1.2.1** (2010-02)
   - Digital Audio Broadcasting (DAB); Transport of DAB+ audio
   - [Download PDF](https://www.etsi.org/deliver/etsi_ts/102500_102599/102563/01.02.01_60/ts_102563v010201p.pdf)

### Supporting Standards

4. **ETSI TS 102 693 v1.1.2** (2014-01)
   - Digital Audio Broadcasting (DAB); Encapsulation of DAB Interfaces (EDI)
   - [Download PDF](https://www.etsi.org/deliver/etsi_ts/102600_102699/102693/01.01.02_60/ts_102693v010102p.pdf)

5. **ISO/IEC 11172-3** (1993)
   - MPEG-1 Audio Layer II
   - Used for traditional DAB audio

6. **ISO/IEC 14496-3** (2005)
   - MPEG-4 Audio (HE-AAC v2)
   - Used for DAB+ audio

## Conformance Testing

### ETI Frame Validation

```python
from dabmux.mux import DabMultiplexer
from dabmux.core.eti import EtiFrame

# Generate frame
mux = DabMultiplexer(ensemble)
frame = mux.generate_frame()

# Validate structure
assert frame.sync.fsync == 0x49C5F8  # SYNC word
assert frame.fc.ficf == 1             # FIC present
assert frame.fc.mid == 1              # Mode I
assert len(frame.pack()) == 6144      # Correct size

# Validate CRCs
header = frame.sync.pack() + frame.fc.pack()
# ... (CRC validation)
```

### FIG Validation

```python
from dabmux.fig.fic import FICEncoder

fic_encoder = FICEncoder(ensemble)
fic_data = fic_encoder.encode_fic(frame_number=0)

# FIC must be exact size for mode
assert len(fic_data) == 96  # Mode I

# Parse FIGs
# ... (FIG parsing and validation)
```

## Reporting Compliance Issues

If you discover standards compliance issues:

1. **Check specification**: Verify against official ETSI documents
2. **Compare with ODR-DabMux**: Test reference implementation
3. **Report issue**: [GitHub Issues](https://github.com/python-dabmux/python-dabmux/issues)
4. **Include details**:
   - Standard section reference
   - Expected vs actual behavior
   - Minimal reproduction case

## See Also

- [Architecture](../architecture/index.md) - Implementation details
- [API Reference](../api-reference/index.md) - Complete API
- [Development](../development/index.md) - Contributing
- [FAQ](../faq.md) - Common questions
