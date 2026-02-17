# Reed-Solomon Forward Error Correction

Reed-Solomon FEC implementation for PFT packet recovery in EDI protocol.

## Overview

Reed-Solomon (RS) codes are error-correcting codes used in PFT (Protection, Fragmentation and Transport) to recover lost UDP packets in EDI transmission.

**Key benefits:**
- Recover lost packets without retransmission
- Protect against network packet loss
- Essential for unreliable networks (wireless, Internet)

## Reed-Solomon Basics

### What is Reed-Solomon?

A mathematical error correction code that adds redundancy to data:

```
Original data:  k packets
Redundancy:     m packets (FEC)
Total sent:     n = k + m packets

Can recover up to m lost packets
```

### Galois Field Math

Reed-Solomon operates in **GF(2^8)** - Galois Field with 256 elements:
- Each element is a byte (0-255)
- Special arithmetic rules (finite field)
- Uses polynomial mathematics

**Note:** Implementation details are in `dabmux/fec/reed_solomon.py`

## PFT Reed-Solomon Configuration

### Parameters

python-dabmux uses **RS(255, 207)** with zero-padding:

| Parameter | Value | Description |
|-----------|-------|-------------|
| **n** | 255 | Total symbols (max for GF(2^8)) |
| **k** | 207 | Data symbols |
| **m** | 48 | FEC symbols (n - k) |
| **Max errors** | 24 | Can correct up to m/2 errors |

**For PFT:**
- Not all 255 positions used (packets may be fewer)
- FEC parameter `m` sets number of recoverable fragments
- Typical: m=2 to m=5

## PFT Configuration

### Module: `dabmux.edi.pft`

```python
from dabmux.edi.pft import PFTConfig

# No FEC (fragmentation only)
pft_config = PFTConfig(
    fec=False,
    fec_m=0,
    max_fragment_size=1400
)

# With FEC (can recover 2 lost fragments)
pft_config = PFTConfig(
    fec=True,
    fec_m=2,
    max_fragment_size=1400
)

# Strong FEC (can recover 5 lost fragments)
pft_config = PFTConfig(
    fec=True,
    fec_m=5,
    max_fragment_size=1400
)
```

### CLI Usage

```bash
# EDI with PFT + FEC (m=2)
python -m dabmux.cli -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec \
  --pft-fec-m 2

# Strong FEC (m=5)
python -m dabmux.cli -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec \
  --pft-fec-m 5
```

## How It Works

### Encoding Process

1. **Fragment data** into k packets
2. **Add m FEC packets** using RS encoding
3. **Send all k + m packets** over network

```
Original ETI data (6144 bytes)
          ↓
    Fragmentation
          ↓
┌─────────────────────────────┐
│ Frag 0 │ Frag 1 │ ... │ Frag k-1 │  (k data fragments)
└─────────────────────────────┘
          ↓
   Reed-Solomon Encoding
          ↓
┌─────────────────────────────────────────┐
│ Frag 0 │ ... │ Frag k-1 │ FEC 0 │ ... │ FEC m-1 │  (k+m total)
└─────────────────────────────────────────┘
          ↓
   Transmit all k+m packets
```

### Decoding Process

1. **Receive packets** (some may be lost)
2. **Check if k packets received**
3. **If yes**: Reassemble data
4. **If no but ≥k total**: Use RS decoding to recover

```
Transmitted: 10 data + 2 FEC = 12 packets
Received:    8 data + 2 FEC = 10 packets (2 lost)
              ↓
      Reed-Solomon Decoding
              ↓
      Recover 2 lost packets
              ↓
      Full data restored!
```

**Condition:** Can recover if **(received packets) ≥ k**

## Example Scenarios

### Scenario 1: No Packet Loss

```
Sent:     10 data + 2 FEC = 12 packets
Received: 10 data + 2 FEC = 12 packets
Result:   ✅ Use data packets directly (no FEC needed)
```

### Scenario 2: 1 Packet Lost (Recoverable)

```
Sent:     10 data + 2 FEC = 12 packets
Received: 9 data + 2 FEC = 11 packets (1 data lost)
Result:   ✅ RS decodes, recovers 1 lost packet
```

### Scenario 3: 2 Packets Lost (Recoverable)

```
Sent:     10 data + 2 FEC = 12 packets
Received: 8 data + 2 FEC = 10 packets (2 data lost)
Result:   ✅ RS decodes, recovers 2 lost packets
```

### Scenario 4: 3 Packets Lost (Not Recoverable)

```
Sent:     10 data + 2 FEC = 12 packets
Received: 7 data + 2 FEC = 9 packets (3 lost)
Result:   ❌ Cannot recover (m=2, but 3 lost)
```

**Rule:** Can recover up to **m** lost packets.

## Choosing FEC Parameter (m)

### Trade-offs

| m | Recovery | Overhead | Bandwidth | Use Case |
|---|----------|----------|-----------|----------|
| 0 | None | 0% | 1.0× | Reliable network |
| 2 | 2 packets | ~20% | 1.2× | Occasional loss |
| 3 | 3 packets | ~30% | 1.3× | Moderate loss |
| 5 | 5 packets | ~50% | 1.5× | Lossy network |

### Recommendations

**m=0 (No FEC):**
- Wired networks
- Local/LAN
- Very reliable connections

**m=2 (Light FEC):**
- Good quality networks
- Occasional packet loss (<2%)
- Standard recommendation

**m=3 (Moderate FEC):**
- Moderate packet loss (2-5%)
- Wireless links
- Balanced protection

**m=5 (Strong FEC):**
- High packet loss (5-10%)
- Unreliable networks
- Internet transmission

