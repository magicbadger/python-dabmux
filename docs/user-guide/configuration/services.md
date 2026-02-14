# Service Configuration

Complete reference for service configuration parameters. Services are the radio stations that listeners see.

## Overview

Services represent individual radio stations or programs within the ensemble. Each service must be linked to a subchannel via a component.

**Required fields:**
- `uid`: Unique identifier
- `id`: Service ID
- `label`: Service name

**Optional fields:**
- `pty`: Programme Type
- `language`: Language code

## Service Structure

```yaml
services:
  - uid: 'unique_name'
    id: '0xXXXX'
    label:
      text: 'Station Name'
      short: 'Short'
    pty: 10
    language: 9
```

---

## UID (Unique Identifier)

### `uid`

Internal identifier for the service (not transmitted).

**Type:** String
**Required:** Yes
**Purpose:** Reference this service in components

**Example:**
```yaml
services:
  - uid: 'bbc_radio1'
    id: '0x5001'
```

**Guidelines:**
- Use descriptive names
- Must be unique within configuration
- Only used internally (not visible to listeners)
- Alphanumeric and underscores recommended

**Good UIDs:**
```yaml
uid: 'bbc_radio1'
uid: 'news_24_7'
uid: 'classical_music'
```

**Avoid:**
```yaml
uid: 'svc1'  # Not descriptive
uid: '0x5001'  # Confusing with service ID
```

---

## Service ID

### `id`

Unique 16-bit identifier transmitted with the service.

**Type:** String (hex) or Integer
**Format:** `'0xXXXX'` (hex string, quoted)
**Range:** 0x0000 - 0xFFFF
**Required:** Yes

**Example:**
```yaml
services:
  - id: '0x5001'
  - id: '0x5002'
  - id: '0x5003'
```

**Guidelines:**
- Must be unique within ensemble
- Typically starts from 0x5001
- Use sequential IDs for organization
- Must be quoted with 0x prefix

**ID allocation patterns:**
```yaml
# Sequential (recommended)
services:
  - id: '0x5001'  # First service
  - id: '0x5002'  # Second service
  - id: '0x5003'  # Third service

# By category
services:
  - id: '0x6001'  # Music services
  - id: '0x6002'
  - id: '0x7001'  # News services
  - id: '0x7002'
```

**Reserved values:**
- 0x0000: Reserved
- Avoid 0xFFFF

---

## Service Label

### `label`

The name of the service displayed to listeners.

**Type:** Object with `text` and optional `short`
**Required:** Yes

#### `label.text`

Full service/station name.

**Type:** String
**Max length:** 16 characters
**Character set:** EBU Latin
**Required:** Yes

**Examples:**
```yaml
# Good labels
label:
  text: 'BBC Radio 1'     # 11 chars
  text: 'Classic FM'      # 10 chars
  text: 'News 24/7'       # 9 chars

# Maximum length
label:
  text: 'Sixteen Char Svc' # 16 chars - OK
  text: 'This Is Too Long' # 17 chars - ERROR
```

**Guidelines:**
- Clear and recognizable
- Avoid abbreviations unless necessary
- Use proper capitalization
- Include station branding

#### `label.short`

Abbreviated service name for small displays.

**Type:** String
**Max length:** 8 characters
**Required:** No (auto-generated if omitted)
**Default:** First 8 characters of `text`

**Examples:**
```yaml
# Manual short label
label:
  text: 'BBC Radio 1'
  short: 'BBC R1'  # 6 chars

# Auto-generated (omit short field)
label:
  text: 'BBC Radio 1'  # short = 'BBC Radi' (first 8)
```

**Abbreviation strategies:**
```yaml
# Remove spaces
text: 'Pop Music Radio'
short: 'PopMusic'

# Use initials
text: 'Classical Music FM'
short: 'CM FM'

# Remove vowels
text: 'News Radio'
short: 'NwsRadio'
```

---

## Programme Type (PTY)

### `pty`

Categorizes the service content type.

**Type:** Integer
**Range:** 0 - 31
**Default:** 0 (None/Undefined)
**Required:** No (but recommended)

**Standard PTY codes:**

| Code | Category | Description |
|------|----------|-------------|
| 0 | None | Unspecified/varied content |
| 1 | News | News and current affairs |
| 2 | Current Affairs | Analysis and discussion |
| 3 | Information | General information |
| 4 | Sport | Sports content |
| 5 | Education | Educational programmes |
| 6 | Drama | Drama and culture |
| 7 | Cultures | Arts and culture |
| 8 | Science | Science programming |
| 9 | Varied Speech | Talk/variety |
| 10 | Pop Music | Popular music |
| 11 | Rock Music | Rock music |
| 12 | Easy Listening | Easy listening/MOR |
| 13 | Light Classical | Light classical |
| 14 | Serious Classical | Classical music |
| 15 | Other Music | Other musical styles |
| 16 | Weather | Weather information |
| 17 | Finance | Business/finance |
| 18 | Children's | Children's programmes |
| 19 | Social Affairs | Social issues |
| 20 | Religion | Religious programming |
| 21 | Phone In | Call-in shows |
| 22 | Travel | Travel information |
| 23 | Leisure | Leisure and hobby |
| 24 | Jazz Music | Jazz |
| 25 | Country Music | Country music |
| 26 | National Music | National/folk music |
| 27 | Oldies Music | Oldies/retro |
| 28 | Folk Music | Folk music |
| 29 | Documentary | Documentaries |
| 30 | Alarm Test | Emergency test |
| 31 | Alarm | Emergency broadcast |

