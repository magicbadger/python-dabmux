# Character Encoding

EBU Latin character set and UTF-8 conversion for DAB labels.

## Overview

DAB uses the **EBU Latin character set** for all text labels (ensemble names, service names, etc.). This is a subset of UTF-8 designed for European languages.

## EBU Latin Character Set

### Supported Characters

**Basic Latin** (compatible with ASCII):
- A-Z, a-z (uppercase and lowercase letters)
- 0-9 (digits)
- Space and common punctuation: `. , ; : ! ? ' " - ( ) /`
- Math symbols: `+ = # @ & *`

**Extended Latin** (accented characters):
- German: `ä ö ü ß Ä Ö Ü`
- French: `é è ê ë à â ç ù û ï ô É È Ê À Ç`
- Spanish: `á é í ó ú ñ Á É Í Ó Ú Ñ`
- Italian: `à è ì ò ù À È Ì Ò Ù`
- Portuguese: `ã õ ç Ã Õ Ç`
- Nordic: `å æ ø Å Æ Ø`
- And more...

### Character Limits

| Type | Long Label | Short Label |
|------|-----------|-------------|
| **Length** | 16 characters | 8 characters |
| **Encoding** | EBU Latin | EBU Latin |
| **Bytes** | 16 bytes | 8 bytes |

**Note**: Most EBU Latin characters are single-byte (same as ASCII). Special characters may use multi-byte encoding.

## Python API

### Module: `dabmux.utils.charset`

```python
from dabmux.utils.charset import utf8_to_ebu, ebu_to_utf8

# Convert UTF-8 string to EBU Latin bytes
ebu_bytes = utf8_to_ebu("Rádio Música")

# Convert EBU Latin bytes back to UTF-8 string
utf8_string = ebu_to_utf8(ebu_bytes)
```

### Functions

#### `utf8_to_ebu(text: str) -> bytes`

Convert UTF-8 string to EBU Latin bytes.

**Parameters:**
- `text: str` - UTF-8 string (max 16 characters for labels)

**Returns:** EBU Latin encoded bytes

**Raises:**
- `ValueError` - If string contains unsupported characters
- `ValueError` - If string is too long

**Example:**
```python
from dabmux.utils.charset import utf8_to_ebu

# Basic ASCII (no conversion needed)
label = utf8_to_ebu("Radio One")
assert len(label) == 9  # 9 bytes

# German umlauts
label = utf8_to_ebu("Süddeutsch FM")
assert len(label) == 14  # ü is encoded

# French accents
label = utf8_to_ebu("Musique Café")
assert len(label) == 12
```

#### `ebu_to_utf8(data: bytes) -> str`

Convert EBU Latin bytes to UTF-8 string.

**Parameters:**
- `data: bytes` - EBU Latin encoded bytes

**Returns:** UTF-8 string

**Example:**
```python
from dabmux.utils.charset import ebu_to_utf8

ebu_bytes = b'Radio One'
text = ebu_to_utf8(ebu_bytes)
assert text == "Radio One"
```

## Label Configuration

### YAML Configuration

Labels are specified as UTF-8 strings in configuration files. python-dabmux automatically converts them to EBU Latin.

```yaml
ensemble:
  label:
    text: 'My DAB Ensemble'  # UTF-8, auto-converted to EBU
    short: 'MyDAB'

services:
  - uid: 'service1'
    label:
      text: 'Rádio Música'     # Portuguese characters
      short: 'Música'

  - uid: 'service2'
    label:
      text: 'Süddeutsch FM'    # German umlauts
      short: 'SüdFM'
```

### Python API

```python
from dabmux.core.mux_elements import DabLabel, DabService

# Create label with non-ASCII characters
label = DabLabel(
    text='Français Radio',  # UTF-8 string
    short='FrRadio'
)

# Create service
service = DabService(
    uid='french',
    id=0x5001,
    label_text='Français Radio',
    label_short='FrRadio'
)
```

## Supported Languages

### Germanic Languages

**German:**
```yaml
label:
  text: 'Süddeutsche'  # ü supported
  short: 'Süd'
```

**Dutch:**
```yaml
label:
  text: 'Nederlandse'  # No special chars needed
```

**Swedish/Norwegian:**
```yaml
label:
  text: 'Göteborg'  # ö supported
  short: 'Göteborg'
```

**Danish:**
```yaml
label:
  text: 'København'  # ø supported
```

### Romance Languages

**French:**
```yaml
label:
  text: 'Français Musique'  # ç, é supported
  short: 'FrMus'
```

**Spanish:**
```yaml
label:
  text: 'Español Radio'  # ñ, á supported
  short: 'EspRadio'
```

**Italian:**
```yaml
label:
  text: 'Italiano'  # à, è, ì, ò, ù supported
```

**Portuguese:**
```yaml
label:
  text: 'Português'  # ã, õ, ç supported
```

### Other European Languages

**Polish:**
```yaml
label:
  text: 'Polskie Radio'  # ł, ą, ę, ó, ś, ż, ź supported
```

