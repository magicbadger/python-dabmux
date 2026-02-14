# Tutorial: PFT with FEC

Use PFT (Protection, Fragmentation and Transport) with Reed-Solomon FEC for reliable network transmission.

**Difficulty:** Advanced
**Time:** 35 minutes

## What You'll Build

An EDI output setup with:
- PFT fragmentation
- Reed-Solomon Forward Error Correction
- Resilience to packet loss
- Network monitoring

## Prerequisites

- Completed [Network Streaming Tutorial](network-streaming.md)
- Understanding of [EDI Protocol](../architecture/edi-protocol.md)
- Network tools (netcat, tcpdump)

## What is PFT?

**PFT (Protection, Fragmentation and Transport)** adds three capabilities to EDI:

1. **Fragmentation**: Splits large packets to fit MTU
2. **Sequencing**: Detects missing fragments
3. **FEC**: Recovers lost fragments using Reed-Solomon

## Step 1: Basic PFT Setup

### Configuration

Create `pft_config.yaml`:

```yaml
ensemble:
  id: '0xCE30'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'PFT Demo'
    short: 'PFT'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x8001'
    label:
      text: 'PFT Radio'

components:
  - uid: 'comp1'
    service_id: '0x8001'
    subchannel_id: 0
```

### Run with PFT (no FEC yet)

```bash
python -m dabmux.cli \
  -c pft_config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --continuous
```

**What happens:**
- ETI frames converted to EDI
- Large packets fragmented to 1400 bytes
- Fragments sent over UDP

## Step 2: Enable Reed-Solomon FEC

### Run with FEC

```bash
python -m dabmux.cli \
  -c pft_config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec \
  --pft-fec-m 2 \
  --continuous
```

**Flags:**
- `--pft`: Enable PFT fragmentation
- `--pft-fec`: Enable Reed-Solomon FEC
- `--pft-fec-m 2`: Can recover up to 2 lost fragments

### How FEC Works

**Example:** ETI frame fragmented into 5 data fragments + 2 parity fragments

```
Data fragments:    [1] [2] [3] [4] [5]
Parity fragments:                    [P1] [P2]

Total sent: 7 fragments

Can lose any 2 and still reconstruct:
- Lost [2] and [4]? Recover using [1][3][5][P1][P2]
- Lost [3] and [P1]? Recover using [1][2][4][5][P2]
```

## Step 3: Configure FEC Parameters

### Understanding M Parameter

`--pft-fec-m M` sets recovery capability:

| M | Recovery | Overhead | Use Case |
|---|----------|----------|----------|
| 1 | 1 fragment | ~14% | Low packet loss |
| 2 | 2 fragments | ~29% | Moderate packet loss |
| 3 | 3 fragments | ~43% | High packet loss |
| 4 | 4 fragments | ~57% | Very high packet loss |

**Trade-off:** Higher M = better recovery but more bandwidth.

### Fragment Size

```bash
# Default: 1400 bytes (fits standard MTU)
python -m dabmux.cli --edi udp://239.1.2.3:12000 --pft --pft-fragment-size 1400

# Smaller fragments (more conservative)
python -m dabmux.cli --edi udp://239.1.2.3:12000 --pft --pft-fragment-size 1200

# Larger fragments (jumbo frames)
python -m dabmux.cli --edi udp://239.1.2.3:12000 --pft --pft-fragment-size 8000
```

**Rule:** Fragment size must be < network MTU (typically 1500 bytes)

## Step 4: Test Packet Loss Recovery

### Simulate Packet Loss

Use `tc` (traffic control) to simulate packet loss:

```bash
# Add 10% packet loss on interface eth0
sudo tc qdisc add dev eth0 root netem loss 10%

# Check it's applied
sudo tc qdisc show dev eth0
```

### Run with Different FEC Settings

**No FEC (baseline):**
```bash
python -m dabmux.cli -c pft_config.yaml --edi udp://239.1.2.3:12000 --pft -n 1000
```

With 10% loss, ~10% of fragments lost → some frames unrecoverable.