**Examples:**
```yaml
# News station
services:
  - label:
      text: 'News 24/7'
    pty: 1  # News

# Music station
services:
  - label:
      text: 'Pop Hits Radio'
    pty: 10  # Pop Music

# Classical station
services:
  - label:
      text: 'Classical FM'
    pty: 14  # Serious Classical

# Talk radio
services:
  - label:
      text: 'Talk Radio'
    pty: 9  # Varied Speech
```

**Purpose:**
- Helps receivers filter/search stations
- Used for "genre search" features
- Displayed on receiver screens
- Important for user experience

**Choosing PTY:**
- Select the primary content type
- If mixed content, use 0 (None)
- Be consistent across similar services

---

## Language Code

### `language`

Indicates the primary language of the service.

**Type:** Integer
**Range:** 0 - 255
**Default:** 0 (Unknown)
**Required:** No (but recommended)

**Common language codes:**

| Code | Language |
|------|----------|
| 0 | Unknown/Not applicable |
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

**Examples:**
```yaml
# English service
services:
  - label:
      text: 'BBC Radio 1'
    language: 9  # English

# French service
services:
  - label:
      text: 'Radio France'
    language: 15  # French

# German service
services:
  - label:
      text: 'Deutschlandfunk'
    language: 8  # German
```

**Purpose:**
- Helps receivers filter by language
- Used for "language search" features
- Important for multilingual areas

---

## Complete Examples

### Minimal Service

```yaml
services:
  - uid: 'simple_service'
    id: '0x5001'
    label:
      text: 'My Radio'
```

### Full Service Configuration

```yaml
services:
  - uid: 'complete_service'
    id: '0x5001'
    label:
      text: 'BBC Radio 1'
      short: 'BBC R1'
    pty: 10       # Pop Music
    language: 9   # English
```

### Multiple Services

```yaml
services:
  # News service
  - uid: 'news_service'
    id: '0x5001'
    label:
      text: 'News 24/7'
      short: 'News24'
    pty: 1        # News
    language: 9   # English

  # Music service
  - uid: 'music_service'
    id: '0x5002'
    label:
      text: 'Pop Hits Radio'
      short: 'PopHits'
    pty: 10       # Pop Music
    language: 9   # English

  # Classical service
  - uid: 'classical_service'
    id: '0x5003'
    label:
      text: 'Classical FM'
      short: 'Classic'
    pty: 14       # Serious Classical
    language: 9   # English
```

---

## Linking Services to Subchannels

Services must be linked to subchannels via components:

```yaml
services:
  - uid: 'radio_one'
    id: '0x5001'
    label:
      text: 'Radio One'

components:
  - uid: 'radio_one_comp'
    service_id: '0x5001'    # References service above
    subchannel_id: 0        # References subchannel
    type: 0                 # Audio component
```

See [Components](../../architecture/configuration-hierarchy.md) for details.

---

## Validation Rules

1. **Unique UIDs**
   ```yaml
   ✓ uid: 'service1'
   ✓ uid: 'service2'
   ✗ uid: 'service1' (duplicate)
   ```

2. **Unique Service IDs**
   ```yaml
   ✓ id: '0x5001'
   ✓ id: '0x5002'
   ✗ id: '0x5001' (duplicate)
   ```

3. **Label length**
   ```yaml
   ✓ text: 'BBC Radio' (9 chars)
   ✗ text: 'Very Long Station Name' (23 chars)
   ```

4. **PTY range**
   ```yaml
   ✓ pty: 10
   ✗ pty: 50 (out of range)
   ```

5. **Language range**
   ```yaml
   ✓ language: 9
   ✗ language: 300 (out of range)
   ```

---

## Common Issues

### Duplicate service ID

**Error:**
```
ERROR: Duplicate service ID: 0x5001
```

**Solution:**
```yaml
services:
  - id: '0x5001'  # First service
  - id: '0x5002'  # Different ID
```

### Service not linked

**Warning:** Service defined but no component links it

**Solution:**
```yaml
services:
  - uid: 'my_service'
    id: '0x5001'

components:
  - service_id: '0x5001'  # Link service
    subchannel_id: 0
```

### Label too long

**Error:**
```
ERROR: Service label exceeds 16 characters
```

**Solution:**
```yaml
# Shorten the label
label:
  text: 'Short Name'  # 10 chars - OK
```

---

## Best Practices

### Descriptive UIDs

```yaml
# Good
uid: 'bbc_radio1'
uid: 'classical_fm'
uid: 'news_24_7'

# Avoid
uid: 'svc1'
uid: 'service_a'
```

### Sequential IDs

```yaml
# Organized by number
services:
  - id: '0x5001'
  - id: '0x5002'
  - id: '0x5003'
```

### Always Set PTY and Language

```yaml
services:
  - label:
      text: 'My Station'
    pty: 10       # Always specify
    language: 9   # Always specify
```

### Meaningful Short Labels

```yaml
# Good abbreviations
text: 'BBC Radio 1'
short: 'BBC R1'

text: 'Classical Music FM'
short: 'ClassicFM'

# Avoid
text: 'BBC Radio 1'
short: 'BBC Radi'  # Auto-truncated, not ideal
```

---

## See Also

- [Ensemble Parameters](ensemble.md): Top-level configuration
- [Subchannels](subchannels.md): Audio stream configuration
- [Configuration Hierarchy](../../architecture/configuration-hierarchy.md): How services link to subchannels
- [Examples](examples.md): Complete working configurations
