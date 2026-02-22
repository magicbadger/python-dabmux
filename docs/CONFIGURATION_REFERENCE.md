# Configuration Reference

Complete YAML configuration reference for the Python DAB Multiplexer.

---

## Table of Contents

1. [Overview](#overview)
2. [Ensemble Section](#ensemble-section)
3. [Subchannels Section](#subchannels-section)
4. [Services Section](#services-section)
5. [Components Section](#components-section)
6. [Complete Examples](#complete-examples)

---

## Overview

### Configuration File Format

**YAML format:**
```yaml
ensemble:
  # Ensemble configuration

subchannels:
  # List of subchannels

services:
  # List of services

components:
  # List of service components
```

### File Location

**Typical locations:**
- `/etc/dabmux/config.yaml` (system-wide)
- `~/.config/dabmux/config.yaml` (user-specific)
- `./config.yaml` (current directory)

### Loading Configuration

```bash
python -m dabmux.cli -c /path/to/config.yaml -o output.eti
```

---

## Ensemble Section

### Required Fields

```yaml
ensemble:
  # Ensemble identifier (16-bit hex)
  id: '0xCE15'  # Range: 0x0000-0xFFFF

  # Extended Country Code (8-bit hex)
  ecc: '0xE1'  # E1 = Germany, E2 = UK, etc.

  # Ensemble label
  label:
    text: 'My DAB Ensemble'  # Max 16 characters
    short_text: 'MyDAB'      # Max 8 characters (optional)

  # Transmission mode
  transmission_mode: 'I'  # I, II, III, or IV
```

### Optional Fields

#### Date and Time (FIG 0/10, FIG 0/9)

```yaml
ensemble:
  datetime:
    enabled: true  # Enable FIG 0/10
    utc_offset: 0  # Hours from UTC (-12 to +12)
```

**Default:** `enabled: false`

#### Remote Control

```yaml
ensemble:
  remote_control:
    # ZeroMQ JSON API
    zmq_enabled: true
    zmq_bind: 'tcp://*:9000'  # Bind address and port

    # Telnet interface
    telnet_enabled: true
    telnet_port: 9001
    telnet_bind: '127.0.0.1'  # Localhost only by default

    # Authentication
    auth_enabled: true
    auth_password: 'your_password'  # Change this!

    # Audit logging
    audit_log: '/var/log/dabmux/audit.log'
```

**Default:** All disabled

**Security:** See [Remote Control Guide](REMOTE_CONTROL_GUIDE.md)

#### EDI Output

```yaml
ensemble:
  edi_output:
    # Enable EDI
    enabled: true

    # Protocol: 'udp' or 'tcp'
    protocol: 'udp'

    # Destination (IP:port)
    destination: '192.168.1.100:12000'

    # TCP mode (only for protocol: 'tcp')
    tcp_mode: 'client'  # 'client' or 'server'

    # PFT (Fragmentation with FEC)
    enable_pft: true
    pft_fec: 2          # FEC level (0-5)
    pft_fragment_size: 1400  # bytes

    # TIST (Timestamps for SFN)
    enable_tist: true

    # Source identifier (16-bit)
    source_id: 0x1234  # Optional
```

**Default:** `enabled: false`

**Details:** See [EDI Output Guide](EDI_OUTPUT_GUIDE.md)

#### Conditional Access

```yaml
ensemble:
  conditional_access:
    enabled: true
    systems:
      - 0x5601  # Nagravision
      - 0x4A10  # DigitalRadio CA
```

**Default:** `enabled: false`

**Use:** Subscription services only

---

## Subchannels Section

### Audio Subchannel (DAB+)

```yaml
subchannels:
  - uid: 'unique_identifier'  # Required, must be unique
    id: 0                     # Required, 0-63
    type: 'dabplus'           # Required: 'dabplus' or 'packet'
    bitrate: 48               # Required, kbps (8-192)
    protection: 'EEP_3A'      # Required, see below
    input_uri: 'file:///path/to/audio.dabp'  # Required

    # Optional fields
    fec_scheme: 'RS'  # Reed-Solomon FEC (default for DAB+)
```

#### Protection Levels

**Equal Error Protection (EEP):**

| Level | Code Rate | Use Case |
|-------|-----------|----------|
| `EEP_1A` | 1/4 | Worst RF conditions |
| `EEP_2A` | 2/6 | Poor RF conditions |
| `EEP_3A` | 1/2 | **Recommended** (balanced) |
| `EEP_4A` | 3/4 | Good RF conditions |
| `EEP_1B` | 4/9 | Low bitrate, high protection |
| `EEP_2B` | 4/7 | Medium bitrate, medium protection |
| `EEP_3B` | 4/5 | **Recommended for low bitrate** |
| `EEP_4B` | 4/3 | High bitrate, low protection |

**Choosing protection:**
- **Good signal:** EEP_4A (more capacity)
- **Medium signal:** EEP_3A (balanced)
- **Poor signal:** EEP_2A or EEP_1A (more protection)

#### Bitrates

**Recommended bitrates (DAB+/HE-AAC):**

| Quality | Bitrate | Use Case |
|---------|---------|----------|
| Speech | 24 kbps | Talk radio |
| Low | 32 kbps | News, podcasts |
| Medium | 48 kbps | **Most stations** |
| Good | 64 kbps | Music stations |
| High | 80-96 kbps | High-quality music |
| Stereo+ | 128 kbps | Premium music |

#### Input URI Formats

**File input:**
```yaml
input_uri: 'file:///full/path/to/audio.dabp'  # Absolute path required
```

**UDP input:**
```yaml
input_uri: 'udp://@:9001'  # Listen on port 9001
```

**TCP input:**
```yaml
input_uri: 'tcp://192.168.1.100:9001'  # Connect to encoder
```

### Data Subchannel (Packet Mode)

```yaml
subchannels:
  - uid: 'data_subchannel'
    id: 1
    type: 'packet'      # Packet mode
    bitrate: 16         # 8-32 kbps for MOT
    protection: 'EEP_2A'

    # Optional: FEC for packet mode
    fec_scheme: 'ConvolutionalCode'  # Or 'RS'
```

**Use for:**
- MOT slideshow
- EPG (Electronic Programme Guide)
- Directory browsing
- Other data services

---

## Services Section

### Basic Service

```yaml
services:
  - uid: 'my_service'      # Required, unique identifier
    id: '0x5001'           # Required, 16-bit for audio, 32-bit for data
    label:
      text: 'My Radio'     # Required, max 16 characters
      short_text: 'MyRadio'  # Optional, max 8 characters

    # Programme Type (PTy)
    pty: 10                # Required, 0-31 (see table below)

    # Language
    language: 9            # Required, 0-127 (see table below)
```

#### Programme Types (PTy)

| Code | Type | Description |
|------|------|-------------|
| 0 | No programme | Undefined |
| 1 | News | News |
| 2 | Current affairs | Current affairs |
| 3 | Information | Information |
| 4 | Sport | Sport |
| 5 | Education | Education |
| 6 | Drama | Drama |
| 7 | Culture | Culture |
| 8 | Science | Science |
| 9 | Varied | Varied |
| 10 | Pop music | Pop music |
| 11 | Rock music | Rock music |
| 12 | Easy listening | Easy listening |
| 13 | Light classical | Light classical |
| 14 | Serious classical | Serious classical |
| 15 | Other music | Other music |
| 16 | Weather/meteorology | Weather |
| 17 | Finance/business | Finance |
| 18 | Children's programmes | Children's |
| 19 | Social affairs | Social affairs |
| 20 | Religion | Religion |
| 21 | Phone-in | Phone-in |
| 22 | Travel | Travel |
| 23 | Leisure | Leisure |
| 24 | Jazz music | Jazz |
| 25 | Country music | Country |
| 26 | National music | National |
| 27 | Oldies music | Oldies |
| 28 | Folk music | Folk |
| 29 | Documentary | Documentary |
| 30 | Alarm test | Alarm test |
| 31 | Alarm | Alarm |

#### Languages

| Code | Language |
|------|----------|
| 0 | Unknown |
| 1 | Albanian |
| 2 | Breton |
| 3 | Catalan |
| 4 | Croatian |
| 5 | Welsh |
| 6 | Czech |
| 7 | Danish |
| 8 | German |
| 9 | English |
| 10 | Spanish |
| 11 | Esperanto |
| 12 | Estonian |
| 13 | Basque |
| 14 | Faroese |
| 15 | French |
| 16 | Frisian |
| 17 | Irish |
| 18 | Gaelic |
| 19 | Galician |
| 20 | Icelandic |
| 21 | Italian |
| 22 | Lappish |
| 23 | Latin |
| 24 | Latvian |
| 25 | Luxembourgian |
| 26 | Lithuanian |
| 27 | Hungarian |
| 28 | Maltese |
| 29 | Dutch |
| 30 | Norwegian |
| 31 | Occitan |
| 32 | Polish |
| 33 | Portuguese |
| 34 | Romanian |
| 35 | Romansh |
| 36 | Serbian |
| 37 | Slovak |
| 38 | Slovene |
| 39 | Finnish |
| 40 | Swedish |
| 41 | Turkish |
| 42 | Flemish |
| 43 | Walloon |

### Service with Announcements

```yaml
services:
  - uid: 'my_service'
    id: '0x5001'
    label:
      text: 'Emergency Broadcast'

    # Emergency alerts (FIG 0/18, 0/19)
    announcements:
      enabled: true
      cluster_id: 0  # Announcement cluster (0-7)

      # Supported announcement types
      types:
        - 'alarm'           # Emergency alarm
        - 'road_traffic'    # Traffic flash
        - 'warning_service' # Weather warnings
        - 'news_flash'      # Breaking news

      # Optional: Map types to specific subchannels
      announcement_subchannels:
        - type: 'alarm'
          subchannel_uid: 'emergency_audio'
```

**Details:** See [Emergency Alerting Guide](EMERGENCY_ALERTING_GUIDE.md)

### Service with Conditional Access

```yaml
services:
  - uid: 'premium_service'
    id: '0x5001'
    label:
      text: 'Premium Radio'

    # Conditional Access
    ca_system: 0x5601  # CAId (16-bit)
```

**Requires:** Ensemble-level CA configuration

### Service Linking

```yaml
services:
  - uid: 'my_service'
    id: '0x5001'

    # Links to other services
    service_links:
      # DAB service in another ensemble
      - type: 'dab'
        id: 0x5002
        ecc: 0xE1
        ensemble_id: 0xCE16

      # FM/RDS alternative
      - type: 'fm'
        rds_pi: 0x1234
        frequency: 98500  # kHz
```

---

## Components Section

### Audio Component

```yaml
components:
  - uid: 'audio_component'  # Required, unique identifier
    service_id: '0x5001'    # Required, matches service
    subchannel_id: 0        # Required, matches subchannel

    label:
      text: 'Main Programme'  # Optional, max 16 characters
      short_text: 'Main'      # Optional, max 8 characters

    # Component type
    component_type: 0  # 0 = DAB Audio (TMId)

    # Audio Service Component Type (ASCTy)
    ascty: 0  # 0 = DAB, 1 = DAB+
```

### Data Component (MOT Carousel)

```yaml
components:
  - uid: 'slideshow_component'
    service_id: '0x5001'
    subchannel_id: 1
    is_packet_mode: true  # Required for data

    # Packet configuration
    packet:
      address: 0  # Packet address (0-1023)

      # User Application types
      ua_types:
        - type: 2      # 2 = MOT Slideshow
          data: [12]   # Application-specific data

    # MOT Carousel
    carousel_enabled: true
    carousel_directory: '/path/to/images'

    # Optional carousel settings
    carousel_interval: 30  # seconds between images
```

**User Application Types:**
- `2` - MOT Slideshow
- `4` - MOT Directory Browsing (BWS)
- `6` - EPG (Electronic Programme Guide)
- `7` - Journaline (news)

**Details:** See [MOT Carousel Guide](MOT_CAROUSEL_GUIDE.md)

### Component with Dynamic Label

```yaml
components:
  - uid: 'audio_component'
    service_id: '0x5001'
    subchannel_id: 0

    # Dynamic label ("Now Playing")
    dynamic_label:
      text: 'Now Playing: Artist - Song Title'
      charset: 2  # 0 = EBU Latin, 1 = UCS-2, 2 = UTF-8
```

**Update via remote control:**
```bash
telnet localhost 9001
> set_label audio_component "New song title"
```

---

## Complete Examples

### Minimal DAB+ Configuration

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'My DAB'
  transmission_mode: 'I'

subchannels:
  - uid: 'audio'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file:///path/to/audio.dabp'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'My Radio'
    pty: 10
    language: 9

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
```

### Multi-Service Configuration

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Multi-Service DAB'
    short_text: 'Multi'
  transmission_mode: 'I'
  datetime:
    enabled: true

subchannels:
  - uid: 'music'
    id: 0
    type: 'dabplus'
    bitrate: 64
    protection: 'EEP_3A'
    input_uri: 'file:///audio/music.dabp'

  - uid: 'news'
    id: 1
    type: 'dabplus'
    bitrate: 32
    protection: 'EEP_2A'
    input_uri: 'file:///audio/news.dabp'

  - uid: 'talk'
    id: 2
    type: 'dabplus'
    bitrate: 24
    protection: 'EEP_3B'
    input_uri: 'file:///audio/talk.dabp'

services:
  - uid: 'music_service'
    id: '0x5001'
    label:
      text: 'Music Channel'
      short_text: 'Music'
    pty: 10
    language: 9

  - uid: 'news_service'
    id: '0x5002'
    label:
      text: 'News Channel'
      short_text: 'News'
    pty: 1
    language: 9

  - uid: 'talk_service'
    id: '0x5003'
    label:
      text: 'Talk Radio'
      short_text: 'Talk'
    pty: 3
    language: 9

components:
  - uid: 'music_comp'
    service_id: '0x5001'
    subchannel_id: 0

  - uid: 'news_comp'
    service_id: '0x5002'
    subchannel_id: 1

  - uid: 'talk_comp'
    service_id: '0x5003'
    subchannel_id: 2
```

### Full-Featured Configuration

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'Advanced DAB'
    short_text: 'AdvDAB'
  transmission_mode: 'I'

  # Date and time
  datetime:
    enabled: true
    utc_offset: 0

  # Remote control
  remote_control:
    zmq_enabled: true
    zmq_bind: 'tcp://*:9000'
    telnet_enabled: true
    telnet_port: 9001
    auth_enabled: true
    auth_password: '${DABMUX_PASSWORD}'  # From environment

  # EDI output
  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'
    enable_pft: true
    pft_fec: 2
    enable_tist: true

subchannels:
  # Audio
  - uid: 'main_audio'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file:///audio/main.dabp'

  # Emergency audio
  - uid: 'emergency_audio'
    id: 1
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_2A'
    input_uri: 'file:///audio/emergency.dabp'

  # MOT slideshow
  - uid: 'slideshow'
    id: 2
    type: 'packet'
    bitrate: 16
    protection: 'EEP_2A'

services:
  - uid: 'main_service'
    id: '0x5001'
    label:
      text: 'Advanced Radio'
      short_text: 'AdvRadio'
    pty: 10
    language: 9

    # Emergency alerts
    announcements:
      enabled: true
      cluster_id: 0
      types:
        - 'alarm'
        - 'road_traffic'
        - 'warning_service'
      announcement_subchannels:
        - type: 'alarm'
          subchannel_uid: 'emergency_audio'

components:
  # Main audio
  - uid: 'main_audio_comp'
    service_id: '0x5001'
    subchannel_id: 0
    label:
      text: 'Main Programme'
      short_text: 'Main'
    dynamic_label:
      text: 'Welcome to Advanced Radio'
      charset: 2

  # MOT slideshow
  - uid: 'slideshow_comp'
    service_id: '0x5001'
    subchannel_id: 2
    is_packet_mode: true
    packet:
      address: 0
      ua_types:
        - type: 2
          data: [12]
    carousel_enabled: true
    carousel_directory: '/var/dabmux/slideshow'
    carousel_interval: 30
```

---

## Environment Variables

Use environment variables for sensitive data:

```yaml
ensemble:
  remote_control:
    auth_password: '${DABMUX_PASSWORD}'

  edi_output:
    destination: '${MODULATOR_IP}:12000'
```

```bash
export DABMUX_PASSWORD='secure_password'
export MODULATOR_IP='192.168.1.100'

python -m dabmux.cli -c config.yaml -o output.eti
```

---

## Validation

### Check Configuration Syntax

```bash
# Python validation
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Or with yamllint
pip install yamllint
yamllint config.yaml
```

### Dry Run

```bash
# Check configuration without generating ETI
python -m dabmux.cli -c config.yaml --dry-run
```

---

## Best Practices

1. **Use absolute paths** for input_uri
2. **Quote hex values** ('0xCE15', not 0xCE15)
3. **Enable authentication** for remote control
4. **Use environment variables** for passwords
5. **Comment your configuration** for clarity
6. **Validate before deployment** with --dry-run
7. **Test with tools** (etisnoop, dablin)

---

## Resources

**Examples:**
- `examples/basic_dabplus.yaml` - Minimal setup
- `examples/multi_service.yaml` - Multiple services
- `examples/priority1_emergency_alerting.yaml` - Emergency alerts
- `examples/priority4_advanced_signalling.yaml` - All features

**Guides:**
- [Quick Start Guide](QUICK_START.md)
- [MOT Carousel Guide](MOT_CAROUSEL_GUIDE.md)
- [Remote Control Guide](REMOTE_CONTROL_GUIDE.md)
- [EDI Output Guide](EDI_OUTPUT_GUIDE.md)

---

**Last Updated:** 2026-02-22

**Status:** Production Ready
