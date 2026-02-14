# Protection Levels

Complete guide to DAB error protection configuration and UEP (Unequal Error Protection).

## Overview

DAB uses **UEP (Unequal Error Protection)** to protect audio data from transmission errors. Protection adds redundancy but increases capacity usage.

**Key concepts:**
- Higher protection = more robust but more capacity used
- Protection level: 0 (weakest) to 4 (strongest)
- Two forms: Short form and Long form

## Protection Configuration

```yaml
subchannels:
  - protection:
      level: 2          # Protection level (0-4)
      shortform: true   # Use short form table
```

---

## Protection Levels

### Level 0 - Weakest Protection

**Use when:**
- Very strong signal
- Controlled environment
- Maximum bitrate needed

**Characteristics:**
- Minimal overhead
- Least robust
- Highest useful bitrate

**Example:**
```yaml
protection:
  level: 0
```

**Typical scenario:** Indoor/cable distribution, very strong signal

---

### Level 1 - Weak Protection

**Use when:**
- Strong signal
- Good reception area
- Some error tolerance acceptable

**Characteristics:**
- Low overhead
- Basic error correction
- High useful bitrate

**Example:**
```yaml
protection:
  level: 1
```

**Typical scenario:** Good coverage area, wired distribution

---

### Level 2 - Moderate Protection (Default)

**Use when:**
- Normal operating conditions
- General broadcast
- Standard signal strength

**Characteristics:**
- Balanced overhead/protection
- Good error correction
- Standard bitrate

**Example:**
```yaml
protection:
  level: 2  # Default and recommended
```

**Typical scenario:** Standard terrestrial broadcasting, most use cases

**Recommendation:** Use level 2 for most services.

---

### Level 3 - Strong Protection

**Use when:**
- Weak signal areas
- Edge of coverage
- Premium/important content

**Characteristics:**
- Higher overhead
- Strong error correction
- Lower useful bitrate

**Example:**
```yaml
protection:
  level: 3
```

**Typical scenario:** Weak signal areas, fringe coverage, mobile reception

---

### Level 4 - Strongest Protection

**Use when:**
- Very weak signals
- Critical data services
- Maximum robustness needed

**Characteristics:**
- Highest overhead
- Maximum error correction
- Lowest useful bitrate

**Example:**
```yaml
protection:
  level: 4
```

**Typical scenario:** Emergency broadcasts, data services, extreme conditions

---

## Short Form vs Long Form

### Short Form (Recommended)

**Use:** `shortform: true`

**Characteristics:**
- Simpler protection scheme
- Standard protection tables
- Widely supported
- Easier to configure

**Example:**
```yaml
protection:
  level: 2
  shortform: true  # Recommended
```

**Recommendation:** Use short form unless you have specific requirements.

### Long Form

**Use:** `shortform: false`

**Characteristics:**
- More flexible protection
- Custom protection tables
- Advanced use cases
- More complex

**Example:**
```yaml
protection:
  level: 2
  shortform: false
```

**Use cases:** Specialized applications, custom protection profiles

---

## Capacity Impact

Protection level affects Capacity Unit (CU) usage.

### Example: 128 kbps Audio (Mode I)

| Protection | CUs Used | Overhead | Useful Data |
|------------|----------|----------|-------------|
| Level 0 | ~70 | Lowest | Maximum |
| Level 1 | ~75 | Low | High |
| Level 2 | ~84 | Medium | Standard |
| Level 3 | ~95 | High | Lower |
| Level 4 | ~110 | Highest | Lowest |

**Trade-off:** Higher protection = fewer services fit in ensemble

### Capacity Calculation Example

**Mode I total capacity:** 864 CU

**Scenario 1: Level 2 protection (84 CU per 128 kbps service)**
- Max services: 864 / 84 ≈ 10 services

**Scenario 2: Level 3 protection (95 CU per 128 kbps service)**
- Max services: 864 / 95 ≈ 9 services

**Impact:** Higher protection = fewer services possible

---

## Choosing Protection Level

### Decision Matrix

| Scenario | Recommended Level | Reasoning |
|----------|------------------|-----------|
| Indoor/cable | 0-1 | Strong signal, controlled |
| Urban coverage | 2 | Standard conditions |
| Suburban | 2-3 | Variable signal |
| Rural/edge | 3-4 | Weak signal |
| Mobile reception | 3 | Variable conditions |
| Data services | 3-4 | Less tolerance for errors |
| Emergency | 4 | Maximum reliability |

### Signal Strength Guidelines

**Strong signal (>80 dB\u00b5V):**
- Level 1-2
- Indoor/local transmitters
- Cable distribution

**Medium signal (60-80 dB\u00b5V):**
- Level 2 (default)
- Most broadcast scenarios
- Standard coverage

**Weak signal (40-60 dB\u00b5V):**
- Level 3
- Edge of coverage
- Obstructed areas

**Very weak signal (<40 dB\u00b5V):**
- Level 4
- Fringe reception
- Maximum reach