**Czech:**
```yaml
label:
  text: 'České Rádio'  # č, š, ž, ř, ý, á, é supported
```

## Unsupported Characters

### Non-European Scripts

❌ **Not supported:**
- Cyrillic (Russian, Bulgarian, Ukrainian)
- Greek
- Arabic
- Hebrew
- Asian scripts (Chinese, Japanese, Korean)
- Emoji

**Workaround:** Use ASCII transliteration:
```yaml
# Instead of "Русское радио" (Cyrillic)
label:
  text: 'Russkoye Radio'  # ASCII transliteration
```

### Special Symbols

❌ **Limited support:**
- Most mathematical symbols
- Currency symbols (except basic ones)
- Box-drawing characters
- Control characters

## Character Length Considerations

### Counting Characters

```python
def count_label_length(text: str) -> int:
    """Count EBU Latin length of label."""
    from dabmux.utils.charset import utf8_to_ebu
    return len(utf8_to_ebu(text))

# Examples
assert count_label_length("Radio") == 5
assert count_label_length("Rádio") == 5  # á is 1 byte in EBU
assert count_label_length("Süd") == 3    # ü is 1 byte in EBU
```

### Truncation

If label is too long, truncate before conversion:

```python
def truncate_label(text: str, max_len: int = 16) -> str:
    """Truncate label to max length."""
    from dabmux.utils.charset import utf8_to_ebu

    # Truncate character by character until it fits
    while len(utf8_to_ebu(text)) > max_len:
        text = text[:-1]

    return text

# Example
long_label = "This is a very long radio station name"
short = truncate_label(long_label, max_len=16)
# Result: "This is a very"
```

## Dynamic Text (DLS)

**Note:** Dynamic Label Segment (DLS) for scrolling text on DAB+ uses a different character encoding (UTF-8 directly). This is separate from static labels.

## Validation

### Check Label Validity

```python
from dabmux.utils.charset import is_valid_ebu_label

def validate_label(text: str, max_len: int = 16) -> bool:
    """Check if label is valid for DAB."""
    if len(text) > max_len:
        return False

    try:
        from dabmux.utils.charset import utf8_to_ebu
        ebu_bytes = utf8_to_ebu(text)
        return len(ebu_bytes) <= max_len
    except ValueError:
        return False

# Examples
assert validate_label("Radio One") == True
assert validate_label("Rádio Música") == True
assert validate_label("This is way too long for a label") == False
assert validate_label("Русское радио") == False  # Cyrillic not supported
```

## Configuration Validation

python-dabmux automatically validates labels during configuration loading:

```python
from dabmux.config import load_config, ConfigurationError

try:
    ensemble = load_config('config.yaml')
except ConfigurationError as e:
    print(f"Invalid label: {e}")
    # Example error: "Label 'Русское радио' contains unsupported characters"
```

## Best Practices

1. **Use ASCII when possible** for maximum compatibility
2. **Test labels** with actual DAB receivers
3. **Avoid ambiguous characters** (e.g., `0` vs `O`, `1` vs `l`)
4. **Keep short labels meaningful** (8 characters is very short)
5. **Use standard abbreviations** for short labels (e.g., "FM", "News", "Rock")

### Good Label Examples

```yaml
# Clear, readable, fits in 16 chars
services:
  - label:
      text: 'BBC Radio 1'
      short: 'Radio 1'

  - label:
      text: 'Classic FM'
      short: 'Classic'

  - label:
      text: 'News 24/7'
      short: 'News 24'
```

### Poor Label Examples

```yaml
# Too long (will be truncated)
services:
  - label:
      text: 'This Is The Best Radio Station Ever'  # > 16 chars

  # Ambiguous characters
  - label:
      text: 'l0O1Il'  # Hard to read

  # Unsupported characters
  - label:
      text: '🎵 Music 🎵'  # Emoji not supported
```

## Character Reference Table

Common accented characters in EBU Latin:

| Char | Name | Used In |
|------|------|---------|
| `à` | a grave | French, Italian, Portuguese |
| `á` | a acute | Spanish, Portuguese, Czech |
| `â` | a circumflex | French, Portuguese |
| `ä` | a umlaut | German, Swedish |
| `ã` | a tilde | Portuguese |
| `ç` | c cedilla | French, Portuguese |
| `é` | e acute | French, Spanish, Portuguese |
| `è` | e grave | French, Italian |
| `ê` | e circumflex | French, Portuguese |
| `ë` | e umlaut | French |
| `í` | i acute | Spanish, Portuguese |
| `ñ` | n tilde | Spanish |
| `ö` | o umlaut | German, Swedish |
| `ø` | o slash | Norwegian, Danish |
| `ü` | u umlaut | German |
| `å` | a ring | Swedish, Norwegian, Danish |
| `æ` | ae ligature | Danish, Norwegian |

## See Also

- [Configuration: Labels](../user-guide/configuration/ensemble.md#labels) - Label configuration guide
- [Standards: ETSI EN 300 401](../standards/etsi-references.md) - Character set specification
- [API: DabLabel](../api-reference/core.md#dablabel) - Label class API