**With FEC m=2:**
```bash
python -m dabmux.cli -c pft_config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fec --pft-fec-m 2 -n 1000
```

With 10% loss, can recover up to 2 lost fragments per frame → much better!

### Remove Packet Loss

```bash
# Remove packet loss
sudo tc qdisc del dev eth0 root
```

## Step 5: Monitor Network Performance

### Capture PFT Packets

```bash
# Capture EDI/PFT traffic
sudo tcpdump -i any udp port 12000 -w pft_capture.pcap

# Analyze capture
tcpdump -r pft_capture.pcap -n | head -20
```

### Check Fragment Count

Look for PF (PFT) sync bytes (0x5046):

```bash
tcpdump -r pft_capture.pcap -X | grep "5046"
```

### Bandwidth Calculation

**Without PFT:**
- ETI frame: 6000 bytes
- Overhead: ~2% (EDI headers)
- Bandwidth: ~6120 bytes/frame

**With PFT (no FEC):**
- Fragmented into 5 fragments
- Overhead: ~5% (PFT headers)
- Bandwidth: ~6300 bytes/frame

**With PFT + FEC (m=2):**
- 5 data + 2 parity fragments
- Total: 7 fragments
- Overhead: ~40%
- Bandwidth: ~8400 bytes/frame

## Step 6: Production Setup

### Recommended Settings

**Low packet loss (<1%):**
```bash
python -m dabmux.cli \
  -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec \
  --pft-fec-m 1 \
  --pft-fragment-size 1400 \
  --continuous
```

**Moderate packet loss (1-5%):**
```bash
python -m dabmux.cli \
  -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec \
  --pft-fec-m 2 \
  --pft-fragment-size 1400 \
  --continuous
```

**High packet loss (5-10%):**
```bash
python -m dabmux.cli \
  -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec \
  --pft-fec-m 3 \
  --pft-fragment-size 1200 \
  --continuous
```

### Network Optimization

**Use dedicated network:**
- Separate VLAN for DAB traffic
- QoS prioritization
- Wired connections only

**Monitor performance:**
```bash
# Check packet loss
netstat -su | grep "packet receive errors"

# Monitor bandwidth
iftop -i eth0 -f "udp port 12000"
```

## Troubleshooting

### High bandwidth usage

**Problem:** PFT + FEC uses too much bandwidth

**Solutions:**
1. Reduce M parameter (less FEC)
2. Use larger fragment size
3. Skip PFT if network is reliable

### Fragments not reassembling

**Problem:** Receiver can't reconstruct frames

**Causes:**
- More than M fragments lost
- Sequence number gaps
- Fragment timeout

**Solutions:**
1. Increase M parameter
2. Improve network reliability
3. Check receiver buffer size

### MTU issues

**Error:** Fragments larger than MTU

**Solution:** Reduce fragment size:
```bash
--pft-fragment-size 1200  # Conservative
```

## Real-World Scenarios

### Local Network (LAN)
```bash
# Reliable wired network - minimal PFT
--pft --pft-fragment-size 1400
# No FEC needed
```

### Wireless Network (WiFi)
```bash
# Some packet loss expected
--pft --pft-fec --pft-fec-m 2 --pft-fragment-size 1200
```

### Wide Area Network (WAN)
```bash
# Higher latency and loss
--pft --pft-fec --pft-fec-m 3 --pft-fragment-size 1200
```

### Internet (Public)
```bash
# Unpredictable conditions
--pft --pft-fec --pft-fec-m 4 --pft-fragment-size 1000
```

## Summary

You've learned PFT with FEC:

- ✅ Enabling PFT fragmentation
- ✅ Configuring Reed-Solomon FEC
- ✅ Calculating recovery parameters
- ✅ Testing packet loss resilience
- ✅ Production deployment

PFT+FEC makes network transmission robust against packet loss!

## Quick Reference

```bash
# Basic PFT (no FEC)
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --continuous

# PFT with FEC (recover 2 lost fragments)
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fec --pft-fec-m 2 --continuous

# Custom fragment size
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fragment-size 1200 --continuous
```
