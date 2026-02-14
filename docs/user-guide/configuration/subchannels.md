# Subchannel Configuration

Complete reference for subchannel configuration. Subchannels are the actual audio/data streams that carry content.

## Overview

Subchannels define the data streams that carry audio or data. Each subchannel must be linked to a service via a component.

**Required fields:**
- `uid`: Unique identifier
- `id`: Subchannel ID
- `type`: Stream type
- `bitrate`: Data rate in kbps
- `input`: Input source URI

**Optional fields:**
- `start_address`: Position in MST
- `protection`: Error protection settings

## Subchannel Structure

```yaml
subchannels:
  - uid: 'unique_name'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'file://audio.mp2'
```

---

## UID (Unique Identifier)

### `uid`

Internal identifier for the subchannel.

**Type:** String
**Required:** Yes
**Purpose:** Reference in configuration, logging

**Example:**
```yaml
subchannels:
  - uid: 'music_stream'
    id: 0
```

**Guidelines:**
- Descriptive names
- Unique within configuration
- Internal only (not transmitted)

---

## Subchannel ID

### `id`

Numeric identifier for the subchannel.

**Type:** Integer
**Range:** 0 - 63
**Required:** Yes

**Example:**
```yaml
subchannels:
  - id: 0  # First subchannel
  - id: 1  # Second subchannel
  - id: 2  # Third subchannel
```

**Guidelines:**
- Must be unique
- Sequential recommended (0, 1, 2, ...)
- Referenced by components

---

## Subchannel Type

### `type`

The format of audio/data in the subchannel.

**Type:** String
**Values:** `'audio'`, `'dabplus'`, `'packet'`, `'data'`
**Required:** Yes

#### `'audio'` - DAB Audio (MPEG Layer II)

Traditional DAB using MPEG-1 Audio Layer II.

**Use for:** `.mp2` files
**Bitrates:** 32 - 384 kbps (typical: 128-192 kbps)

```yaml
subchannels:
  - uid: 'dab_audio'
    type: 'audio'
    bitrate: 128
    input: 'file://audio.mp2'
```

#### `'dabplus'` - DAB+ Audio (HE-AAC v2)

Modern DAB+ using HE-AAC v2 codec.

**Use for:** `.aac` files
**Bitrates:** 32 - 192 kbps (typical: 48-96 kbps)

```yaml
subchannels:
  - uid: 'dabplus_audio'
    type: 'dabplus'
    bitrate: 72
    input: 'file://audio.aac'
```

#### `'packet'` - Packet Mode Data

Packet mode for data services.

**Use for:** Data services, PAD
**Bitrates:** Variable

```yaml
subchannels:
  - uid: 'data_service'
    type: 'packet'
    bitrate: 32
    input: 'file://data.bin'
```

#### `'data'` - Stream Mode Data

Stream mode for continuous data.

```yaml
subchannels:
  - uid: 'stream_data'
    type: 'data'
    bitrate: 64
    input: 'file://stream.bin'
```

**Type selection guide:**

| Content | File Format | Type |
|---------|-------------|------|
| MPEG Layer II audio | `.mp2` | `'audio'` |
| HE-AAC audio | `.aac` | `'dabplus'` |
| Packet data | `.bin`, packets | `'packet'` |
| Stream data | `.bin`, stream | `'data'` |

---

## Bitrate

### `bitrate`

Data rate in kilobits per second.

**Type:** Integer
**Unit:** kbps
**Required:** Yes

#### Standard DAB Bitrates

For `type: 'audio'` (MPEG Layer II):

| Bitrate | Quality | Use Case |
|---------|---------|----------|
| 32 kbps | Low | Mono speech minimum |
| 48 kbps | Fair | Mono speech |
| 64 kbps | Good | Mono speech/music |
| 80 kbps | Good | Stereo speech |
| 96 kbps | Good | Stereo music |
| 112 kbps | Very Good | Stereo music |
| 128 kbps | Excellent | Standard music |
| 160 kbps | Excellent | High-quality music |
| 192 kbps | Premium | Premium music |
| 224 kbps | Premium | Very high quality |
| 256 kbps | Premium | Exceptional quality |

