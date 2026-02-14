# Ensemble Parameters

Complete reference for ensemble-level configuration parameters.

## Overview

The `ensemble` section defines top-level parameters that apply to the entire DAB multiplex.

**Required fields:**
- `id`: Ensemble identifier
- `label`: Ensemble name

**Optional fields:**
- `ecc`: Extended Country Code
- `transmission_mode`: RF transmission mode
- `lto_auto`: Automatic local time offset
- `lto`: Manual local time offset

## Ensemble ID

### `id`

Unique 16-bit identifier for the ensemble.

**Type:** String (hex) or Integer
**Format:** `'0xXXXX'` (hex string, quoted)
**Range:** 0x0000 - 0xFFFF (0 - 65535)
**Required:** Yes

**Example:**
```yaml
ensemble:
  id: '0xCE15'
```

**Guidelines:**
- Use hex format with quotes: `'0xCE15'`
- Must be unique in your broadcast area
- Typically assigned by broadcast authority
- Avoid 0x0000 (reserved)

**Common mistakes:**
```yaml
# Wrong - missing quotes
id: 0xCE15

# Wrong - missing 0x prefix
id: 'CE15'

# Correct
id: '0xCE15'
```

---

## Extended Country Code (ECC)

### `ecc`

Identifies the country of broadcast.

**Type:** String (hex) or Integer
**Format:** `'0xXX'` (hex string, quoted)
**Range:** 0x00 - 0xFF
**Default:** 0xE1 (Germany)
**Required:** No (but recommended)

**Common values:**

| ECC | Country |
|-----|---------|
| `'0xE0'` | Germany (alternative) |
| `'0xE1'` | Germany |
| `'0xE2'` | United Kingdom |
| `'0xE3'` | Switzerland |
| `'0xE4'` | Denmark |
| `'0xF0'` | France |
| `'0xF1'` | Belgium |

**Example:**
```yaml
ensemble:
  ecc: '0xE1'  # Germany
```

**Purpose:**
- Helps receivers identify broadcast country
- Used for regional service restrictions
- Required for proper EPG integration

---

## Transmission Mode

### `transmission_mode`

DAB transmission mode defining RF characteristics.

**Type:** String or Integer
**Values:** `'I'`, `'II'`, `'III'`, `'IV'` (or `1`, `2`, `3`, `4`)
**Default:** `'I'`
**Required:** No

**Modes:**

| Mode | Bandwidth | Frame Duration | Capacity | Use Case |
|------|-----------|----------------|----------|----------|
| I | 1.536 MHz | 96 ms | 864 CU | Standard terrestrial (most common) |
| II | 384 kHz | 24 ms | 216 CU | Local/indoor, cable |
| III | 192 kHz | 24 ms | 108 CU | Cable/satellite |
| IV | 768 kHz | 48 ms | 432 CU | Regional, mobile |

**Example:**
```yaml
ensemble:
  transmission_mode: 'I'  # Standard mode
```

**Recommendations:**
- **Mode I**: Default for terrestrial broadcasting (99% of use cases)
- **Mode II**: Indoor/local transmitters
- **Mode III**: Cable distribution
- **Mode IV**: Mobile/regional coverage

**Note:** Mode determines frame timing and capacity. Most DAB broadcasts use Mode I.

---

## Ensemble Label

### `label`

The name of the ensemble displayed to listeners.

**Type:** Object with `text` and optional `short` fields
**Required:** Yes

#### `label.text`

Full ensemble name.

**Type:** String
**Max length:** 16 characters
**Character set:** EBU Latin (ASCII-compatible subset)
**Required:** Yes

**Example:**
```yaml
ensemble:
  label:
    text: 'BBC DAB'
```

**Guidelines:**
- Keep it descriptive but concise
- Avoid special characters
- Use spaces for readability
- Max 16 characters (strictly enforced)

#### `label.short`

Abbreviated ensemble name.

**Type:** String
**Max length:** 8 characters
**Required:** No (auto-generated if omitted)
**Default:** First 8 characters of `text`

**Example:**
```yaml
ensemble:
  label:
    text: 'My Radio Network'
    short: 'MyRadio'  # 8 chars
```

**Guidelines:**
- Used on small displays
- Should be recognizable abbreviation
- Remove vowels if needed to fit: "MyRadio" → "MyRdio"

