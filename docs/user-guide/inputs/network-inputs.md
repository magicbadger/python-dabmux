# Network Inputs

Complete guide to UDP and TCP network inputs for live streaming.

## Overview

Network inputs receive audio streams over IP networks via UDP or TCP protocols. They enable live broadcasting, remote encoders, and distributed architectures.

**Protocols supported:**
- **UDP:** Low-latency, multicast-capable, connectionless
- **TCP:** Reliable, guaranteed delivery, connection-oriented

---

## UDP Inputs

### Basic Configuration

**URI format:**
```
udp://host:port
```

**Configuration:**
```yaml
subchannels:
  - uid: 'udp_stream'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'udp://239.1.2.3:5001'
```

### UDP Unicast

**Point-to-point streaming** between one sender and one receiver.

**Receiver configuration:**
```yaml
input: 'udp://0.0.0.0:5001'  # Listen on all interfaces
# or
input: 'udp://192.168.1.100:5001'  # Specific interface
```

**Sender (encoder):**
```bash
# Send MPEG Layer II audio
ffmpeg -re -i input.wav \
  -c:a mp2 -ar 48000 -b:a 128k \
  -f mp2 udp://192.168.1.100:5001

# Send HE-AAC audio (DAB+)
ffmpeg -re -i input.wav \
  -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 \
  -f adts udp://192.168.1.100:5001
```

**Use cases:**
- Single encoder to single multiplexer
- Simple streaming setups
- Local network streaming

### UDP Multicast

**One-to-many streaming** from one sender to multiple receivers.

**Receiver configuration:**
```yaml
input: 'udp://239.1.2.3:5001'  # Multicast group
```

**Multicast address ranges:**
- **239.0.0.0 - 239.255.255.255:** Organization-local scope
- **239.1.2.0 - 239.1.2.255:** Recommended for DAB streaming

**Sender (encoder):**
```bash
# Send to multicast group
ffmpeg -re -i input.wav \
  -c:a mp2 -ar 48000 -b:a 128k \
  -f mp2 udp://239.1.2.3:5001?ttl=2
```

**TTL (Time To Live):**
- `1`: Same subnet only
- `2`: Same building/site
- `32`: Same organization
- `64`: Same region
- `128`: Same continent
- `255`: Global

**Use cases:**
- One encoder feeding multiple multiplexers
- Redundant receiver systems
- Distribution networks
- Large-scale deployments

### UDP Advantages

✅ **Low latency:** 1-10ms typical
✅ **Multicast support:** One-to-many distribution
✅ **Network efficient:** No connection overhead
✅ **Simple protocol:** Easy to implement and debug

### UDP Limitations

❌ **No delivery guarantee:** Packets can be lost
❌ **No error correction:** Lost packets = audio gaps
❌ **Sensitive to network issues:** Jitter, congestion affect quality
❌ **Firewall complexity:** Often blocked by default

---

## TCP Inputs

### Basic Configuration

**URI format:**
```
tcp://host:port
```

**Configuration:**
```yaml
subchannels:
  - uid: 'tcp_stream'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'tcp://192.168.1.100:5002'
```

### TCP Streaming

**Connection-oriented** with guaranteed delivery.

**Receiver configuration:**
```yaml
input: 'tcp://0.0.0.0:5002'  # Listen on all interfaces
# or
input: 'tcp://192.168.1.100:5002'  # Specific interface
```

**Sender (encoder):**
```bash
# Send MPEG Layer II audio
ffmpeg -re -i input.wav \
  -c:a mp2 -ar 48000 -b:a 128k \
  -f mp2 tcp://192.168.1.100:5002

# Send HE-AAC audio (DAB+)
ffmpeg -re -i input.wav \
  -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 \
  -f adts tcp://192.168.1.100:5002
```

### TCP Advantages

✅ **Guaranteed delivery:** No packet loss
✅ **Error correction:** Automatic retransmission
✅ **Congestion control:** Adapts to network conditions
✅ **Firewall friendly:** Easier to configure than UDP multicast

### TCP Limitations

