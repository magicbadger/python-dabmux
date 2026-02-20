# EDI Network Output

Complete guide to streaming DAB multiplex data via EDI (Ensemble Data Interface) over IP networks.

!!! info "Implementation Status"
    **Currently Available (v0.x):**

    - ✅ Full EDI protocol implementation (TAG items, AF packets)
    - ✅ UDP output (unicast & multicast)
    - ✅ TCP output (client & server modes)
    - ✅ TIST timestamp synchronization
    - ✅ PFT fragmentation with Reed-Solomon FEC
    - ✅ Programmatic API (Python configuration)

    **Coming Soon:**

    - ⏳ CLI arguments (--edi, --edi-destination, etc.) - Phase 4
    - ⏳ YAML configuration schema - Phase 4
    - ⏳ Example configuration files - Phase 4

    For now, use the programmatic API as shown in the [Integration Examples](#integration-examples) section below. CLI arguments will be added in the next release.

## Overview

EDI is the network protocol for distributing ETI frames to remote transmitters. It encapsulates ETI data in TAG-based packets suitable for UDP or TCP transmission.

**Key features:**
- Real-time streaming
- Low latency
- Optional fragmentation and FEC (PFT)
- Timestamp support
- Sequence numbering

**Standard:** ETSI TS 102 693

---

## EDI Protocol Stack

```
┌─────────────────────┐
│   ETI Frame Data    │  Application Layer
├─────────────────────┤
│   TAG Items         │  EDI Layer
│   (*ptr, deti, etc) │
├─────────────────────┤
│   TAG Packet        │  TAG Layer
│   (8-byte aligned)  │
├─────────────────────┤
│   AF Packet         │  AF Layer
│   (SYNC + CRC)      │
├─────────────────────┤
│   [Optional: PFT]   │  PFT Layer
│   (Fragments + FEC) │
├─────────────────────┤
│   UDP / TCP         │  Transport Layer
└─────────────────────┘
```

See [Architecture: EDI Protocol](../../architecture/edi-protocol.md) for detailed diagrams.

---

## Integration Examples

!!! note "Current API (Pre-CLI)"
    Until CLI arguments are available, use the programmatic API by configuring `EdiOutputConfig` in your ensemble YAML or Python code.

### UDP Output (Programmatic)

**YAML Configuration:**
```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'My Ensemble'
  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'
    enable_pft: false
```

**Python API:**
```python
from dabmux.mux import DabMultiplexer
from dabmux.core.mux_elements import DabEnsemble, DabLabel, EdiOutputConfig

# Configure ensemble with EDI output
ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    label=DabLabel(text="My Ensemble"),
    edi_output=EdiOutputConfig(
        enabled=True,
        protocol="udp",
        destination="192.168.1.100:12000"
    )
)

# Create multiplexer (automatically initializes EDI output)
mux = DabMultiplexer(ensemble)

# Generate frames (automatically sent via EDI)
for i in range(1000):
    frame = mux.generate_frame()
    # Frame automatically transmitted to 192.168.1.100:12000

# Cleanup
mux.edi_output.close()
```

### TCP Client Mode

**YAML Configuration:**
```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'My Ensemble'
  edi_output:
    enabled: true
    protocol: 'tcp'
    tcp_mode: 'client'  # Connect to remote server
    destination: '192.168.1.100:12000'
```

**Python API:**
```python
ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    label=DabLabel(text="My Ensemble"),
    edi_output=EdiOutputConfig(
        enabled=True,
        protocol="tcp",
        tcp_mode="client",
        destination="192.168.1.100:12000"
    )
)

mux = DabMultiplexer(ensemble)
# TCP connection established automatically
# Frames sent reliably over TCP
```

### TCP Server Mode

**YAML Configuration:**
```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'My Ensemble'
  edi_output:
    enabled: true
    protocol: 'tcp'
    tcp_mode: 'server'  # Listen for connections
    destination: '0.0.0.0:12000'
```

**Python API:**
```python
ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    label=DabLabel(text="My Ensemble"),
    edi_output=EdiOutputConfig(
        enabled=True,
        protocol="tcp",
        tcp_mode="server",
        destination="0.0.0.0:12000"  # Listen on all interfaces
    )
)

mux = DabMultiplexer(ensemble)
# Server listening on port 12000
# Multiple clients can connect
# Frames broadcast to all connected clients
```

### UDP with PFT and FEC

**YAML Configuration:**
```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  label:
    text: 'My Ensemble'
  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'
    enable_pft: true
    pft_fec: 3          # FEC depth (0-7)
    pft_fragment_size: 1400  # MTU-based fragmentation
```

**Python API:**
```python
ensemble = DabEnsemble(
    id=0xCE15,
    ecc=0xE1,
    label=DabLabel(text="My Ensemble"),
    edi_output=EdiOutputConfig(
        enabled=True,
        protocol="udp",
        destination="192.168.1.100:12000",
        enable_pft=True,
        pft_fec=3,
        pft_fragment_size=1400
    )
)

mux = DabMultiplexer(ensemble)
# EDI packets fragmented and protected with Reed-Solomon FEC
```

---

## Basic EDI Streaming

!!! warning "CLI Not Yet Available"
    The CLI examples below show the planned interface. For now, use the [Integration Examples](#integration-examples) above with YAML or Python API.


### UDP Output

```bash
python -m dabmux.cli -c config.yaml --edi udp://192.168.1.100:12000
```

**Sends EDI packets to:**
- Host: 192.168.1.100
- Port: 12000
- Protocol: UDP

### TCP Output

```bash
python -m dabmux.cli -c config.yaml --edi tcp://192.168.1.100:12000
```

**Opens TCP connection to modulator:**
- Guaranteed delivery
- Higher latency than UDP
- No packet loss

### Multicast Output

```bash
python -m dabmux.cli -c config.yaml --edi udp://239.1.2.3:12000
```

**Multicast distribution:**
- One encoder → multiple receivers
- Efficient bandwidth usage
- Requires multicast-capable network

---

## EDI Packet Structure

### AF (Assembly Format) Packet

**Structure:**
```
┌──────────┬─────────────┬─────────┬────────────┬──────┐
│ SYNC     │ LEN         │ SEQ     │ PAYLOAD    │ CRC  │
│ (2 bytes)│ (4 bytes)   │ (2 bytes│ (variable) │ (2 B)│
└──────────┴─────────────┴─────────┴────────────┴──────┘
```

**Fields:**
- **SYNC:** 0x4146 ("AF" in ASCII)
- **LEN:** Payload length
- **SEQ:** Sequence number (wraps at 65535)
- **PAYLOAD:** TAG items
- **CRC:** 16-bit CRC

### TAG Items

**Common TAG types:**

| TAG | Name | Purpose |
|-----|------|---------|
| `*ptr` | Protocol Type | Indicates protocol version |
| `deti` | DAB ETI Data | Contains ETI frame |
| `est` | ETI Stream | Stream characteristics |
| `*dmy` | Dummy | Padding/alignment |

**TAG structure:**
```
┌──────────┬─────────┬──────────┐
│ Name     │ Length  │ Value    │
│ (4 bytes)│ (4 bytes│ (N bytes)│
└──────────┴─────────┴──────────┘
```

---

## Bandwidth Requirements

### Without PFT

**Formula:**
```
Bandwidth ≈ ETI bitrate × 1.15
```

**Mode I example:**
- ETI: 6144 bytes per 96ms frame
- Rate: 6144 × (1000/96) = 64,000 bytes/s = 512 kbps
- With overhead: 512 × 1.15 ≈ **590 kbps**

### With PFT

**Formula:**
```
Bandwidth ≈ ETI bitrate × (1.15 + FEC_overhead)
```

**FEC overhead depends on settings:**
- FEC depth 2, M=3: +30% overhead
- FEC depth 3, M=5: +40% overhead
- FEC depth 5, M=7: +50% overhead

**Mode I with PFT example:**
- Base: 512 kbps
- PFT overhead (30%): 154 kbps
- **Total: ~665 kbps**

---

## Network Configuration

### Firewall Rules

#### Linux (iptables)

**Allow UDP:**
```bash
# Outbound (multiplexer)
sudo iptables -A OUTPUT -p udp --dport 12000 -j ACCEPT

# Inbound (modulator)
sudo iptables -A INPUT -p udp --dport 12000 -j ACCEPT
```

**Allow TCP:**
```bash
# Outbound (multiplexer)
sudo iptables -A OUTPUT -p tcp --dport 12000 -j ACCEPT

# Inbound (modulator)
sudo iptables -A INPUT -p tcp --dport 12000 -j ACCEPT
```

**Allow multicast:**
```bash
# Enable IGMP
sudo iptables -A INPUT -p igmp -j ACCEPT

# Allow multicast traffic
sudo iptables -A INPUT -d 239.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -d 239.0.0.0/8 -j ACCEPT
```

#### Linux (firewalld)

```bash
# Add UDP port
sudo firewall-cmd --add-port=12000/udp --permanent

# Add TCP port
sudo firewall-cmd --add-port=12000/tcp --permanent

# Reload
sudo firewall-cmd --reload
```

### Router Configuration

**Port forwarding:**
1. Access router configuration
2. Forward external port 12000 → internal IP:12000
3. Select UDP or TCP based on usage

**Multicast routing:**
```bash
# Enable multicast forwarding (Linux router)
sudo sysctl -w net.ipv4.conf.all.mc_forwarding=1

# Add multicast route
sudo route add -net 239.0.0.0 netmask 255.0.0.0 dev eth0
```

---

## Quality of Service (QoS)

### Traffic Prioritization

**Linux traffic control:**
```bash
# Prioritize EDI traffic on eth0
sudo tc qdisc add dev eth0 root handle 1: htb default 12

# Create priority class
sudo tc class add dev eth0 parent 1: classid 1:1 htb rate 1gbit

# High priority for EDI
sudo tc class add dev eth0 parent 1:1 classid 1:10 htb rate 10mbit prio 0

# Filter EDI traffic (port 12000)
sudo tc filter add dev eth0 protocol ip parent 1:0 prio 1 u32 \
  match ip dport 12000 0xffff flowid 1:10
```

### Router QoS

**Typical settings:**
- **Protocol:** UDP
- **Port:** 12000
- **Priority:** High or Critical
- **Bandwidth reservation:** 1-2 Mbps (safe margin)

---

## Monitoring and Statistics

### Enable Verbose Output

```bash
python -m dabmux.cli -c config.yaml --edi udp://192.168.1.100:12000 -v
```

**Statistics displayed:**
- Packets sent
- Bytes transmitted
- Sequence numbers
- Errors detected
- Buffer status

### Example Output

```
INFO: Generated frame 1000
INFO: EDI: Sent 1000 packets, 6,200,000 bytes
INFO: EDI: Sequence 1000, 0 errors
INFO: EDI: Send buffer: 15% full
```

### Network Monitoring

**Check UDP traffic:**
```bash
# Monitor outgoing EDI packets
sudo tcpdump -i eth0 udp port 12000 -v

# Count packets
sudo tcpdump -i eth0 udp port 12000 -c 100
```

**Check TCP connection:**
```bash
# Monitor TCP connection
netstat -tn | grep 12000

# Example output:
# tcp    0    0 192.168.1.50:45678    192.168.1.100:12000    ESTABLISHED
```

---

## UDP vs TCP

### UDP Streaming

**Advantages:**
- ✅ Low latency (1-10ms)
- ✅ Multicast support
- ✅ Simple protocol
- ✅ Lower overhead

**Disadvantages:**
- ❌ No delivery guarantee
- ❌ Packet loss possible
- ❌ No congestion control
- ❌ Sequence gaps on loss

**Use when:**
- Low latency critical
- Reliable network (< 1% loss)
- Multicast needed
- Using PFT for error recovery

### TCP Streaming

**Advantages:**
- ✅ Guaranteed delivery
- ✅ No packet loss
- ✅ Automatic retransmission
- ✅ Congestion control

**Disadvantages:**
- ❌ Higher latency (10-50ms)
- ❌ No multicast
- ❌ Head-of-line blocking
- ❌ Connection overhead

**Use when:**
- Reliability critical
- Network has packet loss
- Point-to-point only
- Latency tolerance > 20ms

---

## Real-time Streaming Setup

### Complete Production Setup

**Multiplexer (192.168.1.50):**

```bash
#!/bin/bash
# Start multiplexer with EDI streaming

LOG_DIR="/var/log/dabmux"
mkdir -p "$LOG_DIR"

while true; do
    python -m dabmux.cli \
      -c /etc/dabmux/production.yaml \
      --edi udp://192.168.1.100:12000 \
      --pft \
      --pft-fec 3 \
      --pft-fec-m 5 \
      --tist \
      --continuous \
      -v 2>&1 | tee -a "$LOG_DIR/dabmux_$(date +%Y%m%d).log"

    echo "Multiplexer stopped, restarting in 5 seconds..."
    sleep 5
done
```

**Modulator (192.168.1.100):**

Must be configured to:
- Listen on UDP port 12000
- Accept EDI with PFT
- Handle TIST timestamps

### Systemd Service

**Create `/etc/systemd/system/dabmux-edi.service`:**

```ini
[Unit]
Description=DAB Multiplexer with EDI Streaming
After=network.target

[Service]
Type=simple
User=dabmux
Group=dabmux
WorkingDirectory=/opt/dabmux
ExecStart=/opt/dabmux/bin/start_edi_stream.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable dabmux-edi
sudo systemctl start dabmux-edi
sudo systemctl status dabmux-edi
```

---

## Advanced Configuration

### Multiple EDI Outputs

```bash
# Send to multiple destinations (requires script)
# Not supported directly - use multicast or PFT broadcast
```

**Multicast solution:**
```bash
# Send to multicast group
python -m dabmux.cli -c config.yaml --edi udp://239.1.2.3:12000

# Multiple receivers join multicast group
# Each modulator independently receives stream
```

### Redundancy

**Primary + Backup:**
```bash
#!/bin/bash
# Primary multiplexer

python -m dabmux.cli \
  -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --continuous &

# Backup multiplexer (same config, same multicast)
python -m dabmux.cli \
  -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --continuous &

# Modulator receives from both, uses first/best
```

---

## Troubleshooting

### No Connection / Cannot Send

**Problem:**
```
ERROR: Cannot send to udp://192.168.1.100:12000
```

**Diagnosis:**
```bash
# Test connectivity
ping 192.168.1.100

# Test UDP port (send test packet)
echo "test" | nc -u 192.168.1.100 12000

# Check firewall
sudo iptables -L -n | grep 12000
```

**Solutions:**
1. Check network connectivity
2. Verify firewall allows UDP/TCP port 12000
3. Ensure modulator is listening
4. Check IP address and port

### Packet Loss

**Problem:**
```
WARNING: EDI: High packet loss detected
```

**Diagnosis:**
```bash
# Monitor packet loss
sudo tcpdump -i eth0 udp port 12000 -c 1000

# Check network statistics
netstat -s | grep -i "packet loss"

# Test with iperf
iperf3 -c 192.168.1.100 -u -b 1M
```

**Solutions:**
1. **Enable PFT with FEC:** Recovers lost packets
2. **Use TCP instead of UDP:** Guaranteed delivery
3. **Improve network:** Better switches, dedicated VLAN
4. **Reduce other traffic:** QoS prioritization
5. **Check cables and interfaces:** Physical layer issues

### Multicast Not Working

**Problem:** Multicast packets not received

**Diagnosis:**
```bash
# Check IGMP support
cat /proc/net/igmp

# Test multicast join
sudo ip maddr add 239.1.2.3 dev eth0
sudo tcpdump -i eth0 'dst 239.1.2.3'

# Check routing
route -n | grep 239
```

**Solutions:**
1. **Enable IGMP on router and switches**
2. **Add multicast route:**
   ```bash
   sudo route add -net 239.0.0.0 netmask 255.0.0.0 dev eth0
   ```
3. **Join multicast group manually**
4. **Check TTL value:** Increase if packets don't reach destination

### High Latency

**Problem:** Unacceptable delay

**Typical latency:**
- UDP without PFT: 1-10ms
- UDP with PFT: 10-30ms
- TCP: 10-50ms

**If higher:**

**Solutions:**
1. **Use UDP instead of TCP**
2. **Disable PFT if network reliable**
3. **Reduce network hops:** Direct connection
4. **Check network congestion:** QoS, traffic shaping
5. **Upgrade network infrastructure**

---

## Best Practices

### Network Design

1. **Dedicated network:** Separate VLAN for streaming
2. **Gigabit links:** Minimum 100 Mbps, prefer 1 Gbps
3. **Managed switches:** Enable multicast filtering, QoS
4. **Redundant paths:** Multiple network routes
5. **Low latency:** Minimize hops between encoder and modulator

### Protocol Selection

1. **Use UDP + PFT** for most deployments
2. **Use TCP** only if packet loss > 2% and can tolerate latency
3. **Use multicast** for one-to-many distribution
4. **Enable TIST** for SFN or multi-transmitter setups

### Monitoring

1. **Log all output:** Keep verbose logs
2. **Monitor packet loss:** Alert on > 0.5%
3. **Track sequence gaps:** Indicates lost packets
4. **Bandwidth monitoring:** Ensure sufficient headroom
5. **Automated alerts:** Email/SMS on failures

### Security

1. **Firewall:** Only allow necessary ports
2. **VPN:** Use VPN for remote streaming
3. **Private networks:** Keep streaming on internal networks
4. **Authentication:** Modulator-side authentication if supported
5. **Monitoring:** Watch for unusual traffic

---

## Examples

### Basic UDP Streaming

```bash
# Simple UDP streaming to local modulator
python -m dabmux.cli \
  -c config.yaml \
  --edi udp://127.0.0.1:12000 \
  --continuous
```

### Production UDP + PFT

```bash
# Production setup with error correction
python -m dabmux.cli \
  -c production.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 3 \
  --pft-fec-m 5 \
  --tist \
  --continuous \
  -v
```

### Multicast Distribution

```bash
# Send to multicast for multiple receivers
python -m dabmux.cli \
  -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec 2 \
  --pft-fec-m 3 \
  --continuous
```

### Archival + Streaming

```bash
# Archive to file AND stream to network
python -m dabmux.cli \
  -c config.yaml \
  -o "/archive/dab_$(date +%Y%m%d_%H%M%S).eti" \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --continuous
```

### TCP for Reliable Delivery

```bash
# Use TCP for guaranteed delivery
python -m dabmux.cli \
  -c config.yaml \
  --edi tcp://192.168.1.100:12000 \
  --continuous
```

---

## See Also

- [Output Formats Overview](index.md): All output types
- [PFT Fragmentation](pft-fragmentation.md): Forward error correction details
- [ETI Files](eti-files.md): File-based output
- [Architecture: EDI Protocol](../../architecture/edi-protocol.md): Protocol stack diagrams
- [PFT Tutorial](../../tutorials/pft-with-fec.md): Step-by-step PFT setup
