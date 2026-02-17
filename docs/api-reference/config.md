# Configuration Module

Configuration file parsing and validation.

## Module: `dabmux.config`

Provides utilities for loading and parsing YAML configuration files into `DabEnsemble` objects.

## Functions

### `load_config(path: str | Path) -> DabEnsemble`

Load ensemble configuration from YAML file.

**Parameters:**
- `path: str | Path` - Path to YAML configuration file

**Returns:** `DabEnsemble` instance with all services, subchannels, and components configured

**Raises:**
- `FileNotFoundError` - If configuration file doesn't exist
- `ConfigurationError` - If configuration is invalid
- `yaml.YAMLError` - If YAML syntax is invalid

**Example:**
```python
from dabmux.config import load_config

ensemble = load_config('config.yaml')
print(f"Loaded ensemble: {ensemble.label.text}")
print(f"Services: {len(ensemble.services)}")
print(f"Subchannels: {len(ensemble.subchannels)}")
```

### Configuration File Format

YAML configuration with four main sections:

```yaml
ensemble:           # Ensemble configuration
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'My DAB'
    short: 'DAB'
  lto_auto: true

subchannels:        # Audio/data streams
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    protection:
      level: 2
      shortform: true
    input: 'file://audio.mp2'

services:           # Radio stations
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'Radio One'
      short: 'R1'
    pty: 10
    language: 9

components:         # Service ↔ Subchannel links
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
    type: 0
```

## Exceptions

### `ConfigurationError`

Raised when configuration validation fails.

**Base class:** `Exception`

**Common causes:**
- Missing required fields
- Invalid hex values
- Unknown transmission mode
- Invalid protection level
- Missing service or subchannel references

**Example:**
```python
from dabmux.config import load_config, ConfigurationError

try:
    ensemble = load_config('config.yaml')
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Fix configuration and retry
```

## Configuration Validation

The parser validates:

### Ensemble Section

- ✅ `id` must be hex string (e.g., '0xCE15')
- ✅ `ecc` must be hex string (e.g., '0xE1')
- ✅ `transmission_mode` must be 'I', 'II', 'III', or 'IV'
- ✅ `label.text` max 16 characters
- ✅ `label.short` max 8 characters

### Subchannels Section

