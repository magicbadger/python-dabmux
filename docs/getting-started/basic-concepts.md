# Basic Concepts

This guide explains fundamental DAB concepts and terminology used throughout python-dabmux.

## DAB Overview

**DAB (Digital Audio Broadcasting)** is a digital radio standard for broadcasting multiple audio channels over terrestrial radio. Think of it like this:

- **Analog FM**: One station per frequency
- **DAB**: Multiple stations (ensemble) on one frequency

## Core Concepts

### Ensemble

An **ensemble** is a collection of radio stations (services) transmitted together on a single frequency. It's like a "bundle" of stations.

**Key properties:**

- **Ensemble ID** (`0xCE15`): Unique 16-bit identifier
- **Label**: Name visible to listeners (e.g., "BBC Ensemble")
- **ECC**: Extended Country Code (e.g., `0xE1` for Germany)
- **Transmission Mode**: RF characteristics (Mode I, II, III, or IV)

**Example:**
```
┌─────────────────────────────────┐
│      Ensemble: "BBC DAB"        │
│      ID: 0xCE15                 │
├─────────────────────────────────┤
│  📻 BBC Radio 1                 │
│  📻 BBC Radio 2                 │
│  📻 BBC Radio 3                 │
│  📻 BBC Radio 4                 │
└─────────────────────────────────┘
```

### Service

A **service** is a radio station or program stream. Each service has:

- **Service ID** (`0x5001`): Unique identifier within the ensemble
- **Label**: Station name (e.g., "BBC Radio 1")
- **Short Label**: Abbreviated name (e.g., "BBC R1")
- **PTY**: Programme Type (News, Rock, Classical, etc.)
- **Language**: Language code

**Example:**
```yaml
services:
  - uid: 'bbc_radio1'
    id: '0x5001'
    label:
      text: 'BBC Radio 1'
      short: 'BBC R1'
    pty: 10                   # Pop Music
    language: 9               # English
```

### Component

A **component** links a service to a subchannel. Services can have multiple components (e.g., primary audio + data).

- **Service ID**: Which service this belongs to
- **Subchannel ID**: Which subchannel carries the data
- **Type**: Audio (0), Data (various)

**Example:**
```yaml
components:
  - uid: 'comp1'
    service_id: '0x5001'      # BBC Radio 1
    subchannel_id: 0          # Uses subchannel 0
    type: 0                   # Audio component
```

### Subchannel

A **subchannel** is the actual data stream carrying audio or data. It defines:

- **Bitrate**: Data rate (e.g., 128 kbps)
- **Protection Level**: Error correction strength (0-4)
- **Start Address**: Position in the transmission frame
- **Input Source**: Where the data comes from

**Example:**
```yaml
subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'             # MPEG Layer II
    bitrate: 128              # 128 kbps
    start_address: 0          # Start position
    protection:
      level: 2                # Moderate protection
      shortform: true
    input: 'file://audio.mp2'
```

## Configuration Hierarchy

The relationship between these elements:

```
Ensemble
  │
  ├─► Service 1 ──► Component 1 ──► Subchannel 1 ──► Input 1
  │                                      ↓
  │                                  Protection
  │                                   Bitrate
  │
  ├─► Service 2 ──► Component 2 ──► Subchannel 2 ──► Input 2
  │
  └─► Service 3 ──► Component 3 ──► Subchannel 3 ──► Input 3
```

**Key insights:**

1. **Services** are what listeners see (station names)
2. **Components** link services to data streams
3. **Subchannels** carry the actual data
4. **Inputs** provide the data to subchannels

## ETI and EDI

### ETI (Ensemble Transport Interface)

**ETI** is the frame format that python-dabmux generates. Each ETI frame contains:

- **Header**: Frame characteristics, subchannel info
- **FIC**: Fast Information Channel (metadata, FIGs)
- **MST**: Main Service Transport (audio data)
- **Footer**: CRC and timestamp

