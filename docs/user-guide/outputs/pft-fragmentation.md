# PFT Fragmentation and FEC

Complete guide to PFT (Protection, Fragmentation and Transport) with Reed-Solomon forward error correction.

## Overview

PFT adds fragmentation and forward error correction (FEC) to EDI streaming, enabling reliable transmission over lossy networks.

**Key features:**
- **Fragmentation:** Splits large packets into smaller fragments
- **FEC:** Reed-Solomon error correction codes
- **Sequence numbering:** Detects missing fragments
- **Reassembly:** Receiver reconstructs original packets

**Standard:** ETSI TS 102 821

---

## Why Use PFT?

### Problem: Packet Loss

**UDP has no delivery guarantee:**
- Network congestion → dropped packets
- Router buffers → packet loss
- Wireless links → interference
- Long-distance links → higher loss probability

**Impact on DAB:**
- Lost ETI data = audio dropouts
- Missing FIG data = service info gaps
- Single lost packet = corrupt frame

### Solution: PFT with FEC

**Reed-Solomon FEC:**
- Adds redundant data
- Can recover lost fragments
- No retransmission needed
- Bounded latency

**Example:**
- Send 10 fragments
- Add 3 FEC fragments
- Total: 13 fragments
- **Can lose any 3** and still recover original data

---

## Basic PFT Configuration

### Enable PFT

```bash
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft
```

**Default PFT settings:**
- Fragmentation: Enabled
- FEC: Disabled (must enable explicitly)
- Fragment size: 512 bytes

### Enable FEC

```bash
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 2 \
  --pft-fec-m 3
```

**Parameters:**
- `--pft-fec 2`: FEC depth (RS overhead)
- `--pft-fec-m 3`: Maximum correctable fragments

---

## FEC Parameters

### FEC Depth (`--pft-fec`)

**Range:** 0-20
**Default:** 0 (disabled)

**Meaning:** Number of additional FEC fragments per group

**Example:**
```bash
--pft-fec 3
```

If original data requires 10 fragments:
- Original: 10 fragments
- FEC: 3 fragments
- **Total sent:** 13 fragments
- **Overhead:** 30%

### Maximum Correctable (`--pft-fec-m`)

**Range:** 0-20 (must be ≤ FEC depth)
**Default:** 0

**Meaning:** Maximum number of fragment losses that can be corrected

**Example:**
```bash
--pft-fec 5 --pft-fec-m 5
```

- Can correct up to 5 lost fragments
- Requires 5 FEC fragments overhead
- 100% overhead if original = 5 fragments

### Relationship

**Rule:** `FEC-M ≤ FEC depth`

```
Can correct: min(FEC-M, number of FEC fragments)
```

**Examples:**

| Original | FEC Depth | FEC-M | Total Sent | Can Lose |
|----------|-----------|-------|------------|----------|
| 10 | 2 | 2 | 12 | Up to 2 |
| 10 | 3 | 3 | 13 | Up to 3 |
| 10 | 5 | 3 | 15 | Up to 3* |
| 10 | 3 | 5 | 13 | Up to 3* |

\* Limited by smaller value

---

## Reed-Solomon FEC

### How It Works

**Reed-Solomon codes:**
1. Takes N data symbols
2. Generates K parity symbols
3. Total: N + K symbols
4. Can recover original from any N symbols
5. Tolerates up to K losses

**In PFT context:**
- **N** = Original fragments
- **K** = FEC depth
- **M** = Maximum corrections (≤ K)

### Mathematics

**Galois Field GF(256):**
- Operations on 8-bit symbols
- Polynomial arithmetic
- Generator polynomial creates parity

**Encoding:**
```
For message M with n fragments:
1. Compute k FEC fragments
2. Send all n + k fragments
3. Any n fragments sufficient to decode
```

**Decoding:**
```
Receiver needs n fragments:
1. Collect fragments (any n of n+k)
2. Identify which are missing
3. Use FEC to reconstruct
4. Recover original message M
```

