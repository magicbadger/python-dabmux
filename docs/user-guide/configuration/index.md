# Configuration Reference

Complete reference for python-dabmux YAML configuration files.

## Overview

python-dabmux uses YAML configuration files to define the structure of a DAB ensemble. The configuration includes:

- **Ensemble**: Top-level container with ID, country code, and transmission parameters
- **Subchannels**: Audio/data streams with bitrates and protection levels
- **Services**: Radio stations with labels and metadata
- **Components**: Links between services and subchannels

## Configuration Structure

```yaml
ensemble:
  # Ensemble-level parameters

subchannels:
  # List of audio/data streams

services:
  # List of radio stations

components:
  # Links between services and subchannels
```

## Quick Example

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'My DAB'
    short: 'DAB'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    protection:
      level: 2
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'Radio One'
      short: 'Radio1'
    pty: 1
    language: 9

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
    type: 0
```

## Section Reference

### [Ensemble Parameters](ensemble.md)

Top-level ensemble configuration including:

- Ensemble ID and Extended Country Code (ECC)
- Transmission mode (I, II, III, IV)
- Ensemble label
- Local Time Offset (LTO)

[Read more →](ensemble.md)

### [Services](services.md)

Service (radio station) configuration including:

- Service ID and labels
- Programme Type (PTY)
- Language code

[Read more →](services.md)

### [Subchannels](subchannels.md)

Subchannel (data stream) configuration including:

- Subchannel type (DAB, DAB+, packet, data)
- Bitrate and start address
- Input source (file or network)
- Protection settings

[Read more →](subchannels.md)

### [Protection Levels](protection.md)

Error protection configuration including:

- UEP (Unequal Error Protection) levels (0-4)
- Short form vs long form protection
- Trade-offs and recommendations

[Read more →](protection.md)

### [Configuration Examples](examples.md)

Complete working examples including:

- Single service configuration
- Multi-service ensemble
- DAB+ configuration
- Network input configuration

[Read more →](examples.md)

## Configuration Hierarchy

The relationship between configuration elements:

```
Ensemble (0xCE15 "My DAB")
  │
  ├─► Service 1 (0x5001 "Radio One")
  │     └─► Component 1
  │           └─► Subchannel 0 (128 kbps, audio)
  │                 └─► Input: file://audio1.mp2
  │
  ├─► Service 2 (0x5002 "Radio Two")
  │     └─► Component 2
  │           └─► Subchannel 1 (128 kbps, audio)
  │                 └─► Input: udp://239.1.2.3:5001
  │
  └─► Service 3 (0x5003 "Radio Three")
        └─► Component 3
              └─► Subchannel 2 (96 kbps, dabplus)
                    └─► Input: file://audio3.aac
```

**Key points:**

1. **Ensemble** contains all services
2. **Services** are what listeners see
3. **Components** link services to subchannels
4. **Subchannels** carry the actual audio data
5. **Inputs** provide data to subchannels

## YAML Syntax

### Basic Types

```yaml
# Strings (quotes optional unless they contain special characters)
text: 'Hello World'
text: Hello World

# Numbers
number: 42
hex: '0xCE15'  # Hex values must be quoted

# Booleans
enabled: true
disabled: false

# Lists
items:
  - item1
  - item2
  - item3
```

### Indentation

YAML uses **spaces** for indentation (not tabs):

```yaml
ensemble:
  id: '0xCE15'          # 2 spaces
  label:
    text: 'My DAB'      # 4 spaces
    short: 'DAB'        # 4 spaces
```

### Comments

```yaml
# This is a comment
ensemble:
  id: '0xCE15'          # Inline comment
  # Another comment
  ecc: '0xE1'
```

## Validation

python-dabmux validates configuration files and reports errors:

### Missing Required Fields

```
ERROR: Missing 'ensemble' section in configuration
```

**Solution:** Add `ensemble:` section

### Invalid Hex Values

```
ERROR: Invalid ensemble ID: CE15
```

**Solution:** Add `0x` prefix: `id: '0xCE15'`

### Mismatched IDs

```
ERROR: Component references unknown service_id: 0x5999
```

**Solution:** Ensure `service_id` in components matches a service `id`

### Invalid Bitrate

```
ERROR: Invalid bitrate: 150 (not a standard DAB bitrate)
```

**Solution:** Use standard bitrates: 32, 48, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384

## Common Patterns

### Single Service

Simplest configuration with one radio station:

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Single Service'
    short: 'Single'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    protection:
      level: 2
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'My Station'

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
```

### Multiple Services

Ensemble with multiple stations:

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Multi Service'
    short: 'Multi'

subchannels:
  - uid: 'audio1'
    id: 0
    bitrate: 128
    input: 'file://audio1.mp2'
  - uid: 'audio2'
    id: 1
    bitrate: 128
    input: 'file://audio2.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'Station 1'
  - uid: 'service2'
    id: '0x5002'
    label:
      text: 'Station 2'

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
  - uid: 'comp2'
    service_id: '0x5002'
    subchannel_id: 1
```

### Network Input

Using UDP/TCP network inputs:

```yaml
subchannels:
  # UDP unicast
  - uid: 'audio1'
    id: 0
    input: 'udp://192.168.1.100:5001'

  # UDP multicast
  - uid: 'audio2'
    id: 1
    input: 'udp://239.1.2.3:5002'

  # TCP
  - uid: 'audio3'
    id: 2
    input: 'tcp://192.168.1.100:5003'
```

### DAB+ Configuration

Using DAB+ (HE-AAC) instead of MPEG Layer II:

```yaml
subchannels:
  - uid: 'dabplus1'
    id: 0
    type: 'dabplus'          # DAB+ type
    bitrate: 72              # Lower bitrate possible
    input: 'file://audio.aac'  # AAC input file
```

## Best Practices

### Use Meaningful UIDs

```yaml
# Good
services:
  - uid: 'bbc_radio1'
    id: '0x5001'

# Bad
services:
  - uid: 'svc1'
    id: '0x5001'
```

### Choose Appropriate Bitrates

- **128 kbps**: Standard for music (DAB MPEG Layer II)
- **192 kbps**: High-quality music (DAB)
- **64-80 kbps**: Speech/talk radio (DAB+)
- **48-72 kbps**: Music (DAB+)

### Select Protection Levels

- **Level 2**: Default, good for most conditions
- **Level 3**: Weak signal areas
- **Level 4**: Very weak signal, data services

### Use Absolute Paths for Production

```yaml
# Development
input: 'file://audio.mp2'

# Production
input: 'file:///var/dabmux/audio.mp2'
```

### Document Your Configuration

```yaml
ensemble:
  # Production ensemble for City Radio
  id: '0xCE15'
  # Germany
  ecc: '0xE1'
  # Mode I (standard terrestrial)
  transmission_mode: 'I'
```

## Loading Configuration

### From Python

```python
from dabmux.config import load_config

ensemble = load_config('config.yaml')
```

### From CLI

```bash
dabmux -c config.yaml -o output.eti
```

## See Also

- [Ensemble Parameters](ensemble.md): Detailed ensemble configuration
- [Services](services.md): Service configuration reference
- [Subchannels](subchannels.md): Subchannel configuration reference
- [Protection Levels](protection.md): Error protection details
- [Examples](examples.md): Complete working examples
- [CLI Reference](../cli-reference.md): Command-line options
- [Basic Concepts](../../getting-started/basic-concepts.md): DAB terminology
