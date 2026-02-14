# Tutorial: Network Streaming

Stream audio over the network using UDP and TCP inputs for live broadcasting.

**Difficulty:** Intermediate
**Time:** 30 minutes

## What You'll Build

A live streaming setup with:
- UDP network input (multicast)
- TCP network input (reliable)
- Live audio encoding with ffmpeg
- Network troubleshooting skills

## Prerequisites

- Completed [Basic Single Service Tutorial](basic-single-service.md)
- ffmpeg installed
- Basic network knowledge

## Step 1: Understanding Network Inputs

### UDP (User Datagram Protocol)
- **Fast**: Low latency
- **Unreliable**: Packets can be lost
- **Multicast**: One stream to many receivers
- **Best for**: Local network, real-time streaming

### TCP (Transmission Control Protocol)
- **Reliable**: Guaranteed delivery
- **Slower**: Higher latency
- **Unicast**: One-to-one connection
- **Best for**: Reliability is critical

## Step 2: Create UDP Streaming Setup

###Configure UDP Input

Create `udp_stream.yaml`:

```yaml
ensemble:
  id: '0xCE20'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Live Stream'
    short: 'Live'
  lto_auto: true

subchannels:
  - uid: 'live_audio'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'udp://239.1.2.3:5001'  # UDP multicast address

services:
  - uid: 'live_service'
    id: '0x7001'
    label:
      text: 'Live Radio'
      short: 'Live'
    pty: 1
    language: 9

components:
  - uid: 'live_comp'
    service_id: '0x7001'
    subchannel_id: 0
    type: 0
```

### Stream Audio to UDP

In a separate terminal, start streaming:

```bash
ffmpeg -re -i music.wav \
  -codec:a mp2 -b:a 128k -ar 48000 \
  -f rtp rtp://239.1.2.3:5001
```

**Flags explained:**
- `-re`: Real-time mode (simulate live streaming)
- `-codec:a mp2`: MPEG Layer II codec
- `-b:a 128k`: 128 kbps bitrate
- `-ar 48000`: 48 kHz sample rate
- `-f rtp`: RTP protocol for UDP
- `rtp://239.1.2.3:5001`: Multicast destination

### Run Multiplexer

```bash
python -m dabmux.cli -c udp_stream.yaml -o live.eti --continuous
```

The multiplexer will receive UDP stream and multiplex it continuously.

## Step 3: Test UDP Multicast

### Check Network Configuration

```bash
# Linux/macOS: Check multicast routing
netstat -rn | grep 239

# Should show route for 239.x.x.x addresses
```

### Add Multicast Route (if needed)

```bash
# Linux
sudo route add -net 224.0.0.0 netmask 240.0.0.0 dev eth0

# macOS
sudo route add -net 224.0.0.0/4 -interface en0
```

### Monitor UDP Traffic

```bash
# Use tcpdump to see UDP packets
sudo tcpdump -i any udp port 5001 -n

# Should show packets flowing to 239.1.2.3:5001
```

## Step 4: Create TCP Streaming Setup

### Configure TCP Input

Create `tcp_stream.yaml`:

```yaml
ensemble:
  id: '0xCE21'
  label:
    text: 'TCP Stream'
    short: 'TCP'

subchannels:
  - uid: 'tcp_audio'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'tcp://192.168.1.100:5002'  # TCP connection

services:
  - uid: 'tcp_service'
    id: '0x7002'
    label:
      text: 'TCP Radio'
```

### Start TCP Server (netcat)

Stream to TCP socket:

```bash
# Method 1: Using netcat as TCP server
ffmpeg -re -i music.wav -codec:a mp2 -b:a 128k -ar 48000 -f mp2 - | \
  nc -l 5002
```

### Run Multiplexer (connects to TCP)

```bash
python -m dabmux.cli -c tcp_stream.yaml -o tcp_live.eti --continuous
```

python-dabmux connects to the TCP server and receives audio.