See [Advanced: Reed-Solomon](../../advanced/reed-solomon.md) for mathematical details.

---

## Fragment Size

### Configure Fragment Size

```bash
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fragment-size 1024
```

**Default:** 512 bytes
**Range:** 64 - 1400 bytes

### Choosing Fragment Size

**Smaller fragments (256-512):**
- ✅ Less data lost per packet
- ✅ Fits in most networks (MTU)
- ✅ Better for high-loss networks
- ❌ More fragments = more overhead
- ❌ Higher packet rate

**Larger fragments (1024-1400):**
- ✅ Fewer fragments needed
- ✅ Lower overhead
- ✅ Lower packet rate
- ❌ More data lost per packet
- ❌ May exceed MTU

**Recommended:** 512-1024 bytes

**MTU consideration:**
```
Fragment size + UDP header + IP header ≤ MTU

Typical MTU: 1500 bytes
UDP header: 8 bytes
IP header: 20 bytes
Safe maximum: 1472 bytes

Recommended: 1024 bytes (safe margin)
```

---

## Bandwidth and Overhead

### Calculate Overhead

**Formula:**
```
Overhead = (FEC_depth / Original_fragments) × 100%
```

**Examples:**

| Original | FEC | Overhead |
|----------|-----|----------|
| 10 | 2 | 20% |
| 10 | 3 | 30% |
| 10 | 5 | 50% |
| 12 | 3 | 25% |

### Total Bandwidth

**Formula:**
```
Total bandwidth = ETI bandwidth × (1 + Overhead)
```

**Mode I example:**
- ETI: ~590 kbps (including EDI overhead)
- FEC depth 3 (30% overhead)
- **Total: 590 × 1.30 = 767 kbps**

### Bandwidth Table

| Mode | Base | FEC 2 (20%) | FEC 3 (30%) | FEC 5 (50%) |
|------|------|-------------|-------------|-------------|
| I | 590 kbps | 708 kbps | 767 kbps | 885 kbps |
| II | 148 kbps | 178 kbps | 192 kbps | 222 kbps |
| IV | 295 kbps | 354 kbps | 384 kbps | 443 kbps |

---

## Latency

### Fragmentation Latency

**Sender:**
1. Wait for complete AF packet
2. Fragment into pieces
3. Calculate FEC
4. Send fragments

**Additional delay:** ~1-2 frame durations

### Receiver Reassembly

**Receiver:**
1. Collect all fragments
2. Perform FEC decoding if needed
3. Reconstruct packet
4. Deliver to application

**Additional delay:** ~1 frame duration

### Total PFT Latency

**Without PFT:** 1-10ms
**With PFT:** 10-30ms additional

**Total UDP + PFT:** ~20-40ms

**Acceptable for:**
- Live broadcasting (not critical)
- Studio-to-transmitter links

**Not suitable for:**
- Interactive applications
- Ultra-low-latency required

---

## Configuration Examples

### Low Loss Network (< 0.5%)

```bash
# Minimal FEC for occasional losses
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 2 \
  --pft-fec-m 2 \
  --pft-fragment-size 1024
```

**Settings:**
- FEC depth: 2 (20% overhead)
- Max corrections: 2
- Fragment size: 1024 bytes

**Protection:** Corrects up to 2 lost fragments per group

### Medium Loss Network (0.5-2%)

```bash
# Moderate FEC for typical networks
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 3 \
  --pft-fec-m 3 \
  --pft-fragment-size 512
```

**Settings:**
- FEC depth: 3 (30% overhead)
- Max corrections: 3
- Fragment size: 512 bytes

**Protection:** Corrects up to 3 lost fragments per group

### High Loss Network (2-5%)

```bash
# Strong FEC for challenging networks
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 5 \
  --pft-fec-m 5 \
  --pft-fragment-size 512
```