- ✅ `uid` must be unique string
- ✅ `id` must be 0-63
- ✅ `type` must be 'audio', 'dabplus', 'dmb', or 'packet'
- ✅ `bitrate` must be valid for type (32-384 kbps)
- ✅ `protection.level` must be 0-4
- ✅ `input` must be valid URI (file://, udp://, tcp://)

### Services Section

- ✅ `uid` must be unique string
- ✅ `id` must be hex string (e.g., '0x5001')
- ✅ `label.text` max 16 characters
- ✅ `label.short` max 8 characters
- ✅ `pty` must be 0-31
- ✅ `language` must be 0-127

### Components Section

- ✅ `service_id` must reference existing service
- ✅ `subchannel_id` must reference existing subchannel
- ✅ `type` must be 0 (audio) or 1 (data)

## Examples

### Minimal Configuration

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'Test'

subchannels:
  - uid: 'sub1'
    id: 0
    bitrate: 128
    input: 'file://audio.mp2'

services:
  - uid: 'svc1'
    id: '0x5001'
    label:
      text: 'Test'

components:
  - service_id: '0x5001'
    subchannel_id: 0
```

**Load and verify:**
```python
from dabmux.config import load_config

ensemble = load_config('minimal.yaml')
assert ensemble.id == 0xCE15
assert len(ensemble.services) == 1
assert len(ensemble.subchannels) == 1
```

### Multi-Service Configuration

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Multi Service'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'file://music.mp2'

  - uid: 'audio2'
    id: 1
    type: 'audio'
    bitrate: 96
    start_address: 84
    input: 'file://news.mp2'

  - uid: 'audio3'
    id: 2
    type: 'dabplus'
    bitrate: 72
    start_address: 168
    input: 'file://speech.aac'

services:
  - uid: 'music'
    id: '0x5001'
    label:
      text: 'Music FM'
    pty: 10  # Pop Music

  - uid: 'news'
    id: '0x5002'
    label:
      text: 'News 24'
    pty: 1  # News

  - uid: 'talk'
    id: '0x5003'
    label:
      text: 'Talk Radio'
    pty: 9  # Varied Speech

components:
  - service_id: '0x5001'
    subchannel_id: 0
  - service_id: '0x5002'
    subchannel_id: 1
  - service_id: '0x5003'
    subchannel_id: 2
```

**Load and inspect:**
```python
from dabmux.config import load_config

ensemble = load_config('multi_service.yaml')

# List all services
for service in ensemble.services:
    print(f"{service.label.text} (ID: 0x{service.id:04X})")

# List all subchannels
for subchannel in ensemble.subchannels:
    print(f"Subchannel {subchannel.id}: {subchannel.bitrate} kbps")
```

### Network Input Configuration

```yaml
subchannels:
  - uid: 'live1'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'udp://239.1.2.3:5001'  # UDP multicast

  - uid: 'live2'
    id: 1
    type: 'audio'
    bitrate: 128
    input: 'tcp://192.168.1.100:5002'  # TCP stream
```

### DAB+ Configuration

```yaml
subchannels:
  - uid: 'dabplus1'
    id: 0
    type: 'dabplus'      # HE-AAC v2
    bitrate: 72          # Lower bitrate than DAB
    protection:
      level: 2
    input: 'file://audio.aac'  # AAC file, not MP2
```

## Hex Value Handling

All hex values must be quoted strings with `0x` prefix:

**Correct:**
```yaml
ensemble:
  id: '0xCE15'    # String with 0x prefix
  ecc: '0xE1'

services:
  - id: '0x5001'  # String with 0x prefix
```

**Incorrect:**
```yaml
ensemble:
  id: 0xCE15      # Unquoted (parsed as integer)
  ecc: E1         # No 0x prefix

services:
  - id: 5001      # Decimal integer
```

## URI Schemes

Input URIs support three schemes:

### File URI

```yaml
input: 'file://audio.mp2'              # Relative path
input: 'file:///path/to/audio.mp2'     # Absolute path
```

### UDP URI

```yaml
input: 'udp://239.1.2.3:5001'          # Multicast
input: 'udp://192.168.1.100:5001'      # Unicast
input: 'udp://0.0.0.0:5001'            # Listen on all interfaces
```

### TCP URI

```yaml
input: 'tcp://192.168.1.100:5001'      # Connect to server
input: 'tcp://0.0.0.0:5001'            # Listen for connections
```

## Default Values

If not specified, these defaults are used:

```yaml
ensemble:
  ecc: '0xE1'                # Germany
  transmission_mode: 'I'     # Mode I
  lto_auto: true            # Automatic local time offset

subchannels:
  type: 'audio'             # MPEG Layer II
  start_address: 0          # Auto-calculated
  protection:
    level: 2                # Moderate protection
    shortform: true         # UEP (Unequal Error Protection)

services:
  pty: 0                    # No programme type
  language: 9               # English
  country_id: 0             # From ensemble ECC

components:
  type: 0                   # Audio component
```

## Configuration Tips

### 1. Use Descriptive UIDs

```yaml
# Good
subchannels:
  - uid: 'music_128kbps'
  - uid: 'news_96kbps'

# Bad
subchannels:
  - uid: 'sub1'
  - uid: 'sub2'
```

### 2. Calculate Start Addresses

For Mode I (864 CU total capacity):

```yaml
subchannels:
  - id: 0
    bitrate: 128
    start_address: 0      # First subchannel

  - id: 1
    bitrate: 96
    start_address: 84     # After first (128 kbps ≈ 84 CU)

  - id: 2
    bitrate: 64
    start_address: 147    # After second (96 kbps ≈ 63 CU)
```

Or use `start_address: 0` for all and let the multiplexer calculate automatically.

### 3. Match Service IDs with Components

```yaml
services:
  - uid: 'radio1'
    id: '0x5001'        # Remember this ID

components:
  - uid: 'comp1'
    service_id: '0x5001'  # Must match service ID
    subchannel_id: 0      # Links to subchannel 0
```

### 4. Use Comments Liberally

```yaml
ensemble:
  id: '0xCE15'          # Custom ensemble ID for testing
  ecc: '0xE1'           # Germany (0xE1)

subchannels:
  - uid: 'audio1'
    id: 0
    bitrate: 128        # Standard music quality
    input: 'file://music.mp2'  # Looping background music
```

## See Also

- [Configuration Reference](../user-guide/configuration/index.md) - Complete configuration guide
- [Core API](core.md) - DabEnsemble and related classes
- [Examples](../user-guide/configuration/examples.md) - More configuration examples
- [Troubleshooting](../troubleshooting/common-errors.md) - Configuration error solutions