**Recommended:** 128 kbps for music, 64-96 kbps for speech

#### Standard DAB+ Bitrates

For `type: 'dabplus'` (HE-AAC v2):

| Bitrate | Quality | Use Case |
|---------|---------|----------|
| 32 kbps | Fair | Mono speech |
| 40 kbps | Good | Mono speech |
| 48 kbps | Very Good | Stereo speech |
| 56 kbps | Very Good | Stereo speech/music |
| 64 kbps | Excellent | Stereo music |
| 72 kbps | Excellent | Standard music |
| 80 kbps | Premium | High-quality music |
| 96 kbps | Premium | Premium music |

**Recommended:** 72 kbps for music, 48 kbps for speech

#### Examples

```yaml
# DAB music station
- type: 'audio'
  bitrate: 128

# DAB+ music station (similar quality, lower bitrate)
- type: 'dabplus'
  bitrate: 72

# DAB+ speech/news station
- type: 'dabplus'
  bitrate: 48

# Premium DAB music
- type: 'audio'
  bitrate: 192
```

**Guidelines:**
- Higher bitrate = better quality but more capacity used
- DAB+ is more efficient: 72 kbps DAB+ ≈ 128 kbps DAB
- Match bitrate to content: speech needs less than music
- Must match audio file bitrate

---

## Start Address

### `start_address`

Position in Main Service Transport (MST) in Capacity Units.

**Type:** Integer
**Unit:** Capacity Units (CU)
**Range:** 0 - 863 (Mode I)
**Default:** Auto-calculated
**Required:** No (recommended to specify)

**Example:**
```yaml
subchannels:
  - id: 0
    start_address: 0    # First subchannel
  - id: 1
    start_address: 100  # After subchannel 0
  - id: 2
    start_address: 200  # After subchannel 1
```

**Calculation:**
- First subchannel: `start_address: 0`
- Subsequent: Start after previous subchannel
- Spacing depends on bitrate + protection overhead

**Simplified approach:** Use multiples of 50 or 100 for spacing.

**Mode I capacity:** 864 CU total

---

## Protection

### `protection`

Error protection configuration.

**Type:** Object with `level` and `shortform`
**Required:** No
**Default:** `{level: 2, shortform: true}`

#### `protection.level`

Protection level (0-4).

**Type:** Integer
**Range:** 0 - 4
**Default:** 2

| Level | Protection | Overhead | Use Case |
|-------|------------|----------|----------|
| 0 | Weakest | Lowest | Strong signal only |
| 1 | Weak | Low | Good signal |
| 2 | Moderate | Medium | Normal conditions (default) |
| 3 | Strong | High | Weak signal |
| 4 | Strongest | Highest | Very weak signal |

**Example:**
```yaml
protection:
  level: 2  # Moderate (recommended)
```

#### `protection.shortform`

Use short form protection table.

**Type:** Boolean
**Values:** `true`, `false`
**Default:** `true`

```yaml
protection:
  level: 2
  shortform: true  # Use short form table
```

**Recommendation:** Use `shortform: true` (simpler, widely supported)

See [Protection Levels](protection.md) for detailed explanation.

---

## Input

### `input`

Source of audio/data for the subchannel.

**Type:** String (URI)
**Format:** `protocol://path`
**Required:** Yes

#### File Inputs

**Format:** `file://path`

```yaml
# Relative path
input: 'file://audio.mp2'

# Absolute path (Linux/macOS)
input: 'file:///home/user/audio.mp2'

# Absolute path (Windows)
input: 'file://C:/Users/user/audio.mp2'
```

**Guidelines:**
- Use absolute paths for production
- Relative paths from current directory
- Must match subchannel type (.mp2 for audio, .aac for dabplus)

#### UDP Network Inputs

**Format:** `udp://host:port`

```yaml
# UDP unicast
input: 'udp://192.168.1.100:5001'

# UDP multicast
input: 'udp://239.1.2.3:5001'
```