**Settings:**
- FEC depth: 5 (50% overhead)
- Max corrections: 5
- Fragment size: 512 bytes

**Protection:** Corrects up to 5 lost fragments per group

### Maximum Protection

```bash
# Highest FEC for extreme conditions
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 10 \
  --pft-fec-m 10 \
  --pft-fragment-size 512
```

**Settings:**
- FEC depth: 10 (100%+ overhead)
- Max corrections: 10
- Fragment size: 512 bytes

**Protection:** Corrects up to 10 lost fragments per group

**Use only when:** Network has 5-10% packet loss

---

## Testing PFT

### Simulate Packet Loss

**Using netem (Linux):**
```bash
# Add 2% packet loss
sudo tc qdisc add dev eth0 root netem loss 2%

# Test streaming with loss
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 3 \
  --pft-fec-m 3 \
  -v

# Remove packet loss
sudo tc qdisc del dev eth0 root
```

### Monitor FEC Performance

**Verbose output shows:**
```
INFO: PFT: 1000 packets sent
INFO: PFT: 100 fragments total
INFO: PFT: 30 FEC fragments (30% overhead)
INFO: PFT: 0 reconstruction errors
```

### Measure Effectiveness

**Without FEC:**
```bash
# Test without FEC
sudo tc qdisc add dev eth0 root netem loss 2%
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --continuous

# Expect errors at receiver
```

**With FEC:**
```bash
# Test with FEC
sudo tc qdisc add dev eth0 root netem loss 2%
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 3 \
  --pft-fec-m 3 \
  --continuous

# Should have zero errors (FEC recovers)
```

---

## Production Recommendations

### FEC Settings by Network Quality

| Packet Loss | FEC Depth | FEC-M | Fragment Size |
|-------------|-----------|-------|---------------|
| < 0.1% | 0 (off) | 0 | 1024 |
| 0.1-0.5% | 2 | 2 | 1024 |
| 0.5-1% | 2 | 2 | 512 |
| 1-2% | 3 | 3 | 512 |
| 2-5% | 5 | 5 | 512 |
| 5-10% | 10 | 10 | 512 |
| > 10% | Fix network! | | |

### Tuning Process

1. **Measure packet loss:**
   ```bash
   # Use iperf3 to measure loss
   iperf3 -c 192.168.1.100 -u -b 1M -l 1024 -t 60
   ```

2. **Start conservative:**
   ```bash
   --pft-fec 2 --pft-fec-m 2
   ```

3. **Monitor receiver:** Check for FEC corrections and errors

4. **Increase if needed:**
   ```bash
   --pft-fec 3 --pft-fec-m 3
   ```

5. **Verify bandwidth:** Ensure total bandwidth < link capacity

### Don't Over-Provision

**Too much FEC:**
- ❌ Wastes bandwidth
- ❌ Increases latency
- ❌ No additional benefit
- ❌ May cause congestion

**Right-sizing:**
- ✅ Just enough to handle typical losses
- ✅ Monitor and adjust based on real data
- ✅ Leave 20% bandwidth margin

---

## Troubleshooting

### FEC Not Correcting Losses

**Problem:** Still seeing errors despite FEC

**Diagnosis:**
```bash
# Check if loss exceeds FEC capability
# Example: 5% loss with FEC depth 3

# Test current loss rate
iperf3 -c 192.168.1.100 -u -b 1M -t 60
```

**Solutions:**
1. **Increase FEC depth:**
   ```bash
   --pft-fec 5 --pft-fec-m 5
   ```

2. **Reduce fragment size:** More fragments = better loss distribution
   ```bash
   --pft-fragment-size 512
   ```

3. **Fix network:** If loss > 5%, improve network infrastructure

### High Overhead/Bandwidth

**Problem:** Excessive bandwidth usage

**Check:**
```bash
# Monitor actual bandwidth
iftop -i eth0
# or
nload eth0
```