---

## Examples by Content Type

### Music Service (High Quality)

```yaml
subchannels:
  - uid: 'music_premium'
    type: 'audio'
    bitrate: 192
    protection:
      level: 3  # Strong protection for premium content
      shortform: true
```

**Reasoning:** High-quality music deserves robust protection.

### News Service (Speech)

```yaml
subchannels:
  - uid: 'news_service'
    type: 'dabplus'
    bitrate: 48
    protection:
      level: 2  # Standard protection
      shortform: true
```

**Reasoning:** Speech is more tolerant of errors than music.

### Data Service

```yaml
subchannels:
  - uid: 'data_service'
    type: 'packet'
    bitrate: 32
    protection:
      level: 4  # Maximum protection for data
      shortform: true
```

**Reasoning:** Data requires error-free transmission.

### Indoor Transmitter

```yaml
subchannels:
  - uid: 'indoor_service'
    type: 'audio'
    bitrate: 128
    protection:
      level: 1  # Light protection, strong signal
      shortform: true
```

**Reasoning:** Controlled environment, strong signal.

---

## Protection and Bitrate Combinations

### Recommended Combinations

**DAB (MPEG Layer II):**

| Bitrate | Normal Use | Weak Signal |
|---------|------------|-------------|
| 128 kbps | Level 2 | Level 3 |
| 160 kbps | Level 2 | Level 3 |
| 192 kbps | Level 2-3 | Level 3-4 |

**DAB+ (HE-AAC v2):**

| Bitrate | Normal Use | Weak Signal |
|---------|------------|-------------|
| 48 kbps | Level 2 | Level 3 |
| 64 kbps | Level 2 | Level 3 |
| 72 kbps | Level 2 | Level 2-3 |
| 96 kbps | Level 2-3 | Level 3 |

---

## Multi-Service Configuration

Balance protection across services:

```yaml
subchannels:
  # Premium music - higher protection
  - uid: 'music_premium'
    bitrate: 192
    protection:
      level: 3
      shortform: true

  # Standard music - normal protection
  - uid: 'music_standard'
    bitrate: 128
    protection:
      level: 2
      shortform: true

  # News - standard protection
  - uid: 'news'
    bitrate: 64
    protection:
      level: 2
      shortform: true

  # Data - maximum protection
  - uid: 'data'
    bitrate: 32
    protection:
      level: 4
      shortform: true
```

**Strategy:**
- Premium content: Higher protection
- Standard content: Level 2
- Data services: Maximum protection

---

## Testing Protection Levels

### Simulate Weak Signal

Test different protection levels:

```bash
# Level 2 (default)
python -m dabmux.cli -c config_level2.yaml -o output.eti

# Level 3 (stronger)
python -m dabmux.cli -c config_level3.yaml -o output.eti
```

Compare output quality in different conditions.

### Monitor Error Rates

In production, monitor:
- Bit error rate (BER)
- Frame error rate (FER)
- Audio quality metrics

Adjust protection based on observed errors.

---

## Common Issues

### Capacity exceeded

**Error:**
```
ERROR: Total capacity exceeds available CUs
```

**Solution:** Lower protection levels
```yaml
# From level 3
protection:
  level: 2  # Use level 2 instead
```

### Excessive errors

**Problem:** Audio dropouts, poor quality

**Solution:** Increase protection
```yaml
# From level 2
protection:
  level: 3  # Increase to level 3
```

### Wrong form selected

**Problem:** Receiver doesn't decode properly

**Solution:** Use short form (widely compatible)
```yaml
protection:
  shortform: true  # Use short form
```

---

## Best Practices

### Start with Level 2

```yaml
protection:
  level: 2  # Default, suitable for most cases
  shortform: true
```

### Adjust Based on Testing

1. Start with level 2
2. Test in target area
3. Increase if errors observed
4. Decrease if capacity needed

### Use Short Form

```yaml
protection:
  shortform: true  # Recommended
```

Short form is simpler and widely supported.

### Match Protection to Content Importance

```yaml
# Critical service
protection:
  level: 3-4

# Standard service
protection:
  level: 2

# Low priority
protection:
  level: 1-2
```

---

## Summary

**Protection levels:**
- 0: Weakest (strong signal only)
- 1: Weak (good signal)
- 2: Moderate (default, recommended)
- 3: Strong (weak signal)
- 4: Strongest (maximum robustness)

**Key points:**
- Higher protection = more robust but less capacity
- Level 2 suitable for most scenarios
- Adjust based on signal strength and content importance
- Use short form unless specific requirements

**Trade-off:**
```
More Protection ↔ More Services
    Level 4     ↔    Level 0
    Robust      ↔    Capacity
```

Choose based on your priorities!

---

## See Also

- [Subchannels](subchannels.md): Subchannel configuration
- [Capacity Management](../../architecture/data-flow.md): Understanding CU usage
- [Examples](examples.md): Complete configurations with protection