**Label validation:**
```yaml
# Valid
label:
  text: 'Test Ensemble'    # 13 chars - OK
  short: 'Test'            # 4 chars - OK

# Invalid - too long
label:
  text: 'This is a very long name'  # 24 chars - ERROR
  short: 'TooLongName'                # 11 chars - ERROR

# Auto short label
label:
  text: 'Test Ensemble'    # short = 'Test Ens' (first 8 chars)
```

---

## Local Time Offset

### `lto_auto`

Automatically calculate local time offset from system timezone.

**Type:** Boolean
**Values:** `true`, `false`
**Default:** `true`
**Required:** No

**Example:**
```yaml
ensemble:
  lto_auto: true
```

**Behavior:**
- `true`: Automatically detect timezone offset from system
- `false`: Use manual `lto` value

**Recommended:** Use `true` unless you have specific requirements.

### `lto`

Manual local time offset in half-hour increments.

**Type:** Integer
**Range:** -24 to +24 (in half-hours)
**Unit:** Half-hours relative to UTC
**Default:** 0
**Required:** Only if `lto_auto: false`

**Examples:**
```yaml
# UTC (no offset)
lto_auto: false
lto: 0

# UTC+1 (Central European Time in winter)
lto_auto: false
lto: 2  # +1 hour = 2 half-hours

# UTC+5:30 (India Standard Time)
lto_auto: false
lto: 11  # +5.5 hours = 11 half-hours

# UTC-5 (US Eastern Time in winter)
lto_auto: false
lto: -10  # -5 hours = -10 half-hours
```

**Calculation:**
```
LTO value = (hours × 2) + (minutes / 30)

Examples:
UTC+1:00  → 1 × 2 + 0 = 2
UTC+1:30  → 1 × 2 + 1 = 3
UTC-5:00  → -5 × 2 + 0 = -10
UTC+5:30  → 5 × 2 + 1 = 11
```

---

## Complete Example

### Minimal Configuration

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'My DAB'
```

Uses defaults:
- ECC: 0xE1 (Germany)
- Transmission mode: I
- LTO: Auto

### Full Configuration

```yaml
ensemble:
  # Identification
  id: '0xCE15'
  ecc: '0xE2'  # United Kingdom

  # RF parameters
  transmission_mode: 'I'

  # Labels
  label:
    text: 'BBC Radio DAB'
    short: 'BBC DAB'

  # Time
  lto_auto: true
```

### Manual Time Offset

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'Test Ensemble'

  # Manual time offset (UTC+1)
  lto_auto: false
  lto: 2  # +1 hour
```

---

## Validation Rules

python-dabmux validates ensemble configuration:

1. **ID present and valid**
   ```
   ✓ id: '0xCE15'
   ✗ id: (missing)
   ✗ id: 0xFFFFFF (out of range)
   ```

2. **Label length**
   ```
   ✓ text: 'Test' (4 chars)
   ✓ text: 'Sixteen Char Txt' (16 chars)
   ✗ text: 'This is too long!' (17 chars)
   ```

3. **ECC format**
   ```
   ✓ ecc: '0xE1'
   ✗ ecc: 'E1' (missing 0x)
   ```

4. **Transmission mode**
   ```
   ✓ transmission_mode: 'I'
   ✓ transmission_mode: 1
   ✗ transmission_mode: 'V' (invalid)
   ```

5. **LTO range**
   ```
   ✓ lto: 2
   ✓ lto: -10
   ✗ lto: 50 (out of range)
   ```

---

## Common Issues

### Label too long error

**Error:**
```
ERROR: Label text exceeds 16 characters
```

**Solution:**
```yaml
# Shorten the label
label:
  text: 'My DAB Network'  # 14 chars - OK
```

### Invalid hex format

**Error:**
```
ERROR: Invalid hex value: CE15
```

**Solution:**
```yaml
# Add quotes and 0x prefix
id: '0xCE15'  # Correct
```

### Missing required field

**Error:**
```
ERROR: Missing required field: id
```

**Solution:**
```yaml
ensemble:
  id: '0xCE15'  # Required
  label:
    text: 'My DAB'  # Required
```

---

## See Also

- [Services](services.md): Service configuration
- [Subchannels](subchannels.md): Audio stream configuration
- [Configuration Hierarchy](../../architecture/configuration-hierarchy.md): How elements relate
- [Examples](examples.md): Complete working configurations