**m>5:**
- Extreme conditions (>10% loss)
- Diminishing returns
- High bandwidth cost

## Bandwidth Calculation

### Formula

```
Overhead = m / k
Bandwidth_multiplier = (k + m) / k = 1 + (m / k)
```

### Examples

**Typical scenario (m=2, k=10):**
```
Overhead: 2/10 = 20%
Bandwidth: 1.2× base bandwidth
```

**Strong FEC (m=5, k=10):**
```
Overhead: 5/10 = 50%
Bandwidth: 1.5× base bandwidth
```

**ETI transmission (Mode I):**
```
Base ETI: ~590 kbps (without PFT)
With PFT (m=2): ~590 × 1.2 = 708 kbps
With PFT (m=5): ~590 × 1.5 = 885 kbps
```

## Python API

### Module: `dabmux.fec.reed_solomon`

```python
from dabmux.fec.reed_solomon import ReedSolomonEncoder, ReedSolomonDecoder

# Create encoder
encoder = ReedSolomonEncoder(fec_symbols=2)

# Original data (k packets)
data_packets = [b'packet1', b'packet2', ..., b'packetk']

# Encode (generates m FEC packets)
fec_packets = encoder.encode(data_packets)

# Total packets to transmit
all_packets = data_packets + fec_packets

# --- Network transmission ---

# Receiver side (some packets may be lost)
received_packets = [...]  # Some packets missing

# Create decoder
decoder = ReedSolomonDecoder(fec_symbols=2)

# Decode (recovers lost packets)
try:
    recovered_data = decoder.decode(received_packets)
    print("Data recovered successfully!")
except ValueError as e:
    print(f"Cannot recover: {e}")
```

### Encoder Class

#### `ReedSolomonEncoder(fec_symbols: int)`

Create Reed-Solomon encoder.

**Parameters:**
- `fec_symbols: int` - Number of FEC symbols (m)

**Methods:**

##### `encode(data: list[bytes]) -> list[bytes]`

Generate FEC packets.

**Parameters:**
- `data: list[bytes]` - Data packets (k packets)

**Returns:** FEC packets (m packets)

### Decoder Class

#### `ReedSolomonDecoder(fec_symbols: int)`

Create Reed-Solomon decoder.

**Parameters:**
- `fec_symbols: int` - Number of FEC symbols (m)

**Methods:**

##### `decode(packets: list[bytes], positions: list[int]) -> list[bytes]`

Recover lost packets.

**Parameters:**
- `packets: list[bytes]` - Received packets (data + FEC)
- `positions: list[int]` - Position indices of received packets

**Returns:** Complete data (all k packets)

**Raises:**
- `ValueError` - If recovery impossible (too many lost)

## Performance

### Encoding Performance

- **Time complexity**: O(k × m)
- **Typical encoding time**: <1ms for ETI frame
- **CPU usage**: Minimal (<5% overhead)

### Decoding Performance

- **Time complexity**: O(k × m)
- **Typical decoding time**: <2ms for ETI frame
- **Only needed when packets lost**

### Memory Usage

- **Encoder**: ~k × packet_size
- **Decoder**: ~(k+m) × packet_size
- **Typical**: <100 KB per ETI frame

## Real-World Example

### Network Statistics

Network with 2% packet loss:

```
Frames sent:     10,000
Packets per frame: 10 + 2 FEC = 12
Total packets:   120,000
Packets lost:    2,400 (2%)

Without FEC (m=0):
  Frames with loss: ~1,814 (18%)
  Frames unrecoverable: ~1,814 (18%)
  Success rate: 82%

With FEC (m=2):
  Frames with ≤2 lost: ~1,752 (17.5%)
  Frames with >2 lost: ~62 (0.6%)
  Success rate: 99.4%
```

**FEC effectiveness:** 82% → 99.4% success rate!

## Troubleshooting

### FEC Not Working

**Problem:** Packets still lost despite FEC

**Check:**
1. **Packet loss > m?** Increase m value
2. **Fragment size too large?** Reduce `max_fragment_size`
3. **Network unreliable?** Use TCP instead of UDP
4. **Corrupt packets?** RS can't fix corruption, only loss

### High Bandwidth Usage

**Problem:** Too much network traffic

**Solution:**
1. Reduce m value (less FEC)
2. Increase fragment size (fewer packets)
3. Reduce bitrate (lower quality)
4. Use DAB+ instead of DAB (more efficient codec)

### Decoder Errors

**Problem:** `ValueError: Cannot recover`

**Cause:** Too many packets lost (>m)

**Solution:**
1. Increase m value
2. Improve network quality
3. Use TCP for reliability

## Mathematical Details

### Generator Polynomial

Reed-Solomon uses primitive polynomial:
```
g(x) = (x - α^0)(x - α^1)...(x - α^(m-1))
```

Where α is a primitive element of GF(2^8).

### Encoding Equation

```
c(x) = m(x) · x^m + r(x)
```

Where:
- m(x) = message polynomial
- r(x) = remainder from division by g(x)
- c(x) = codeword polynomial

**Implementation:** See `dabmux/fec/reed_solomon.py`

## See Also

- [PFT Fragmentation](../user-guide/outputs/pft-fragmentation.md) - PFT overview
- [EDI Protocol](../architecture/edi-protocol.md) - EDI with PFT/FEC
- [Output API](../api-reference/output.md) - EDI output configuration
- [Network Streaming Tutorial](../tutorials/network-streaming.md) - Practical examples

## References

- **Reed-Solomon codes** - [Wikipedia](https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction)
- **ETSI TS 102 693** - EDI specification with RS-FEC
- **Galois Field arithmetic** - Finite field mathematics