❌ **Higher latency:** 10-50ms typical (vs 1-10ms for UDP)
❌ **No multicast:** Point-to-point only
❌ **Head-of-line blocking:** One slow packet delays all
❌ **Connection overhead:** Requires connection management

---

## Network Setup

### Firewall Configuration

#### Linux (iptables)

**Allow UDP:**
```bash
# Allow incoming UDP on port 5001
sudo iptables -A INPUT -p udp --dport 5001 -j ACCEPT

# Allow outgoing UDP
sudo iptables -A OUTPUT -p udp --sport 5001 -j ACCEPT
```

**Allow TCP:**
```bash
# Allow incoming TCP on port 5002
sudo iptables -A INPUT -p tcp --dport 5002 -j ACCEPT

# Allow outgoing TCP
sudo iptables -A OUTPUT -p tcp --sport 5002 -j ACCEPT
```

**Allow multicast:**
```bash
# Allow IGMP (multicast group management)
sudo iptables -A INPUT -p igmp -j ACCEPT

# Allow multicast traffic
sudo iptables -A INPUT -d 239.0.0.0/8 -j ACCEPT
```

#### Linux (firewalld)

```bash
# Add UDP port
sudo firewall-cmd --add-port=5001/udp --permanent

# Add TCP port
sudo firewall-cmd --add-port=5002/tcp --permanent

# Reload
sudo firewall-cmd --reload
```

#### Windows

```powershell
# Allow UDP
netsh advfirewall firewall add rule name="DAB UDP" ^
  protocol=UDP dir=in localport=5001 action=allow

# Allow TCP
netsh advfirewall firewall add rule name="DAB TCP" ^
  protocol=TCP dir=in localport=5002 action=allow
```

### Router Configuration

**Port forwarding (if multiplexer behind NAT):**
1. Access router admin interface
2. Navigate to Port Forwarding
3. Forward external UDP 5001 → internal 192.168.1.100:5001
4. Forward external TCP 5002 → internal 192.168.1.100:5002

**Multicast routing:**
```bash
# Enable multicast routing on Linux
sudo route add -net 239.0.0.0 netmask 255.0.0.0 dev eth0

# View multicast routes
netstat -g
```

### Network Interface Selection

**Bind to specific interface:**

python-dabmux automatically selects best interface, but you can specify:

```yaml
# Listen on specific IP
input: 'udp://192.168.1.100:5001'

# Listen on all interfaces
input: 'udp://0.0.0.0:5001'
```

---

## Bandwidth Requirements

### Calculate Bandwidth

**Formula:**
```
Required bandwidth = Bitrate × 1.1
```

The 1.1 multiplier accounts for:
- Protocol overhead (UDP/TCP headers)
- IP overhead
- Ethernet overhead
- ~10% safety margin

### Examples

| Audio Bitrate | Protocol | Required Bandwidth |
|---------------|----------|-------------------|
| 48 kbps | UDP | ~53 kbps |
| 64 kbps | TCP | ~70 kbps |
| 128 kbps | UDP | ~141 kbps |
| 192 kbps | TCP | ~211 kbps |

### Multiple Streams

```yaml
# 3 streams example
subchannels:
  - input: 'udp://239.1.2.3:5001'  # 128 kbps
  - input: 'udp://239.1.2.4:5002'  # 64 kbps
  - input: 'tcp://192.168.1.100:5003'  # 72 kbps

# Total bandwidth: (128 + 64 + 72) × 1.1 = 290 kbps
```

### Network Capacity Planning

**100 Mbps network:** Can handle ~700 audio streams at 128 kbps
**1 Gbps network:** Can handle ~7000 audio streams at 128 kbps

*In practice, limited by CPU and I/O before network saturation.*

---

## Buffering and Jitter

### Buffer Configuration

python-dabmux uses automatic buffering:

- **UDP:** ~100ms buffer (compensates for jitter)
- **TCP:** ~50ms buffer (less jitter due to reliable delivery)

### Jitter Tolerance

**Jitter:** Variation in packet arrival times

**UDP tolerates:**
- ≤ 50ms jitter: Excellent
- 50-100ms jitter: Good (may hear occasional glitches)
- > 100ms jitter: Poor (frequent glitches)