**ETI frame structure:**
```
┌──────────┬─────┬─────────┬───────┬────────┬──────┬──────┐
│ SYNC (4) │ FC  │ STC (4) │ EOH   │ FIC    │ MST  │ EOF  │
│          │ (4) │ ×N subs │ (4)   │ (96)   │ (var)│ (4)  │
└──────────┴─────┴─────────┴───────┴────────┴──────┴──────┘
                                    │                │
                              Metadata           Audio Data
```

**ETI file formats:**

- **Raw ETI**: Just the frames, no timing
- **Streamed ETI**: Frames with timestamps
- **Framed ETI**: Aligned frames with delimiters

### EDI (Ensemble Data Interface)

**EDI** is a network protocol for transmitting ETI over IP networks. It adds:

- **TAG Items**: Structured data packets (*ptr, deti, estN)
- **AF Packets**: Application Framing with CRC
- **PFT**: Optional fragmentation and FEC

**EDI protocol stack:**
```
┌─────────────────┐
│   ETI Frame     │  Application data
├─────────────────┤
│   TAG Items     │  Structured encoding
├─────────────────┤
│   AF Packet     │  Framing + CRC
├─────────────────┤
│   PFT (opt)     │  Fragmentation + FEC
├─────────────────┤
│   UDP/TCP/IP    │  Network transport
└─────────────────┘
```

## FIG (Fast Information Group)

**FIGs** are metadata packets that describe the ensemble. They tell receivers:

- What services are available
- How subchannels are organized
- Service labels and information

**Common FIG types:**

- **FIG 0/0**: Ensemble information (ID, country)
- **FIG 0/1**: Subchannel organization (bitrates, addresses)
- **FIG 0/2**: Service organization (links services to components)
- **FIG 1/0**: Ensemble label
- **FIG 1/1**: Service labels

**FIG Carousel:**

FIGs are transmitted repeatedly in a rotating schedule:

```
Frame 1:  FIG 0/0, FIG 0/1, FIG 0/2
Frame 2:  FIG 1/0, FIG 1/1
Frame 3:  FIG 0/0, FIG 0/1, FIG 0/2
Frame 4:  FIG 1/0, FIG 1/1
...
```

Frequent FIGs (like 0/0) repeat every 96ms. Others every second or more.

## Audio Formats

### DAB (MPEG Layer II)

Traditional DAB uses **MPEG-1 Audio Layer II**:

- Bitrates: 32-384 kbps (typical: 128-192 kbps)
- Good quality at medium bitrates
- Well-established standard

### DAB+ (HE-AAC v2)

Modern DAB+ uses **HE-AAC v2** (High-Efficiency AAC):

- Bitrates: 32-192 kbps (typical: 48-72 kbps)
- Better quality at lower bitrates
- More efficient than MPEG Layer II
- Uses "superframes" for packaging

## Protection Levels

DAB uses **UEP (Unequal Error Protection)** to protect audio from transmission errors:

| Level | Protection | Use Case |
|-------|------------|----------|
| 0 | Weakest | Strong signal, high bitrate |
| 1 | Weak | Good signal |
| 2 | Moderate | Normal conditions (recommended) |
| 3 | Strong | Weak signal, lower bitrate |
| 4 | Strongest | Very weak signal |

**Trade-off**: Higher protection = more redundancy = lower useful bitrate

**Example:**
```yaml
protection:
  level: 2                    # Moderate protection
  shortform: true             # Use short form table
```

## Capacity Units (CU)

The **Main Service Transport (MST)** is divided into Capacity Units. Each subchannel occupies a contiguous range of CUs.

**Calculation:**
- Higher bitrates = more CUs
- Higher protection = more CUs

**Example allocation:**
```
Mode I MST: 864 Capacity Units

Subchannel 1: Start 0,   Length 84 CUs  (128 kbps, level 2)
Subchannel 2: Start 84,  Length 84 CUs  (128 kbps, level 2)
Subchannel 3: Start 168, Length 42 CUs  (64 kbps, level 2)
```

**Important**: python-dabmux automatically calculates CU allocation. You don't need to manually specify lengths.

## Transmission Modes

DAB defines four transmission modes:

