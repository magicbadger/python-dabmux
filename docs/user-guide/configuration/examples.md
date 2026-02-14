# Configuration Examples

Complete working configuration examples for common scenarios.

## Overview

This page provides ready-to-use configuration examples for various use cases. Each example is annotated and explains the key configuration decisions.

**Example categories:**
- [Single Service (Minimal)](#single-service-minimal)
- [Multi-Service Ensemble](#multi-service-ensemble)
- [DAB+ Configuration](#dab-configuration)
- [Network Streaming](#network-streaming)
- [Mixed DAB/DAB+](#mixed-dabdab)
- [High Protection](#high-protection-weak-signal)
- [Maximum Capacity](#maximum-capacity-strong-signal)
- [Indoor/Local Transmitter](#indoorlocal-transmitter)
- [EDI Output](#edi-output-configuration)

---

## Single Service (Minimal)

**Use case:** Simple single-station setup for testing or small deployments.

**File:** `single_service.yaml`

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'Test Ensemble'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'Radio One'

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
    type: 0
```

**Key points:**
- Uses defaults: ECC=0xE1 (Germany), Mode I, auto LTO
- Standard 128 kbps DAB audio
- Protection level 2 (recommended default)
- File input with relative path

**Run:**
```bash
python -m dabmux.cli -c single_service.yaml -o output.eti
```

**Capacity usage:** ~84 CU (out of 864 available in Mode I)

---

## Multi-Service Ensemble

**Use case:** Multiple radio stations in one ensemble with different bitrates and content types.

**File:** `multi_service.yaml`

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'DAB Multiplex'
    short: 'DABMux'
  lto_auto: true

subchannels:
  # High-quality music station (DAB)
  - uid: 'music_hq'
    id: 0
    type: 'audio'
    bitrate: 160
    start_address: 0
    protection:
      level: 3
      shortform: true
    input: 'file://music.mp2'

  # News/talk station (DAB+)
  - uid: 'news'
    id: 1
    type: 'dabplus'
    bitrate: 64
    start_address: 150
    protection:
      level: 2
      shortform: true
    input: 'file://news.aac'

  # Pop music station (DAB+)
  - uid: 'pop'
    id: 2
    type: 'dabplus'
    bitrate: 80
    start_address: 250
    protection:
      level: 2
      shortform: true
    input: 'file://pop.aac'

  # Classical music station (DAB+)
  - uid: 'classical'
    id: 3
    type: 'dabplus'
    bitrate: 96
    start_address: 350
    protection:
      level: 3
      shortform: true
    input: 'file://classical.aac'

services:
  # Music station
  - uid: 'music_service'
    id: '0x5001'
    label:
      text: 'Classic Hits'
      short: 'Hits'
    pty: 10  # Pop Music
    language: 9  # English

  # News station
  - uid: 'news_service'
    id: '0x5002'
    label:
      text: 'News 24/7'
      short: 'News24'
    pty: 1  # News
    language: 9  # English

  # Pop station
  - uid: 'pop_service'
    id: '0x5003'
    label:
      text: 'Top 40 Radio'
      short: 'Top40'
    pty: 10  # Pop Music
    language: 9  # English

  # Classical station
  - uid: 'classical_service'
    id: '0x5004'
    label:
      text: 'Classical FM'
      short: 'Classic'
    pty: 14  # Serious Classical
    language: 9  # English

components:
  - uid: 'music_comp'
    service_id: '0x5001'
    subchannel_id: 0
    type: 0

  - uid: 'news_comp'
    service_id: '0x5002'
    subchannel_id: 1
    type: 0

  - uid: 'pop_comp'
    service_id: '0x5003'
    subchannel_id: 2
    type: 0

  - uid: 'classical_comp'
    service_id: '0x5004'
    subchannel_id: 3
    type: 0
```

**Key points:**
- 4 services with different content types
- Mixed bitrates: 160, 64, 80, 96 kbps
- Protection levels vary by importance
- Explicit start_address spacing
- Short labels for small displays

**Capacity calculation:**
- Music (160 kbps @ level 3): ~120 CU
- News (64 kbps @ level 2): ~50 CU
- Pop (80 kbps @ level 2): ~65 CU
- Classical (96 kbps @ level 3): ~85 CU
- **Total:** ~320 CU (out of 864 available)

**Run:**
```bash
python -m dabmux.cli -c multi_service.yaml -o multiplex.eti
```

---

## DAB+ Configuration

**Use case:** All services using HE-AAC v2 (DAB+) for maximum efficiency.

**File:** `dabplus_only.yaml`

```yaml
ensemble:
  id: '0xCE20'
  ecc: '0xE2'  # UK
  label:
    text: 'DAB+ Network'
    short: 'DAB+Net'

subchannels:
  # Speech/news - low bitrate
  - uid: 'news'
    id: 0
    type: 'dabplus'
    bitrate: 48
    start_address: 0
    protection:
      level: 2
    input: 'file://news.aac'

  # Music station 1
  - uid: 'music1'
    id: 1
    type: 'dabplus'
    bitrate: 72
    start_address: 100
    protection:
      level: 2
    input: 'file://music1.aac'

  # Music station 2
  - uid: 'music2'
    id: 2
    type: 'dabplus'
    bitrate: 72
    start_address: 200
    protection:
      level: 2
    input: 'file://music2.aac'

  # Premium music - high quality
  - uid: 'premium'
    id: 3
    type: 'dabplus'
    bitrate: 96
    start_address: 300
    protection:
      level: 3
    input: 'file://premium.aac'

services:
  - uid: 'news_svc'
    id: '0x6001'
    label:
      text: 'News Radio'
      short: 'News'
    pty: 1
    language: 9

  - uid: 'music1_svc'
    id: '0x6002'
    label:
      text: 'Pop Hits'
      short: 'PopHits'
    pty: 10
    language: 9

  - uid: 'music2_svc'
    id: '0x6003'
    label:
      text: 'Rock Radio'
      short: 'Rock'
    pty: 11
    language: 9

  - uid: 'premium_svc'
    id: '0x6004'
    label:
      text: 'Premium Music'
      short: 'Premium'
    pty: 10
    language: 9

components:
  - uid: 'news_comp'
    service_id: '0x6001'
    subchannel_id: 0
    type: 0

  - uid: 'music1_comp'
    service_id: '0x6002'
    subchannel_id: 1
    type: 0

  - uid: 'music2_comp'
    service_id: '0x6003'
    subchannel_id: 2
    type: 0

  - uid: 'premium_comp'
    service_id: '0x6004'
    subchannel_id: 3
    type: 0
```

**Key points:**
- All DAB+ (HE-AAC v2) for efficiency
- 48 kbps for speech (excellent quality)
- 72 kbps for standard music (good quality)
- 96 kbps for premium music (excellent quality)
- Fits 4 services with low capacity usage

**Capacity:** ~250 CU total (plenty of room for more services)

**Encoding commands:**
```bash
# Speech (48 kbps)
ffmpeg -i input.wav -c:a aac -b:a 48k -profile:a aac_he_v2 news.aac

# Music (72 kbps)
ffmpeg -i input.wav -c:a aac -b:a 72k -profile:a aac_he_v2 music.aac

# Premium (96 kbps)
ffmpeg -i input.wav -c:a aac -b:a 96k -profile:a aac_he_v2 premium.aac
```

---

## Network Streaming

**Use case:** Live streaming from remote encoders via UDP/TCP.

**File:** `network_streaming.yaml`

```yaml
ensemble:
  id: '0xCE30'
  label:
    text: 'Live Network'
    short: 'LiveNet'

subchannels:
  # UDP multicast input
  - uid: 'live_music'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 3  # Higher protection for network
    input: 'udp://239.1.2.3:5001'

  # UDP unicast input
  - uid: 'live_news'
    id: 1
    type: 'dabplus'
    bitrate: 64
    start_address: 100
    protection:
      level: 2
    input: 'udp://192.168.1.100:5002'

  # TCP input (reliable)
  - uid: 'live_talk'
    id: 2
    type: 'dabplus'
    bitrate: 48
    start_address: 200
    protection:
      level: 2
    input: 'tcp://192.168.1.101:5003'

services:
  - uid: 'music_svc'
    id: '0x7001'
    label:
      text: 'Live Music'
    pty: 10
    language: 9

  - uid: 'news_svc'
    id: '0x7002'
    label:
      text: 'Live News'
    pty: 1
    language: 9

  - uid: 'talk_svc'
    id: '0x7003'
    label:
      text: 'Talk Radio'
    pty: 9  # Varied Speech
    language: 9

components:
  - uid: 'music_comp'
    service_id: '0x7001'
    subchannel_id: 0
    type: 0

  - uid: 'news_comp'
    service_id: '0x7002'
    subchannel_id: 1
    type: 0

  - uid: 'talk_comp'
    service_id: '0x7003'
    subchannel_id: 2
    type: 0
```

**Key points:**
- UDP multicast for distribution
- UDP unicast for point-to-point
- TCP for guaranteed delivery
- Higher protection compensates for network issues

**Network setup:**

Sender (encoder):
```bash
# Send to UDP multicast
ffmpeg -re -i input.wav -c:a mp2 -b:a 128k -f mp2 udp://239.1.2.3:5001

# Send to UDP unicast
ffmpeg -re -i input.wav -c:a aac -b:a 64k udp://192.168.1.200:5002

# Send to TCP
ffmpeg -re -i input.wav -c:a aac -b:a 48k -f mp2 tcp://192.168.1.200:5003
```

Receiver (multiplexer):
```bash
python -m dabmux.cli -c network_streaming.yaml -o live.eti
```

**Troubleshooting:**
- Firewall: Allow UDP/TCP ports
- Multicast: Enable IGMP on routers
- Buffer: Use --continuous mode for live streaming

---

## Mixed DAB/DAB+

**Use case:** Legacy DAB receivers alongside newer DAB+ receivers.

**File:** `mixed_dab_dabplus.yaml`

```yaml
ensemble:
  id: '0xCE40'
  label:
    text: 'Mixed Network'

subchannels:
  # Legacy DAB for old receivers
  - uid: 'dab_main'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 2
    input: 'file://main.mp2'

  # DAB+ for new receivers (efficient)
  - uid: 'dabplus_1'
    id: 1
    type: 'dabplus'
    bitrate: 72
    start_address: 100
    protection:
      level: 2
    input: 'file://station1.aac'

  - uid: 'dabplus_2'
    id: 2
    type: 'dabplus'
    bitrate: 72
    start_address: 200
    protection:
      level: 2
    input: 'file://station2.aac'

services:
  - uid: 'main_svc'
    id: '0x8001'
    label:
      text: 'Main Station'
      short: 'Main'
    pty: 10
    language: 9

  - uid: 'station1_svc'
    id: '0x8002'
    label:
      text: 'Station One'
      short: 'Stn1'
    pty: 10
    language: 9

  - uid: 'station2_svc'
    id: '0x8003'
    label:
      text: 'Station Two'
      short: 'Stn2'
    pty: 1
    language: 9

components:
  - uid: 'main_comp'
    service_id: '0x8001'
    subchannel_id: 0
    type: 0

  - uid: 'station1_comp'
    service_id: '0x8002'
    subchannel_id: 1
    type: 0

  - uid: 'station2_comp'
    service_id: '0x8003'
    subchannel_id: 2
    type: 0
```

**Key points:**
- One DAB service for legacy compatibility
- Multiple DAB+ services for efficiency
- Balances compatibility vs. capacity

**Capacity comparison:**
- DAB 128 kbps @ level 2: ~84 CU
- DAB+ 72 kbps @ level 2: ~60 CU each
- **Total:** ~204 CU (leaves room for more)

---

## High Protection (Weak Signal)

**Use case:** Coverage at edge of broadcast area or mobile reception.

**File:** `high_protection.yaml`

```yaml
ensemble:
  id: '0xCE50'
  label:
    text: 'Rural Coverage'
    short: 'Rural'

subchannels:
  # Critical news service - maximum protection
  - uid: 'emergency_news'
    id: 0
    type: 'dabplus'
    bitrate: 48
    start_address: 0
    protection:
      level: 4  # Maximum protection
      shortform: true
    input: 'file://emergency.aac'

  # Main music - strong protection
  - uid: 'music'
    id: 1
    type: 'dabplus'
    bitrate: 64
    start_address: 100
    protection:
      level: 3  # Strong protection
      shortform: true
    input: 'file://music.aac'

services:
  - uid: 'emergency_svc'
    id: '0x9001'
    label:
      text: 'Emergency Info'
      short: 'EmergInf'
    pty: 31  # Alarm
    language: 9

  - uid: 'music_svc'
    id: '0x9002'
    label:
      text: 'Radio Station'
      short: 'Radio'
    pty: 10
    language: 9

components:
  - uid: 'emergency_comp'
    service_id: '0x9001'
    subchannel_id: 0
    type: 0

  - uid: 'music_comp'
    service_id: '0x9002'
    subchannel_id: 1
    type: 0
```

**Key points:**
- Protection level 4 for critical content
- Protection level 3 for important content
- Lower bitrates to compensate for protection overhead
- Suitable for weak signal areas

**Signal strength guidelines:**
- < 40 dBμV: Use level 4
- 40-60 dBμV: Use level 3
- 60-80 dBμV: Use level 2

---

## Maximum Capacity (Strong Signal)

**Use case:** Indoor transmitter or cable distribution with strong signal.

**File:** `max_capacity.yaml`

```yaml
ensemble:
  id: '0xCE60'
  label:
    text: 'Indoor Network'

subchannels:
  # Use level 1 protection for maximum capacity
  - uid: 'svc1'
    id: 0
    type: 'dabplus'
    bitrate: 96
    start_address: 0
    protection:
      level: 1  # Minimal protection
    input: 'file://station1.aac'

  - uid: 'svc2'
    id: 1
    type: 'dabplus'
    bitrate: 96
    start_address: 80
    protection:
      level: 1
    input: 'file://station2.aac'

  - uid: 'svc3'
    id: 2
    type: 'dabplus'
    bitrate: 96
    start_address: 160
    protection:
      level: 1
    input: 'file://station3.aac'

  - uid: 'svc4'
    id: 3
    type: 'dabplus'
    bitrate: 96
    start_address: 240
    protection:
      level: 1
    input: 'file://station4.aac'

  - uid: 'svc5'
    id: 4
    type: 'dabplus'
    bitrate: 96
    start_address: 320
    protection:
      level: 1
    input: 'file://station5.aac'

  - uid: 'svc6'
    id: 5
    type: 'dabplus'
    bitrate: 96
    start_address: 400
    protection:
      level: 1
    input: 'file://station6.aac'

services:
  - uid: 'svc1_service'
    id: '0xA001'
    label:
      text: 'Station 1'
    pty: 10
    language: 9

  - uid: 'svc2_service'
    id: '0xA002'
    label:
      text: 'Station 2'
    pty: 10
    language: 9

  - uid: 'svc3_service'
    id: '0xA003'
    label:
      text: 'Station 3'
    pty: 1
    language: 9

  - uid: 'svc4_service'
    id: '0xA004'
    label:
      text: 'Station 4'
    pty: 10
    language: 9

  - uid: 'svc5_service'
    id: '0xA005'
    label:
      text: 'Station 5'
    pty: 11
    language: 9

  - uid: 'svc6_service'
    id: '0xA006'
    label:
      text: 'Station 6'
    pty: 14
    language: 9

components:
  - uid: 'comp1'
    service_id: '0xA001'
    subchannel_id: 0
    type: 0

  - uid: 'comp2'
    service_id: '0xA002'
    subchannel_id: 1
    type: 0

  - uid: 'comp3'
    service_id: '0xA003'
    subchannel_id: 2
    type: 0

  - uid: 'comp4'
    service_id: '0xA004'
    subchannel_id: 3
    type: 0

  - uid: 'comp5'
    service_id: '0xA005'
    subchannel_id: 4
    type: 0

  - uid: 'comp6'
    service_id: '0xA006'
    subchannel_id: 5
    type: 0
```

**Key points:**
- Protection level 1 (minimal overhead)
- 6 services at 96 kbps each
- Maximum service count for strong signal
- Total capacity: ~480 CU

**Use only when:**
- Indoor transmitter
- Cable distribution
- Very strong signal (> 80 dBμV)
- Controlled environment

---

## Indoor/Local Transmitter

**Use case:** Small coverage area with excellent signal strength.

**File:** `indoor_transmitter.yaml`

```yaml
ensemble:
  id: '0xCE70'
  transmission_mode: 'II'  # Mode II for local/indoor
  label:
    text: 'Indoor DAB'
    short: 'Indoor'

subchannels:
  # Mode II has 216 CU capacity
  - uid: 'local1'
    id: 0
    type: 'dabplus'
    bitrate: 72
    start_address: 0
    protection:
      level: 1  # Light protection OK indoors
    input: 'file://local1.aac'

  - uid: 'local2'
    id: 1
    type: 'dabplus'
    bitrate: 72
    start_address: 60
    protection:
      level: 1
    input: 'file://local2.aac'

  - uid: 'local3'
    id: 2
    type: 'dabplus'
    bitrate: 48
    start_address: 120
    protection:
      level: 1
    input: 'file://local3.aac'

services:
  - uid: 'local1_svc'
    id: '0xB001'
    label:
      text: 'Local Music'
    pty: 10
    language: 9

  - uid: 'local2_svc'
    id: '0xB002'
    label:
      text: 'Local News'
    pty: 1
    language: 9

  - uid: 'local3_svc'
    id: '0xB003'
    label:
      text: 'Local Talk'
    pty: 9
    language: 9

components:
  - uid: 'comp1'
    service_id: '0xB001'
    subchannel_id: 0
    type: 0

  - uid: 'comp2'
    service_id: '0xB002'
    subchannel_id: 1
    type: 0

  - uid: 'comp3'
    service_id: '0xB003'
    subchannel_id: 2
    type: 0
```

**Key points:**
- Mode II transmission (384 kHz bandwidth)
- 216 CU total capacity (vs. 864 in Mode I)
- Light protection suitable for strong indoor signal
- 3 services fit comfortably

**Transmission modes:**
- **Mode I (1536 kHz):** 864 CU - Standard terrestrial
- **Mode II (384 kHz):** 216 CU - Local/indoor
- **Mode III (192 kHz):** 108 CU - Cable
- **Mode IV (768 kHz):** 432 CU - Regional

---

## EDI Output Configuration

**Use case:** Network distribution to transmitter via EDI protocol.

**File:** `edi_output.yaml`

```yaml
ensemble:
  id: '0xCE80'
  label:
    text: 'EDI Network'

subchannels:
  - uid: 'main_audio'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 2
    input: 'file://audio.mp2'

services:
  - uid: 'main_service'
    id: '0xC001'
    label:
      text: 'Main Station'
    pty: 10
    language: 9

components:
  - uid: 'main_comp'
    service_id: '0xC001'
    subchannel_id: 0
    type: 0
```

**Run with EDI output:**

```bash
# Basic EDI over UDP
python -m dabmux.cli \
  -c edi_output.yaml \
  --edi udp://192.168.1.100:12000

# EDI with PFT (fragmentation and FEC)
python -m dabmux.cli \
  -c edi_output.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 2 \
  --pft-fec-m 3 \
  --pft-fragment-size 512

# Save ETI file AND send EDI
python -m dabmux.cli \
  -c edi_output.yaml \
  -o archive.eti \
  --edi udp://192.168.1.100:12000 \
  --pft
```

**PFT parameters:**
- `--pft`: Enable PFT fragmentation
- `--pft-fec 2`: Reed-Solomon FEC depth (0-20)
- `--pft-fec-m 3`: Maximum correctable fragments
- `--pft-fragment-size 512`: Fragment size in bytes

**Network setup:**
- Multiplexer sends to: `udp://192.168.1.100:12000`
- Modulator receives on port: `12000`
- Firewall: Allow UDP traffic
- MTU: Ensure sufficient for fragment size + overhead

---

## Common Patterns

### Sequential Service IDs

```yaml
services:
  - id: '0x5001'  # First service
  - id: '0x5002'  # Second service
  - id: '0x5003'  # Third service
```

### Descriptive UIDs

```yaml
subchannels:
  - uid: 'bbc_radio1_audio'  # Good
  - uid: 'news_24_7'          # Good
  - uid: 'sub1'               # Avoid
```

### Standard Bitrates

**DAB (MPEG Layer II):**
- Speech: 64-96 kbps
- Music: 128-160 kbps
- Premium: 192 kbps

**DAB+ (HE-AAC v2):**
- Speech: 48-56 kbps
- Music: 72-80 kbps
- Premium: 96 kbps

### Protection by Content Type

```yaml
# Critical content
protection:
  level: 4

# Premium content
protection:
  level: 3

# Standard content
protection:
  level: 2

# Strong signal only
protection:
  level: 1
```

---

## Validation Checklist

Before running your configuration:

- [ ] **Unique IDs:** All service IDs and subchannel IDs are unique
- [ ] **Label length:** Ensemble and service labels ≤ 16 chars
- [ ] **Short labels:** ≤ 8 chars (or omit for auto-generation)
- [ ] **Hex format:** All IDs use quoted hex: `'0xXXXX'`
- [ ] **Capacity:** Total CU usage < mode capacity (864 for Mode I)
- [ ] **File paths:** Input files exist and are correct format
- [ ] **Type match:** File format matches subchannel type
- [ ] **Protection range:** Protection level 0-4
- [ ] **Component links:** All services linked to subchannels
- [ ] **PTY codes:** Valid PTY codes (0-31)
- [ ] **Language codes:** Valid language codes
- [ ] **Start addresses:** No overlap between subchannels

---

## Testing Configurations

### Validate Syntax

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Dry run (parse config only)
python -m dabmux.cli -c config.yaml -o /dev/null -n 1
```

### Test Output

```bash
# Generate 100 frames
python -m dabmux.cli -c config.yaml -o test.eti -n 100

# Check output size
ls -lh test.eti

# Continuous generation
python -m dabmux.cli -c config.yaml -o output.eti --continuous
```

### Verify Capacity

```bash
# The multiplexer will warn if capacity exceeded
# Check logs for warnings:
# "WARNING: Total capacity exceeds available CUs"
```

---

## Troubleshooting

### "Capacity exceeded" Error

**Problem:** Total subchannel capacity > mode capacity

**Solution:**
1. Reduce bitrates
2. Lower protection levels
3. Remove services
4. Switch to DAB+ (more efficient)

### "Input file not found"

**Problem:** File path incorrect

**Solution:**
```yaml
# Use absolute paths
input: 'file:///home/user/audio.mp2'

# Or relative to working directory
input: 'file://./audio.mp2'
```

### "Type mismatch" Error

**Problem:** File format doesn't match subchannel type

**Solution:**
```yaml
# For .mp2 files
type: 'audio'

# For .aac files
type: 'dabplus'
```

### Services Not Appearing

**Problem:** Service not linked to subchannel

**Solution:**
```yaml
# Ensure component links service to subchannel
components:
  - service_id: '0x5001'  # Must match service id
    subchannel_id: 0      # Must match subchannel id
```

---

## See Also

- [Ensemble Parameters](ensemble.md): Ensemble configuration details
- [Services](services.md): Service configuration details
- [Subchannels](subchannels.md): Subchannel configuration details
- [Protection Levels](protection.md): Protection level guide
- [CLI Reference](../cli-reference.md): Command-line options
- [Tutorials](../../tutorials/index.md): Step-by-step guides
