# Timestamps & Synchronization

TIST (Timestamp) implementation for Single Frequency Networks and synchronized transmission.

## Overview

TIST (Time-Stamp) is an optional 4-byte field in ETI frames that enables precise timing for:
- **Single Frequency Networks (SFN)** - Multiple transmitters on same frequency
- **Synchronized transmission** - Coordinated multi-site broadcasting
- **Time-aligned recording** - Frame-accurate archives

## TIST Structure

### Binary Format

```
32-bit timestamp (little-endian)
────────────────────────────────
│  TIST (4 bytes)              │
│  Time in 16.384 MHz ticks    │
└──────────────────────────────┘
```

### Clock Rate

TIST uses **16.384 MHz clock** (16,384,000 ticks per second):
- 1 tick = 61.035 nanoseconds
- 1 millisecond = 16,384 ticks
- 1 second = 16,384,000 ticks

### Value Range

- **32-bit unsigned integer**: 0 to 4,294,967,295
- **Time range**: ~262 seconds (~4.4 minutes)
- **Wraps around**: After ~262 seconds, value resets to 0

## Enabling TIST

### Configuration

```yaml
ensemble:
  id: '0xCE15'
  transmission_mode: 'I'
  label:
    text: 'SFN Network'

  # Enable TIST
  enable_tist: true
  tist_offset: 0.0  # Offset in milliseconds (optional)
```

### CLI

```bash
# Enable TIST in output
python -m dabmux.cli -c config.yaml -o output.eti --tist

# With offset (e.g., 100ms delay)
python -m dabmux.cli -c config.yaml -o output.eti --tist --tist-offset 100.0
```

### Python API

```python
from dabmux.config import load_config
from dabmux.mux import DabMultiplexer

# Load configuration with TIST enabled
ensemble = load_config('config.yaml')
ensemble.enable_tist = True
ensemble.tist_offset = 0.0  # milliseconds

# Create multiplexer
mux = DabMultiplexer(ensemble)

# Generate frame (TIST automatically added)
frame = mux.generate_frame()
assert frame.tist is not None

# Frame size includes TIST
assert len(frame.pack()) == 6148  # 6144 + 4 for TIST
```

## TIST Calculation

### From System Time

```python
from dabmux.core.eti import EtiTIST
from datetime import datetime

# Get current time
now = datetime.now()

# Convert to TIST
tist = EtiTIST.from_datetime(now)

# Get TIST value (16.384 MHz ticks)
ticks = tist.tist
print(f"TIST: {ticks} ticks")

# Convert back to seconds
seconds = ticks / 16_384_000.0
print(f"Time: {seconds:.6f} seconds")
```

### Manual Calculation

```python
import time

# Get Unix timestamp
unix_time = time.time()

# Calculate ticks since midnight UTC
seconds_since_midnight = unix_time % 86400  # Seconds in a day
ticks = int(seconds_since_midnight * 16_384_000) & 0xFFFFFFFF

# Create TIST
from dabmux.core.eti import EtiTIST
tist = EtiTIST(tist=ticks)
```

## TIST Offset

### Purpose

TIST offset compensates for:
- Processing delays
- Network latency
- Modulator delays
- Transmitter delays

### Application

```yaml
ensemble:
  enable_tist: true
  tist_offset: 200.0  # Add 200ms to all timestamps
```

**Effect:**
```
Base TIST:     1000000 ticks (at generation)
Offset:        + 200ms = +3,276,800 ticks
Final TIST:    4,276,800 ticks
```

### Use Cases

**Compensate for modulator delay:**
```yaml
# Modulator adds 150ms processing delay
tist_offset: 150.0
```

**Align multiple multiplexers:**
```yaml
# Site A (reference)
tist_offset: 0.0

# Site B (50ms behind)
tist_offset: 50.0

# Site C (100ms ahead)
tist_offset: -100.0
```

## Single Frequency Networks (SFN)

### Concept

Multiple transmitters broadcast the same signal on the same frequency. Receivers see constructive interference if transmitters are synchronized.

```
Transmitter A ───┐
                 ├──> Same frequency (e.g., 225.648 MHz)
Transmitter B ───┤    Same content
                 │    Synchronized timing via TIST
Transmitter C ───┘
```

### Requirements

1. **Same ETI stream** - All transmitters use identical frames
2. **Synchronized TIST** - All frames have matching timestamps
3. **GPS-locked clocks** - Transmitters locked to GPS time
4. **Propagation delay compensation** - Account for distance between transmitters

### Timing Tolerance

- **Maximum offset**: ±25 μs (Mode I)
- **GPS accuracy**: ~100 ns
- **Typical SFN accuracy**: ±1 μs

### Configuration Example

```yaml
# Master multiplexer
ensemble:
  enable_tist: true
  tist_offset: 0.0

# Distribute ETI to all transmitters via EDI
```

## Frame Timing

### Mode I Timing

```
Frame duration: 96 ms
TIST increment: ~1,572,864 ticks per frame

Frame N:   TIST = 0
Frame N+1: TIST = 1,572,864
Frame N+2: TIST = 3,145,728
...
```