**Solutions:**
1. **Reduce FEC if network improved:**
   ```bash
   --pft-fec 2 --pft-fec-m 2  # from 5
   ```

2. **Increase fragment size:**
   ```bash
   --pft-fragment-size 1024  # from 512
   ```

3. **Disable FEC if network excellent:**
   ```bash
   --pft  # No --pft-fec flags
   ```

### Increased Latency

**Problem:** Unacceptable delay with PFT

**Measure latency:**
```bash
ping 192.168.1.100
```

**Solutions:**
1. **Reduce FEC depth:** Less processing time
2. **Optimize network:** Reduce hops, congestion
3. **Consider TCP:** If latency already high, TCP may be better
4. **Disable PFT:** If network is reliable enough

---

## Best Practices

### Configuration

1. **Match network conditions:** Measure loss, set FEC accordingly
2. **Conservative start:** Begin with FEC 2-3, increase if needed
3. **Monitor performance:** Watch for corrections and errors
4. **Document settings:** Keep record of what works
5. **Test before production:** Simulate losses, verify recovery

### Monitoring

1. **Track packet loss:** Use iperf3, network monitoring tools
2. **Log FEC statistics:** Enable verbose logging
3. **Alert on errors:** Set up notifications for unrecoverable errors
4. **Bandwidth monitoring:** Ensure sufficient capacity
5. **Latency monitoring:** Track end-to-end delay

### Optimization

1. **Right-size FEC:** Not too little, not too much
2. **Tune fragment size:** Balance between loss and overhead
3. **QoS configuration:** Prioritize PFT traffic
4. **Network improvements:** Fix underlying issues
5. **Regular testing:** Periodic validation of settings

---

## Complete Examples

### Production Setup with Monitoring

```bash
#!/bin/bash
# Production PFT streaming with logging

LOG_DIR="/var/log/dabmux"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pft_$(date +%Y%m%d_%H%M%S).log"

# Measure network loss first
echo "Testing network..." | tee -a "$LOG_FILE"
iperf3 -c 192.168.1.100 -u -b 1M -t 10 >> "$LOG_FILE" 2>&1

# Start multiplexer with PFT
echo "Starting multiplexer with PFT..." | tee -a "$LOG_FILE"
python -m dabmux.cli \
  -c /etc/dabmux/production.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 3 \
  --pft-fec-m 3 \
  --pft-fragment-size 512 \
  --tist \
  --continuous \
  -v 2>&1 | tee -a "$LOG_FILE"
```

### Adaptive FEC Script

```bash
#!/bin/bash
# Adapt FEC based on measured packet loss

DEST="udp://192.168.1.100:12000"
CONFIG="/etc/dabmux/config.yaml"

# Measure loss
loss=$(iperf3 -c 192.168.1.100 -u -b 1M -t 10 | grep loss | awk '{print $13}' | tr -d '(%)' )

echo "Measured packet loss: ${loss}%"

# Choose FEC based on loss
if (( $(echo "$loss < 0.5" | bc -l) )); then
    fec=2
elif (( $(echo "$loss < 2" | bc -l) )); then
    fec=3
elif (( $(echo "$loss < 5" | bc -l) )); then
    fec=5
else
    fec=10
fi

echo "Using FEC depth: $fec"

# Start with chosen FEC
python -m dabmux.cli \
  -c "$CONFIG" \
  --edi "$DEST" \
  --pft \
  --pft-fec $fec \
  --pft-fec-m $fec \
  --continuous \
  -v
```

---

## See Also

- [Output Formats Overview](index.md): All output types
- [EDI Network](edi-network.md): EDI streaming basics
- [ETI Files](eti-files.md): File-based output
- [Advanced: Reed-Solomon](../../advanced/reed-solomon.md): FEC mathematics
- [PFT Tutorial](../../tutorials/pft-with-fec.md): Step-by-step guide