**TCP handles jitter better** due to automatic retransmission.

### Underrun Handling

**If network input stalls:**
1. Buffer drains
2. Multiplexer logs warning: `WARNING: Input underrun`
3. **Silence inserted** to maintain ETI frame timing
4. Normal playout resumes when data arrives

---

## Live Streaming Setup

### Complete Example

**Encoder machine (192.168.1.50):**

```bash
# Stream 1: Music (128 kbps MPEG)
ffmpeg -re -f alsa -i hw:0 \
  -c:a mp2 -ar 48000 -b:a 128k \
  -f mp2 udp://239.1.2.3:5001 &

# Stream 2: News (64 kbps AAC)
ffmpeg -re -f alsa -i hw:1 \
  -c:a aac -ar 48000 -b:a 64k -profile:a aac_he_v2 \
  -f adts udp://239.1.2.4:5002 &

# Stream 3: Talk (48 kbps AAC via TCP)
ffmpeg -re -f alsa -i hw:2 \
  -c:a aac -ar 48000 -b:a 48k -profile:a aac_he_v2 \
  -f adts tcp://192.168.1.100:5003 &
```

**Multiplexer machine (192.168.1.100):**

`network_live.yaml`:
```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'Live Network'

subchannels:
  - uid: 'music'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 3  # Higher protection for network
    input: 'udp://239.1.2.3:5001'

  - uid: 'news'
    id: 1
    type: 'dabplus'
    bitrate: 64
    start_address: 100
    protection:
      level: 2
    input: 'udp://239.1.2.4:5002'

  - uid: 'talk'
    id: 2
    type: 'dabplus'
    bitrate: 48
    start_address: 200
    protection:
      level: 2
    input: 'tcp://0.0.0.0:5003'

services:
  - uid: 'music_svc'
    id: '0x5001'
    label:
      text: 'Live Music'
    pty: 10
    language: 9

  - uid: 'news_svc'
    id: '0x5002'
    label:
      text: 'Live News'
    pty: 1
    language: 9

  - uid: 'talk_svc'
    id: '0x5003'
    label:
      text: 'Live Talk'
    pty: 9
    language: 9

components:
  - uid: 'music_comp'
    service_id: '0x5001'
    subchannel_id: 0

  - uid: 'news_comp'
    service_id: '0x5002'
    subchannel_id: 1

  - uid: 'talk_comp'
    service_id: '0x5003'
    subchannel_id: 2
```

**Run multiplexer:**
```bash
python -m dabmux.cli -c network_live.yaml -o live.eti --continuous
```

---

## Monitoring and Debugging

### Check Network Connectivity

**Test UDP reception:**
```bash
# Listen for UDP packets (netcat)
nc -u -l 5001 | hexdump -C

# Or tcpdump
sudo tcpdump -i eth0 udp port 5001 -X
```

**Test TCP connection:**
```bash
# Listen for TCP connection
nc -l 5002

# Connect to test
telnet 192.168.1.100 5002
```

### Monitor Multicast Traffic

```bash
# View multicast group memberships
netstat -g

# Capture multicast traffic
sudo tcpdump -i eth0 'dst net 239.0.0.0/8' -vv

# Test multicast join
sudo ip maddr add 239.1.2.3 dev eth0
```

### Network Statistics

**Enable verbose logging:**
```bash
python -m dabmux.cli -c config.yaml -o output.eti -v
```

**Statistics shown:**
- Packets received
- Bytes received
- Buffer fill level
- Underrun count
- Network errors

**Example output:**
```
INFO: Input 'music': 48523 packets, 62283776 bytes received
INFO: Input 'music': Buffer fill: 75%
INFO: Input 'news': 0 underruns detected
```

---

## Troubleshooting

### No Data Received

**Problem:**
```
WARNING: Input timeout, inserting silence
ERROR: No data received from udp://239.1.2.3:5001
```

**Diagnosis:**
```bash
# Test if packets arriving
sudo tcpdump -i eth0 udp port 5001

# Check firewall
sudo iptables -L -n | grep 5001

# Test connectivity
nc -u 192.168.1.100 5001 < test.mp2
```