## Step 5: Live Encoding Pipeline

### Complete Live Pipeline

```bash
# Terminal 1: Capture live audio and stream
ffmpeg -f alsa -i hw:0 \
  -codec:a mp2 -b:a 128k -ar 48000 \
  -f rtp rtp://239.1.2.3:5001

# Terminal 2: Multiplex the stream
python -m dabmux.cli -c udp_stream.yaml -o live.eti --continuous

# Terminal 3: Monitor output
watch -n 1 ls -lh live.eti
```

**On macOS (use different audio input):**
```bash
ffmpeg -f avfoundation -i ":0" \
  -codec:a mp2 -b:a 128k -ar 48000 \
  -f rtp rtp://239.1.2.3:5001
```

## Step 6: Multiple Network Inputs

Mix file and network inputs:

```yaml
subchannels:
  # Network input
  - uid: 'live1'
    id: 0
    input: 'udp://239.1.2.3:5001'

  # File input
  - uid: 'backup'
    id: 1
    input: 'file://backup.mp2'
```

## Network Input Best Practices

### Buffer Management

Network inputs have internal buffering. python-dabmux handles:
- **Underruns**: When network is slow
- **Overruns**: When network is fast
- **Jitter**: Variable packet timing

### Firewall Configuration

```bash
# Allow UDP port (Linux/ufw)
sudo ufw allow 5001/udp

# Allow TCP port
sudo ufw allow 5002/tcp
```

### Bandwidth Calculation

For 128 kbps audio:
- Network bandwidth needed: ~150 kbps (with overhead)
- Packet rate: ~100-200 packets/second
- Latency: <100ms typical

## Troubleshooting

### No audio from UDP input

**Check streaming is active:**
```bash
nc -u 239.1.2.3 5001
# Should receive data
```

**Check multicast routing:**
```bash
netstat -g  # Show multicast groups
```

**Solution:** Start ffmpeg streaming first, then multiplexer.

### TCP connection refused

**Error:**
```
ERROR: Connection refused: 192.168.1.100:5002
```

**Solutions:**
1. Start TCP server first (nc -l 5002)
2. Check IP address is correct
3. Check firewall allows port

### Packet loss

**Symptoms:** Audio dropouts, underruns

**Solutions:**
1. Use TCP instead of UDP
2. Reduce network congestion
3. Use wired instead of wireless
4. Increase encoding bitrate margin

### High latency

**Problem:** Delay between input and output

**Solutions:**
1. Use UDP (lower latency than TCP)
2. Reduce buffer sizes
3. Use local network (not Internet)

## EDI Network Output

Combine network input with EDI output:

```bash
# Receive UDP, output EDI to network
python -m dabmux.cli \
  -c udp_stream.yaml \
  --edi udp://239.2.3.4:12000 \
  --continuous
```

Complete network-to-network pipeline!

## Next Steps

### Add PFT for Reliability

Continue to [PFT with FEC Tutorial](pft-with-fec.md) to add error correction.

### Monitor Network Performance

Use tools like:
- `iftop`: Monitor bandwidth
- `tcpdump`: Capture packets
- `netstat`: Check connections

## Summary

You've learned network streaming:

- ✅ UDP multicast inputs
- ✅ TCP reliable inputs
- ✅ Live audio encoding
- ✅ Network troubleshooting
- ✅ Firewall configuration

Network inputs enable live broadcasting with python-dabmux!

## Quick Commands

```bash
# Stream to UDP multicast
ffmpeg -re -i audio.wav -codec:a mp2 -b:a 128k -f rtp rtp://239.1.2.3:5001

# Multiplex UDP input
python -m dabmux.cli -c udp_config.yaml -o output.eti --continuous

# Stream to TCP
ffmpeg -re -i audio.wav -codec:a mp2 -b:a 128k -f mp2 - | nc -l 5002

# Multiplex TCP input
python -m dabmux.cli -c tcp_config.yaml -o output.eti --continuous
```
