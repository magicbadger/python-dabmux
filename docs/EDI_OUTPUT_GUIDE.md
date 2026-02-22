# EDI Output Guide

Complete guide to distributing DAB ensembles over IP networks using the EDI (Ensemble Data Interface) protocol.

---

## Table of Contents

1. [What is EDI?](#what-is-edi)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [UDP Mode](#udp-mode)
5. [TCP Mode](#tcp-mode)
6. [PFT Fragmentation](#pft-fragmentation)
7. [TIST Timestamps](#tist-timestamps)
8. [Network Setup](#network-setup)
9. [Integration](#integration)
10. [Troubleshooting](#troubleshooting)

---

## What is EDI?

**EDI (Ensemble Data Interface)** is a protocol for transmitting DAB ensembles over IP networks.

### Why Use EDI?

**Traditional ETI:**
- File-based or serial connection
- Point-to-point only
- No network distribution
- Limited to local modulator

**EDI Advantages:**
- ✅ Network-based distribution
- ✅ Multiple receivers (multicast)
- ✅ Error correction (PFT with FEC)
- ✅ Precise timestamps (TIST for SFN)
- ✅ Long-distance distribution
- ✅ Professional broadcast infrastructure

### Use Cases

**Studio-to-Transmitter Links (STL):**
- Send DAB ensemble from studio to transmitter site
- IP-based distribution (fiber, microwave, satellite)
- Multiple transmitter sites from one source

**Single Frequency Networks (SFN):**
- Synchronized transmission from multiple sites
- TIST timestamps ensure identical transmission timing
- Wide-area coverage with seamless handover

**Cloud Broadcasting:**
- Multiplexer in cloud
- Modulator at transmitter site
- Scalable, flexible deployment

---

## Quick Start

### Basic UDP Configuration

Add to your configuration file:

```yaml
ensemble:
  # ... existing configuration ...

  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'  # Modulator IP:port
```

### Start Multiplexer

```bash
python -m dabmux.cli -c config.yaml -o output.eti --edi
```

You should see:
```
INFO: EDI output enabled (UDP to 192.168.1.100:12000)
```

### Verify Reception

On the receiver (modulator) machine:
```bash
# Check if packets are arriving
tcpdump -i eth0 udp port 12000

# Check with ODR-DabMod
odr-dabmod config.ini
```

---

## Configuration

### Full Configuration Options

```yaml
ensemble:
  edi_output:
    # Enable EDI output
    enabled: true

    # Protocol: 'udp' or 'tcp'
    protocol: 'udp'

    # Destination (IP:port)
    destination: '192.168.1.100:12000'

    # TCP mode (only for protocol: 'tcp')
    tcp_mode: 'client'  # or 'server'

    # PFT (Fragmentation with FEC)
    enable_pft: true
    pft_fec: 2          # FEC level (0-5)
    pft_fragment_size: 1400  # MTU consideration

    # TIST (Timestamps for SFN)
    enable_tist: true

    # Source identifier (optional)
    source_id: 0x1234
```

### Minimal Configuration

**UDP without FEC:**
```yaml
ensemble:
  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'
```

**UDP with FEC:**
```yaml
ensemble:
  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'
    enable_pft: true
    pft_fec: 2
```

**TCP Mode:**
```yaml
ensemble:
  edi_output:
    enabled: true
    protocol: 'tcp'
    destination: '192.168.1.100:12000'
    tcp_mode: 'client'
```

---

## UDP Mode

### When to Use UDP

**Advantages:**
- Simple configuration
- Low latency
- Multicast support (one-to-many)
- Industry standard for STL

**Disadvantages:**
- No reliability (packet loss possible)
- Requires PFT with FEC for error correction

### Configuration

```yaml
ensemble:
  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'
    enable_pft: true  # Recommended for UDP
    pft_fec: 2        # FEC level
```

### Unicast vs Multicast

**Unicast (Point-to-Point):**
```yaml
destination: '192.168.1.100:12000'
```

**Multicast (One-to-Many):**
```yaml
destination: '239.255.1.1:12000'  # Multicast address
```

**Multicast Setup:**
```bash
# On receiver, join multicast group
ip maddr add 239.255.1.1 dev eth0

# Check multicast routing
ip mroute show
```

### MTU Considerations

**Fragmentation:**
- Standard MTU: 1500 bytes
- Ethernet header: 14 bytes
- IP header: 20 bytes
- UDP header: 8 bytes
- Available for payload: 1458 bytes

**Configuration:**
```yaml
ensemble:
  edi_output:
    enable_pft: true
    pft_fragment_size: 1400  # Safe for most networks
```

**Networks with Smaller MTU:**
- VPN: 1400 bytes
- PPPoE: 1492 bytes
- Tunnel: Variable (check with `ping -M do -s 1472 <dest>`)

---

## TCP Mode

### When to Use TCP

**Advantages:**
- Reliable delivery (no packet loss)
- No PFT/FEC needed
- Works over WAN

**Disadvantages:**
- Higher latency
- Head-of-line blocking
- No multicast support
- More complex configuration

### Client Mode

Multiplexer connects to modulator:

```yaml
ensemble:
  edi_output:
    enabled: true
    protocol: 'tcp'
    destination: '192.168.1.100:12000'
    tcp_mode: 'client'
```

**Use when:** Modulator is at fixed location, multiplexer can initiate connection

### Server Mode

Multiplexer listens, modulator connects:

```yaml
ensemble:
  edi_output:
    enabled: true
    protocol: 'tcp'
    destination: '0.0.0.0:12000'  # Listen on all interfaces
    tcp_mode: 'server'
```

**Use when:** Multiplexer is at fixed location, modulator location may change

### Connection Management

**TCP Client:**
- Multiplexer connects on startup
- Auto-reconnect on disconnection
- No incoming firewall rules needed

**TCP Server:**
- Multiplexer listens on port
- Accepts one connection
- Requires incoming firewall rule

---

## PFT Fragmentation

### What is PFT?

**PFT (Protocol with Forward error correction at Transport level)**

- Fragments large EDI packets into smaller chunks
- Adds Reed-Solomon FEC for error correction
- Enables reliable UDP transmission over lossy networks

### Why Use PFT?

**Without PFT (UDP):**
- Packet loss = lost frames
- No recovery possible
- Requires perfect network

**With PFT (UDP + FEC):**
- Packet loss tolerated
- FEC reconstructs lost packets
- Works on imperfect networks

### FEC Levels

```yaml
ensemble:
  edi_output:
    enable_pft: true
    pft_fec: 2  # FEC level (0-5)
```

**FEC Level Guide:**

| Level | Redundancy | Can Recover | Use Case |
|-------|------------|-------------|----------|
| 0 | 0% | 0% loss | Perfect network (testing only) |
| 1 | 25% | Up to 20% loss | Wired LAN |
| 2 | 50% | Up to 33% loss | **Recommended** (balanced) |
| 3 | 75% | Up to 43% loss | Wireless links |
| 4 | 100% | Up to 50% loss | Poor networks |
| 5 | 125% | Up to 56% loss | Very poor networks |

**Recommendation:** Start with `pft_fec: 2` and adjust based on network quality

### Fragment Size

```yaml
ensemble:
  edi_output:
    pft_fragment_size: 1400  # bytes
```

**Guidelines:**
- Standard networks: 1400 bytes
- VPN/tunnels: 1300 bytes
- Satellite links: 1200 bytes
- Check network MTU: `ping -M do -s <size> <dest>`

### Overhead

**Bandwidth calculation:**
```
Total bandwidth = ETI bitrate × (1 + FEC_level / 100)

Example (96 kbps ensemble, FEC level 2):
Total = 96 kbps × 1.5 = 144 kbps
```

---

## TIST Timestamps

### What is TIST?

**TIST (Time Stamp)** - Precise timestamp for each ETI frame

### Why Use TIST?

**Single Frequency Networks (SFN):**
- Multiple transmitters on same frequency
- Must transmit identical signal at identical time
- TIST ensures synchronization (within microseconds)

**Without TIST:**
- Transmitters out of sync
- Destructive interference
- Coverage gaps

**With TIST:**
- Transmitters synchronized
- Constructive interference
- Seamless coverage

### Configuration

```yaml
ensemble:
  edi_output:
    enabled: true
    enable_tist: true
```

### TIST Format

**Timestamp precision:** 1/16.384 MHz (61 nanoseconds)

**Timestamp sources:**
- System clock (NTP synchronized)
- GPS receiver (for SFN)
- PTP (Precision Time Protocol)

### SFN Deployment

**Requirements:**
1. All transmitters GPS synchronized
2. TIST enabled in EDI
3. Modulators synchronized to GPS
4. Network delay compensated

**Example:**
```
┌──────────────┐
│ Multiplexer  │ (GPS synchronized)
│ + TIST       │
└───────┬──────┘
        │ EDI with TIST
        ├────────────┐
        │            │
   ┌────▼────┐  ┌───▼─────┐
   │ Mod A   │  │ Mod B   │ (GPS synchronized)
   │ GPS sync│  │ GPS sync│
   └────┬────┘  └───┬─────┘
        │           │
   ┌────▼────┐  ┌──▼──────┐
   │ TX A    │  │ TX B    │ (same frequency)
   │ Same    │  │ Same    │
   │ freq    │  │ content │
   └─────────┘  └─────────┘
        ╲        ╱
         ╲      ╱
       Coverage area
```

---

## Network Setup

### Basic Network (Studio to Transmitter)

```
┌──────────────┐  Ethernet/Fiber  ┌──────────────┐
│ Multiplexer  ├─────────────────→│  Modulator   │
│ 192.168.1.10 │  UDP:12000       │ 192.168.1.100│
└──────────────┘                  └──────────────┘
```

**Configuration:**
```yaml
# Multiplexer
edi_output:
  enabled: true
  protocol: 'udp'
  destination: '192.168.1.100:12000'
```

### SFN Network (Multiple Transmitters)

```
                   ┌──────────────┐
                   │ Multiplexer  │ (Studio)
                   │ 192.168.1.10 │
                   └───────┬──────┘
                           │ Multicast
                           │ 239.255.1.1:12000
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼─────┐ ┌───▼─────┐
        │ Mod A     │ │ Mod B   │ │ Mod C   │
        │ Site 1    │ │ Site 2  │ │ Site 3  │
        └─────┬─────┘ └───┬─────┘ └───┬─────┘
              │           │           │
         ┌────▼────┐ ┌───▼─────┐ ┌──▼──────┐
         │ TX A    │ │ TX B    │ │ TX C    │
         │ Same F  │ │ Same F  │ │ Same F  │
         └─────────┘ └─────────┘ └─────────┘
```

**Configuration:**
```yaml
# Multiplexer
edi_output:
  enabled: true
  protocol: 'udp'
  destination: '239.255.1.1:12000'  # Multicast
  enable_pft: true
  pft_fec: 2
  enable_tist: true
```

### Firewall Configuration

**Allow EDI traffic:**
```bash
# iptables (UDP)
iptables -A INPUT -p udp --dport 12000 -j ACCEPT
iptables -A OUTPUT -p udp --dport 12000 -j ACCEPT

# iptables (multicast)
iptables -A INPUT -p udp -d 239.255.1.1 --dport 12000 -j ACCEPT

# ufw (Ubuntu)
ufw allow 12000/udp
```

### QoS (Quality of Service)

**Prioritize EDI traffic:**
```bash
# tc (Traffic Control)
tc qdisc add dev eth0 root handle 1: htb default 12
tc class add dev eth0 parent 1: classid 1:1 htb rate 1gbit
tc class add dev eth0 parent 1:1 classid 1:10 htb rate 200kbit prio 1
tc filter add dev eth0 protocol ip parent 1:0 prio 1 u32 \
  match ip dport 12000 0xffff flowid 1:10
```

---

## Integration

### ODR-DabMod Integration

**ODR-DabMod Configuration:**

Create `odr-dabmod.ini`:
```ini
[input]
transport = edi
source = udp://:12000  # Listen for EDI

[modulator]
rate = 2048000
gainmode = 2
digital_gain = 1.0

[output]
; Choose output type
output = uhd      ; USRP
; output = soapysdr ; SoapySDR
; output = file     ; File output

[uhdoutput]
device =
frequency = 229072000  ; DAB channel 11D
txgain = 70
```

**Start ODR-DabMod:**
```bash
odr-dabmod odr-dabmod.ini
```

**Verify:**
```
INFO: EDI input listening on :12000
INFO: Received EDI frame (TIST: 123456789)
INFO: Modulating...
```

### Professional Modulators

Most professional DAB modulators support EDI:

**GatesAir/Harris:**
- Supports EDI over UDP
- Configure IP and port in web interface
- PFT with FEC recommended

**Worldcast Systems:**
- Supports EDI over UDP/TCP
- TIST support for SFN
- Web-based configuration

**Rohde & Schwarz:**
- Full EDI support
- Advanced SFN features
- Professional monitoring

**Configuration:**
```yaml
# For professional modulators
edi_output:
  enabled: true
  protocol: 'udp'
  destination: '<modulator-ip>:12000'
  enable_pft: true
  pft_fec: 2
  enable_tist: true  # For SFN
```

---

## Troubleshooting

### No Packets Received

**Check network connectivity:**
```bash
ping 192.168.1.100
```

**Check firewall:**
```bash
# Temporarily disable
sudo ufw disable

# Check iptables
sudo iptables -L -n
```

**Verify packets sent:**
```bash
# On multiplexer
tcpdump -i eth0 udp port 12000

# Should see outgoing packets
```

**Verify packets received:**
```bash
# On modulator
tcpdump -i eth0 udp port 12000

# Should see incoming packets
```

### Packet Loss

**Measure packet loss:**
```bash
# On receiver
iperf3 -s -p 12001

# On sender
iperf3 -c <receiver-ip> -p 12001 -u -b 200k -t 60
```

**Solutions:**
1. Increase PFT FEC level
2. Reduce fragment size
3. Enable QoS
4. Check network hardware (switches, routers)
5. Use TCP instead of UDP

### High Latency

**Measure latency:**
```bash
ping -c 100 192.168.1.100 | tail -1
```

**Solutions:**
1. Check network path (traceroute)
2. Reduce buffer sizes
3. Enable QoS
4. Use direct network connection
5. For SFN: Latency must be consistent, not necessarily low

### Synchronization Issues (SFN)

**Check GPS lock:**
- All modulators must have GPS lock
- Check GPS antenna placement
- Verify GPS status in modulator web interface

**Check TIST enabled:**
```yaml
enable_tist: true
```

**Check time synchronization:**
```bash
# On all machines
ntpq -p

# GPS time should be primary source
```

**Verify TIST in EDI:**
```bash
# Capture EDI packet
tcpdump -i eth0 -w edi.pcap udp port 12000

# Analyze with Wireshark
# Check for TIST TAG packets
```

---

## Performance

### Bandwidth Requirements

**Calculate required bandwidth:**
```
Ensemble bitrate: X kbps
PFT FEC level: Y

Required bandwidth = X × (1 + Y/100) kbps
```

**Examples:**

| Ensemble | FEC | Total Bandwidth |
|----------|-----|-----------------|
| 96 kbps  | 0   | 96 kbps         |
| 96 kbps  | 2   | 144 kbps        |
| 384 kbps | 0   | 384 kbps        |
| 384 kbps | 2   | 576 kbps        |
| 1536 kbps| 2   | 2304 kbps       |

### Network Requirements

**Minimum:**
- 100 Mbps Ethernet (sufficient for multiple ensembles)
- < 100ms latency (for non-SFN)
- < 1% packet loss (with PFT FEC 2)

**SFN:**
- < 10ms jitter (timestamp accuracy)
- GPS synchronized time
- Stable latency (consistent delay OK)

---

## Standards Compliance

**ETSI TS 102 693** - Digital Audio Broadcasting (DAB); Encapsulation of DAB Interfaces (EDI)

**Implemented:**
- ✅ AF packets (audio frames)
- ✅ TAG packets (timestamps, metadata)
- ✅ PFT fragmentation
- ✅ Reed-Solomon FEC (levels 0-5)
- ✅ TIST timestamps
- ✅ UDP and TCP transport

---

## Resources

**Standards:**
- ETSI TS 102 693 - EDI Specification

**Tools:**
- ODR-DabMod - Open-source DAB modulator
- Wireshark - Packet analysis
- tcpdump - Packet capture

**Examples:**
- `examples/edi_udp.yaml` - UDP configuration
- `examples/edi_tcp.yaml` - TCP configuration
- `examples/edi_sfn.yaml` - SFN configuration

---

**Last Updated:** 2026-02-22

**Status:** Production Ready

For additional help, see [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) or [Quick Start Guide](QUICK_START.md).