**Solutions:**
1. Check encoder is running and sending
2. Verify firewall allows UDP/TCP
3. Confirm network connectivity
4. Test with simpler setup first

### Packet Loss / Audio Glitches

**Problem:**
```
WARNING: Input underrun detected
```

**Diagnosis:**
```bash
# Check packet loss
ping 192.168.1.50
# Look for packet loss %

# Monitor network errors
netstat -s | grep error

# Check interface errors
ifconfig eth0 | grep error
```

**Solutions:**
1. **Use TCP instead of UDP** (guaranteed delivery)
2. **Increase protection level** (compensates for bit errors)
3. **Reduce network load** (eliminate competing traffic)
4. **Use dedicated network** (separate from general traffic)
5. **Check physical layer** (cables, switches, NICs)

### Multicast Not Working

**Problem:** Multicast UDP not received

**Diagnosis:**
```bash
# Check IGMP support
cat /proc/net/igmp

# Test multicast join
sudo ip maddr add 239.1.2.3 dev eth0
sudo tcpdump -i eth0 'dst 239.1.2.3'
```

**Solutions:**
1. **Enable IGMP on router:**
   ```bash
   # Linux router
   sudo sysctl -w net.ipv4.conf.all.mc_forwarding=1
   ```

2. **Add multicast route:**
   ```bash
   sudo route add -net 239.0.0.0 netmask 255.0.0.0 dev eth0
   ```

3. **Join multicast group explicitly:**
   ```bash
   sudo ip maddr add 239.1.2.3 dev eth0
   ```

### High Latency

**Problem:** Noticeable delay in audio

**TCP typical:** 10-50ms
**UDP typical:** 1-10ms

**If higher:**

**Solutions:**
1. **Use UDP instead of TCP** (lower latency)
2. **Reduce network hops** (use direct connection)
3. **Check network congestion** (use QoS)
4. **Disable Nagle algorithm** (TCP optimization)

### Connection Drops (TCP)

**Problem:** TCP connection lost

**Solutions:**
1. **Use TCP keepalive:**
   ```bash
   # Linux: Enable TCP keepalive
   sysctl -w net.ipv4.tcp_keepalive_time=60
   ```

2. **Monitor connection:**
   ```bash
   netstat -tn | grep 5002
   ```

3. **Automatic reconnection:** Run encoder in loop
   ```bash
   while true; do
       ffmpeg -re -i input.wav ... tcp://192.168.1.100:5002
       echo "Connection lost, reconnecting in 5s..."
       sleep 5
   done
   ```

---

## Best Practices

### Protocol Selection

**Use UDP when:**
- ✅ Low latency required (live broadcasting)
- ✅ Multicast needed (multiple receivers)
- ✅ Network is reliable (minimal packet loss)
- ✅ Can tolerate occasional glitches

**Use TCP when:**
- ✅ Reliability critical (no audio gaps allowed)
- ✅ Network has packet loss
- ✅ Point-to-point only
- ✅ Latency not critical

### Network Design

1. **Dedicated network:** Separate streaming traffic from general network
2. **Managed switches:** Use VLANs for isolation
3. **Gigabit links:** Ensure sufficient bandwidth
4. **Redundancy:** Multiple network paths for failover
5. **QoS:** Prioritize streaming traffic

### Monitoring

1. **Log monitoring:** Watch for underruns and errors
2. **Network monitoring:** Use tools like Zabbix, Nagios
3. **Alerts:** Set up notifications for issues
4. **Statistics:** Track packet loss, latency, jitter

### Security

1. **Firewall:** Only open necessary ports
2. **VPN:** Use VPN for remote encoders
3. **Authentication:** Implement stream authentication (external)
4. **Encryption:** Use VPN or SSH tunnels for sensitive streams

---

## See Also

- [Input Sources Overview](index.md): All input types
- [File Inputs](file-inputs.md): File-based inputs
- [Audio Formats](audio-formats.md): Audio encoding guide
- [Network Streaming Tutorial](../../tutorials/network-streaming.md): Step-by-step guide
- [Troubleshooting](../../troubleshooting/network-issues.md): Network problem solving