**Use for:** Live streaming, network sources

#### TCP Network Inputs

**Format:** `tcp://host:port`

```yaml
input: 'tcp://192.168.1.100:5002'
```

**Use for:** Reliable streaming, lower packet loss tolerance

---

## Complete Examples

### DAB Music Service

```yaml
subchannels:
  - uid: 'music_dab'
    id: 0
    type: 'audio'
    bitrate: 192
    start_address: 0
    protection:
      level: 3
      shortform: true
    input: 'file://music.mp2'
```

### DAB+ Music Service

```yaml
subchannels:
  - uid: 'music_dabplus'
    id: 0
    type: 'dabplus'
    bitrate: 72
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'file://music.aac'
```

### DAB+ Speech Service

```yaml
subchannels:
  - uid: 'news_dabplus'
    id: 0
    type: 'dabplus'
    bitrate: 48
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'file://news.aac'
```

### Network Input

```yaml
subchannels:
  - uid: 'live_stream'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'udp://239.1.2.3:5001'
```

### Multiple Subchannels

```yaml
subchannels:
  # Subchannel 0: High-quality music (DAB)
  - uid: 'music_hq'
    id: 0
    type: 'audio'
    bitrate: 192
    start_address: 0
    protection:
      level: 3
    input: 'file://music.mp2'

  # Subchannel 1: News (DAB+)
  - uid: 'news'
    id: 1
    type: 'dabplus'
    bitrate: 64
    start_address: 200
    protection:
      level: 2
    input: 'file://news.aac'

  # Subchannel 2: Pop music (DAB+)
  - uid: 'pop'
    id: 2
    type: 'dabplus'
    bitrate: 80
    start_address: 300
    protection:
      level: 2
    input: 'file://pop.aac'
```

---

## Validation Rules

1. **Unique IDs**
   ```yaml
   ✓ id: 0
   ✓ id: 1
   ✗ id: 0 (duplicate)
   ```

2. **Valid bitrate**
   ```yaml
   ✓ bitrate: 128
   ✗ bitrate: 150 (not standard)
   ```

3. **Type matches input**
   ```yaml
   ✓ type: audio, input: file://audio.mp2
   ✗ type: audio, input: file://audio.aac (mismatch)
   ```

4. **Protection level range**
   ```yaml
   ✓ protection: {level: 2}
   ✗ protection: {level: 5}
   ```

5. **Capacity limits**
   - Total CUs must fit in mode capacity (864 for Mode I)

---

## Common Issues

### Type mismatch

**Error:**
```
ERROR: Expected DAB+ superframe, got MPEG frame
```

**Solution:** Match type to file format
```yaml
# For .mp2 files
type: 'audio'

# For .aac files
type: 'dabplus'
```

### Input not found

**Error:**
```
ERROR: Input file not found: audio.mp2
```

**Solution:** Check path and use `file://` prefix
```yaml
input: 'file://audio.mp2'
```

### Capacity exceeded

**Error:**
```
ERROR: Total capacity exceeds available CUs
```

**Solutions:**
1. Reduce bitrates
2. Lower protection levels
3. Remove subchannels
4. Use DAB+ (more efficient)

---

## Best Practices

### Use DAB+ for Efficiency

```yaml
# DAB+: 72 kbps for music
- type: 'dabplus'
  bitrate: 72

# Equivalent to DAB: 128 kbps
```

### Organize by ID

```yaml
subchannels:
  - id: 0  # First
  - id: 1  # Second
  - id: 2  # Third
```

### Descriptive UIDs

```yaml
uid: 'music_stream'    # Good
uid: 'news_64kbps'     # Good
uid: 'sub1'            # Avoid
```

### Standard Spacing

```yaml
start_address: 0     # First
start_address: 100   # Second
start_address: 200   # Third
```

---

## See Also

- [Protection Levels](protection.md): Detailed protection explanation
- [Services](services.md): Linking subchannels to services
- [Configuration Hierarchy](../../architecture/configuration-hierarchy.md): How subchannels fit in
- [Examples](examples.md): Complete working configurations