| Mode | Bandwidth | Frame Duration | OFDM Carriers | Use Case |
|------|-----------|----------------|---------------|----------|
| I    | 1.536 MHz | 96 ms          | 1536          | Most common |
| II   | 384 kHz   | 24 ms          | 384           | Local/indoor |
| III  | 192 kHz   | 24 ms          | 192           | Cable/satellite |
| IV   | 768 kHz   | 48 ms          | 768           | Regional |

**Mode I** is by far the most common for terrestrial DAB broadcasting.

## Timestamps

### TIST (Time-Stamp)

The **TIST** field in ETI frames provides frame timestamps:

- Milliseconds since "EDI epoch" (January 1, 2000, 00:00:00 UTC)
- Used for synchronization between multiple transmitters
- Optional but recommended for network transmission

### Frame Timing

- Mode I: 96 ms per frame (10.41... frames/second)
- Mode II: 24 ms per frame
- Mode III: 24 ms per frame
- Mode IV: 48 ms per frame

## Input Sources

python-dabmux supports multiple input types:

### File Inputs

- **file://**: Local file path
- Supported formats: MPEG Layer II, DAB+ superframes, raw audio

**Example:**
```yaml
input: 'file://audio.mp2'
input: 'file:///absolute/path/audio.mp2'
```

### Network Inputs

- **udp://**: UDP unicast or multicast
- **tcp://**: TCP client connection

**Example:**
```yaml
input: 'udp://239.1.2.3:5001'
input: 'tcp://192.168.1.100:5001'
```

## Output Formats

### ETI Files

- **Raw ETI**: Binary ETI frames
- **Streamed ETI**: ETI with timing info
- **Framed ETI**: Aligned frames

**Example:**
```bash
python -m dabmux.cli -c config.yaml -o output.eti
```

### EDI Network

- **UDP**: Connectionless, multicast support
- **TCP**: Reliable, connection-oriented
- **PFT**: Optional fragmentation and FEC

**Example:**
```bash
python -m dabmux.cli -c config.yaml --edi udp://239.1.2.3:12000
python -m dabmux.cli -c config.yaml --edi tcp://192.168.1.100:12000 --pft
```

## Common Terminology

| Term | Meaning |
|------|---------|
| **CIF** | Common Interleaved Frame - the audio/data portion of an ETI frame |
| **CRC** | Cyclic Redundancy Check - error detection code |
| **ECC** | Extended Country Code - identifies the country |
| **FEC** | Forward Error Correction - redundancy for error recovery |
| **FIC** | Fast Information Channel - carries FIGs |
| **FIG** | Fast Information Group - metadata packet |
| **MSC** | Main Service Channel - carries audio/data streams |
| **MST** | Main Service Transport - multiplexed audio data |
| **PTY** | Programme Type - station genre/category |
| **PFT** | Protection, Fragmentation and Transport - EDI layer |
| **RS** | Reed-Solomon - type of FEC |
| **STC** | Stream Characterization - subchannel header info |
| **UEP** | Unequal Error Protection - variable protection scheme |

## Key Takeaways

1. **Ensemble** = Collection of stations on one frequency
2. **Service** = A single radio station
3. **Subchannel** = Data stream carrying audio
4. **Component** = Links services to subchannels
5. **ETI** = Frame format containing everything
6. **EDI** = Network protocol for transmitting ETI
7. **FIG** = Metadata describing the ensemble
8. **Protection** = Error correction strength

## Next Steps

Now that you understand the basics:

- [Configuration Reference](../user-guide/configuration/index.md): Learn all configuration options
- [Architecture](../architecture/index.md): See system design with diagrams
- [Tutorials](../tutorials/index.md): Hands-on guides for specific scenarios
- [Glossary](../glossary.md): Complete DAB terminology reference

## See Also

- [ETI Frame Structure](../architecture/eti-frames.md): Detailed frame layout with diagram
- [FIG Types](../advanced/fig-types.md): Complete FIG specification
- [Transmission Modes](../advanced/transmission-modes.md): Deep dive into RF characteristics
- [Standards References](../standards/etsi-references.md): ETSI specifications