### Mode II Timing

```
Frame duration: 24 ms
TIST increment: ~393,216 ticks per frame

Frame N:   TIST = 0
Frame N+1: TIST = 393,216
Frame N+2: TIST = 786,432
...
```

### Calculating Frame Time

```python
def ticks_per_frame(mode: int) -> int:
    """Calculate TIST increment per frame."""
    frame_duration_ms = {
        1: 96,   # Mode I
        2: 24,   # Mode II
        3: 24,   # Mode III
        4: 96    # Mode IV
    }[mode]

    # Convert milliseconds to ticks
    return int(frame_duration_ms * 16_384)

# Example: Mode I
ticks = ticks_per_frame(1)
print(f"Mode I: {ticks} ticks per frame")  # 1,572,864
```

## Reading TIST from ETI

### Parse ETI Frame

```python
from dabmux.core.eti import EtiFrame, EtiTIST

# Read ETI frame from file
with open('input.eti', 'rb') as f:
    frame_data = f.read(6148)  # 6144 + 4 for TIST

# Check if TIST is present (frame must be 6148 bytes)
has_tist = len(frame_data) == 6148

if has_tist:
    # Extract TIST (last 4 bytes)
    tist_bytes = frame_data[-4:]
    tist = EtiTIST.unpack(tist_bytes)

    print(f"TIST: {tist.tist} ticks")

    # Convert to seconds
    seconds = tist.tist / 16_384_000.0
    print(f"Time: {seconds:.6f} seconds")
```

## TIST in EDI

When transmitting ETI over EDI (Ensemble Data Interface), TIST is included in the `estN` TAG item:

```
EDI Packet:
  *ptr TAG (protocol)
  deti TAG (ETI data)
  estN TAG (timestamp) ← TIST value here
```

**Note:** EDI automatically handles TIST when present in ETI frames.

## Synchronization Example

### Multi-Site Setup

```python
from dabmux.mux import DabMultiplexer
from dabmux.output.edi import EdiOutput
from dabmux.edi.pft import PFTConfig
import time

# Configuration with TIST
ensemble.enable_tist = True
ensemble.tist_offset = 0.0

# Create multiplexer
mux = DabMultiplexer(ensemble)

# Create EDI outputs for multiple transmitters
sites = [
    ('239.1.2.3', 12000),  # Site A
    ('239.1.2.4', 12000),  # Site B
    ('239.1.2.5', 12000),  # Site C
]

outputs = []
for addr, port in sites:
    output = EdiOutput(addr, port, enable_pft=True,
                      pft_config=PFTConfig(fec=True, fec_m=2))
    output.open()
    outputs.append(output)

# Generate and distribute frames
try:
    while True:
        frame = mux.generate_frame()

        # Send to all sites simultaneously
        for output in outputs:
            output.write_frame(frame)

        # Wait for next frame time (96ms for Mode I)
        time.sleep(0.096)

finally:
    for output in outputs:
        output.close()
```

## TIST Validation

### Check TIST Consistency

```python
def validate_tist_sequence(frames):
    """Validate TIST increments correctly."""
    expected_increment = 1_572_864  # Mode I

    for i in range(1, len(frames)):
        prev_tist = frames[i-1].tist.tist
        curr_tist = frames[i].tist.tist

        # Handle wrap-around
        if curr_tist < prev_tist:
            curr_tist += 2**32

        increment = curr_tist - prev_tist

        if abs(increment - expected_increment) > 100:
            print(f"Frame {i}: TIST jump detected")
            print(f"  Expected: {expected_increment}")
            print(f"  Actual:   {increment}")
```

## Performance Considerations

### TIST Generation Overhead

- **Minimal overhead**: <0.1ms per frame
- **System time call**: Once per frame
- **Clock accuracy**: Depends on system clock quality

### GPS Synchronization

For production SFN:
1. **Use GPS-disciplined clock** on multiplexer host
2. **NTP not sufficient** - Use GPS or PTP for sub-microsecond accuracy
3. **Monitor clock drift** - Log TIST consistency

## Troubleshooting

### TIST Not Present

**Problem:** ETI frames are 6144 bytes (no TIST)

**Solution:**
```yaml
ensemble:
  enable_tist: true  # Add this
```

### TIST Values Not Incrementing

**Problem:** TIST same across frames

**Cause:** System time not advancing or TIST calculation issue

**Check:**
```python
import time
start = time.time()
time.sleep(0.1)
end = time.time()
assert end > start, "System time not advancing"
```

### SFN Synchronization Issues

**Problem:** Multiple transmitters not synchronized

**Checklist:**
- ☑ All transmitters using same ETI stream?
- ☑ All transmitters GPS-locked?
- ☑ TIST offsets configured correctly?
- ☑ Network latency stable?
- ☑ Propagation delays compensated?

## See Also

- [Architecture: ETI Frames](../architecture/eti-frames.md) - TIST field details
- [EDI Protocol](../architecture/edi-protocol.md) - TIST in network transmission
- [Output API](../api-reference/output.md) - EDI output configuration
- [ETSI EN 300 799](../standards/index.md) - Official TIST specification
