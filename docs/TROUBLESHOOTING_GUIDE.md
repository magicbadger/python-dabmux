# Troubleshooting Guide

Complete guide to diagnosing and resolving common issues with the Python DAB Multiplexer.

---

## Table of Contents

1. [Audio Issues](#audio-issues)
2. [Configuration Problems](#configuration-problems)
3. [Network Issues](#network-issues)
4. [Performance](#performance)
5. [Debugging Tools](#debugging-tools)
6. [Common Errors](#common-errors)
7. [FAQ](#faq)

---

## Audio Issues

### No Audio Output

**Symptoms:**
- DAB receiver shows service but no sound
- dablin plays ETI but no audio
- etisnoop shows -90 dB (silence)

**Diagnosis:**

1. **Check input file exists:**
   ```bash
   ls -l /path/to/audio.dabp
   ```

2. **Verify audio data in ETI:**
   ```bash
   etisnoop -i output.eti | grep "audio level"
   # Should show dB levels > -90
   ```

3. **Check configuration:**
   ```yaml
   subchannels:
     - uid: 'audio_main'
       input_uri: 'file://path/to/audio.dabp'  # Must be absolute path
   ```

**Solutions:**

**Missing input file:**
```bash
# Check file path
ls -l "$(python3 -c 'import yaml; print(yaml.safe_load(open("config.yaml"))["subchannels"][0]["input_uri"].replace("file://", ""))')"
```

**Wrong file format:**
```bash
# Re-encode with odr-audioenc
odr-audioenc -i input.mp2 -o audio.dabp -b 48 -r 48000
```

**Input URI incorrect:**
```yaml
# Before (wrong):
input_uri: 'audio.dabp'  # Relative path

# After (correct):
input_uri: 'file:///full/path/to/audio.dabp'  # Absolute path
```

---

### Audio Distortion

**Symptoms:**
- Crackling or garbled audio
- Intermittent dropouts
- Audio cuts out periodically

**Diagnosis:**

1. **Check bitrate match:**
   ```bash
   ffprobe input.mp2 2>&1 | grep bitrate
   # Must match configuration
   ```

2. **Check protection level:**
   ```yaml
   subchannels:
     - bitrate: 48
       protection: 'EEP_3A'  # Must be valid
   ```

3. **Check subchannel size:**
   ```bash
   etisnoop -i output.eti | grep "SubCh"
   # Size should match bitrate
   ```

**Solutions:**

**Bitrate mismatch:**
```bash
# Configuration says 48 kbps, but file is 96 kbps
# Re-encode to match:
odr-audioenc -i input.mp2 -o audio.dabp -b 48 -r 48000
```

**Invalid protection level:**
```yaml
# Valid protection levels:
protection: 'EEP_1A'  # UEP not supported
protection: 'EEP_2A'
protection: 'EEP_3A'
protection: 'EEP_4A'
protection: 'EEP_1B'
protection: 'EEP_2B'
protection: 'EEP_3B'
protection: 'EEP_4B'
```

---

### MPEG CRC Warnings

**Symptoms:**
- dablin reports "(CRC)" errors
- Audio plays but shows warnings
- etisnoop shows MPEG frames without CRC

**Diagnosis:**

1. **Check MPEG frame headers:**
   ```bash
   python3 -c "
   import struct
   with open('audio.dabp', 'rb') as f:
       header = struct.unpack('>I', f.read(4))[0]
       protection_bit = (header >> 16) & 1
       print(f'Protection bit: {protection_bit}')
       print('CRC: ' + ('No' if protection_bit else 'Yes'))
   "
   ```

2. **Expected:** protection_bit = 0 (CRC present)
3. **Reality:** protection_bit = 1 (no CRC) - ffmpeg default

**Solution:**

**Accept the warnings (RECOMMENDED):**
- Audio plays correctly despite warnings
- CRC is for RF error detection, not required for file playback
- This is a limitation of the encoder, not the multiplexer

**OR re-encode with CRC-enabled encoder:**
```bash
# Option 1: toolame (if available)
toolame -e -b 96 -s 48 input.wav output.mp2

# Option 2: twolame
twolame --protect -b 96 -r input.wav output.mp2

# Option 3: Use DAB+ instead
odr-audioenc -i input.mp2 -o audio.dabp -b 48 -r 48000
# DAB+ uses Reed-Solomon FEC, not MPEG CRC
```

**Note:** Python DAB Multiplexer does NOT add MPEG CRC to existing frames (would corrupt audio structure).

---

### Audio Level Too Low/High

**Symptoms:**
- Audio barely audible
- Audio distorted/clipping
- Receiver shows low/high audio levels

**Diagnosis:**

```bash
# Check audio levels in ETI
etisnoop -i output.eti | grep "audio level"
```

**Solutions:**

**Normalize audio before encoding:**
```bash
# Analyze audio
ffmpeg -i input.mp2 -af volumedetect -f null -

# Output shows:
# mean_volume: -20.5 dB
# max_volume: -5.0 dB

# Normalize to -3 dB peak
ffmpeg -i input.mp2 -af "volume=+15dB" normalized.mp2

# Then encode for DAB
odr-audioenc -i normalized.mp2 -o audio.dabp -b 48 -r 48000
```

**For DAB+ (recommended):**
```bash
# Use built-in normalization
odr-audioenc -i input.mp2 -o audio.dabp -b 48 -r 48000 \
  --afterburner --aaclc --sbr --ps
```

---

## Configuration Problems

### YAML Syntax Errors

**Symptoms:**
- Multiplexer fails to start
- `yaml.scanner.ScannerError`
- `yaml.parser.ParserError`

**Common mistakes:**

**Indentation:**
```yaml
# Wrong:
ensemble:
id: 0xCE15  # Missing indent

# Correct:
ensemble:
  id: 0xCE15  # 2 spaces indent
```

**Quotes:**
```yaml
# Wrong:
label:
  text: My Radio's Station  # Apostrophe breaks parsing

# Correct:
label:
  text: "My Radio's Station"  # Use quotes
```

**Hex values:**
```yaml
# Wrong:
id: 0xCE15  # String, not number

# Correct:
id: '0xCE15'  # Quoted hex string
# OR
id: 52757     # Decimal equivalent
```

**Diagnosis:**

```bash
# Check YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

**Solution:**

Use YAML validator:
```bash
# Install yamllint
pip install yamllint

# Check file
yamllint config.yaml
```

---

### Invalid Protection Level

**Symptoms:**
- `ValueError: Invalid protection level`
- Subchannel size calculation fails

**Diagnosis:**

```yaml
subchannels:
  - protection: 'UEP_3'  # UEP not supported
```

**Solution:**

Use EEP (Equal Error Protection):
```yaml
subchannels:
  - protection: 'EEP_3A'  # A or B suffix required
```

**Valid levels:**
- `EEP_1A`, `EEP_2A`, `EEP_3A`, `EEP_4A`
- `EEP_1B`, `EEP_2B`, `EEP_3B`, `EEP_4B`

---

### Subchannel Conflicts

**Symptoms:**
- `ValueError: Subchannel ID conflict`
- Subchannels overlap

**Diagnosis:**

```yaml
subchannels:
  - uid: 'audio1'
    id: 0  # ❌ Duplicate ID
  - uid: 'audio2'
    id: 0  # ❌ Duplicate ID
```

**Solution:**

Use unique IDs:
```yaml
subchannels:
  - uid: 'audio1'
    id: 0  # ✅ Unique
  - uid: 'audio2'
    id: 1  # ✅ Unique
```

**Check ID range:** 0-63 for subchannels

---

### Service ID Conflicts

**Symptoms:**
- `ValueError: Service ID conflict`
- Services not appearing on receiver

**Diagnosis:**

```yaml
services:
  - uid: 'service1'
    id: '0x5001'  # ❌ Duplicate
  - uid: 'service2'
    id: '0x5001'  # ❌ Duplicate
```

**Solution:**

Use unique service IDs:
```yaml
services:
  - uid: 'service1'
    id: '0x5001'  # ✅ Unique
  - uid: 'service2'
    id: '0x5002'  # ✅ Unique
```

**Service ID ranges:**
- Audio: 0x0001 - 0xFFFF (16-bit)
- Data: 0x10000 - 0xFFFFFFFF (32-bit)

---

## Network Issues

### EDI Not Received

**Symptoms:**
- ODR-DabMod shows no input
- tcpdump shows no packets on modulator
- Multiplexer shows EDI enabled but no reception

**Diagnosis:**

1. **Check network connectivity:**
   ```bash
   ping 192.168.1.100
   ```

2. **Check firewall:**
   ```bash
   sudo iptables -L -n | grep 12000
   sudo ufw status
   ```

3. **Verify packets sent:**
   ```bash
   # On multiplexer
   sudo tcpdump -i eth0 udp port 12000
   ```

4. **Verify packets received:**
   ```bash
   # On modulator
   sudo tcpdump -i eth0 udp port 12000
   ```

**Solutions:**

**Firewall blocking:**
```bash
# Allow EDI traffic
sudo ufw allow 12000/udp

# OR iptables
sudo iptables -A INPUT -p udp --dport 12000 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 12000 -j ACCEPT
```

**Wrong interface:**
```yaml
# Bind to all interfaces
edi_output:
  protocol: 'udp'
  destination: '0.0.0.0:12000'  # Listen on all
```

**Multicast not working:**
```bash
# Join multicast group
sudo ip maddr add 239.255.1.1 dev eth0

# Check multicast routing
ip mroute show
```

---

### Remote Control Connection Refused

**Symptoms:**
- `telnet: Unable to connect: Connection refused`
- ZMQ socket timeout
- Multiplexer shows remote control disabled

**Diagnosis:**

1. **Check multiplexer running:**
   ```bash
   ps aux | grep dabmux
   ```

2. **Check remote control enabled:**
   ```yaml
   ensemble:
     remote_control:
       zmq_enabled: true
       telnet_enabled: true
   ```

3. **Check ports listening:**
   ```bash
   netstat -tuln | grep 9000
   netstat -tuln | grep 9001
   ```

**Solutions:**

**Enable remote control:**
```yaml
ensemble:
  remote_control:
    zmq_enabled: true
    zmq_bind: 'tcp://*:9000'
    telnet_enabled: true
    telnet_port: 9001
```

**Check firewall:**
```bash
sudo ufw allow 9000/tcp
sudo ufw allow 9001/tcp
```

**Bind to correct interface:**
```yaml
# Localhost only:
zmq_bind: 'tcp://127.0.0.1:9000'

# All interfaces:
zmq_bind: 'tcp://*:9000'
```

---

### ZMQ Timeout

**Symptoms:**
- `zmq.error.Again: Resource temporarily unavailable`
- ZMQ send/recv hangs

**Diagnosis:**

```python
import zmq
socket = zmq.Context().socket(zmq.REQ)
socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
socket.connect("tcp://localhost:9000")
```

**Solutions:**

**Set timeout:**
```python
socket.setsockopt(zmq.RCVTIMEO, 5000)  # Receive timeout
socket.setsockopt(zmq.SNDTIMEO, 5000)  # Send timeout
```

**Check multiplexer:**
```bash
# Verify multiplexer running
ps aux | grep dabmux

# Check ZMQ port
netstat -tuln | grep 9000
```

---

## Performance

### High CPU Usage

**Symptoms:**
- 100% CPU usage
- Multiplexer slow to respond
- Frame generation delays

**Diagnosis:**

```bash
# Check CPU usage
top -p $(pgrep -f dabmux)

# Profile with py-spy
pip install py-spy
sudo py-spy record -o profile.svg -- python -m dabmux.cli -c config.yaml -o output.eti -n 1000
```

**Solutions:**

**Reduce FIG update rate:**
```yaml
# Disable unnecessary FIGs
ensemble:
  datetime:
    enabled: false  # If not needed

services:
  - announcements:
      enabled: false  # If not using EAS
```

**Optimize input sources:**
```bash
# Use file inputs instead of network streams
input_uri: 'file://audio.dabp'  # Faster than udp://
```

**Increase frame buffer:**
```python
# In code (advanced)
mux.frame_buffer_size = 10  # Default: 5
```

---

### Memory Leaks

**Symptoms:**
- Memory usage grows over time
- Multiplexer crashes after hours/days
- System runs out of memory

**Diagnosis:**

```bash
# Monitor memory usage
while true; do
  ps aux | grep dabmux | awk '{print $6}'
  sleep 60
done

# Profile with memory_profiler
pip install memory_profiler
python -m memory_profiler dabmux/cli.py -c config.yaml -o output.eti -n 10000
```

**Solutions:**

**Update to latest version:**
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

**Restart periodically:**
```bash
# Systemd service with restart
[Service]
Restart=always
RestartSec=60
```

**Report issue:**
```bash
# Capture diagnostics
pip freeze > requirements.txt
python --version > version.txt
uname -a > system.txt

# Open GitHub issue with diagnostics
```

---

### Slow Frame Generation

**Symptoms:**
- Frame rate < 40 fps (DAB Mode I)
- ETI output lags behind real-time
- Warnings about timing

**Diagnosis:**

```bash
# Check frame generation rate
python -m dabmux.cli -c config.yaml -o output.eti --verbose -n 1000 | grep "fps"
```

**Solutions:**

**Reduce complexity:**
```yaml
# Fewer services
services: []  # Remove unused services

# Fewer FIG types
# Disable optional features
```

**Use faster hardware:**
- More CPU cores
- Faster disk I/O
- SSD instead of HDD

---

## Debugging Tools

### etisnoop

**Purpose:** Analyze ETI frames and FIG data

**Installation:**
```bash
git clone https://github.com/Opendigitalradio/etisnoop.git
cd etisnoop
mkdir build && cd build
cmake ..
make
sudo make install
```

**Usage:**
```bash
# Basic analysis
etisnoop -i output.eti

# Grep for specific FIGs
etisnoop -i output.eti | grep "FIG 0/1"

# Check audio levels
etisnoop -i output.eti | grep "audio level"

# Verify services
etisnoop -i output.eti | grep -i "service"
```

### dablin

**Purpose:** DAB/DAB+ audio player for testing

**Installation:**
```bash
sudo apt install dablin
```

**Usage:**
```bash
# Play ETI file
dablin -f output.eti

# Verbose output
dablin -f output.eti -v

# Select service
dablin -f output.eti -s 0x5001
```

### Verbose Logging

**Enable debug logging:**
```bash
python -m dabmux.cli -c config.yaml -o output.eti --verbose
```

**Or in code:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check specific modules:**
```python
import structlog
logger = structlog.get_logger('dabmux.fig')
logger.setLevel(logging.DEBUG)
```

### tcpdump (Network Debugging)

**Capture EDI traffic:**
```bash
# Capture to file
sudo tcpdump -i eth0 udp port 12000 -w edi.pcap

# Display live
sudo tcpdump -i eth0 udp port 12000 -A

# Filter by destination
sudo tcpdump -i eth0 dst 192.168.1.100 and udp port 12000
```

**Analyze with Wireshark:**
```bash
wireshark edi.pcap
```

---

## Common Errors

### "No input source"

**Error:**
```
ERROR: No input source for subchannel 'audio_main'
```

**Cause:** Input URI not configured or file doesn't exist

**Solution:**
```yaml
subchannels:
  - uid: 'audio_main'
    input_uri: 'file:///full/path/to/audio.dabp'  # Add this
```

### "Invalid FIG type"

**Error:**
```
ValueError: Invalid FIG type: 99
```

**Cause:** FIG type not implemented or configuration error

**Solution:**
```yaml
# Check FIG type is supported (see README for list)
# Implemented: FIG 0/0-0/24, 1/0-1/4, 2/1, 6/0-6/1
```

### "CRC mismatch"

**Error (in etisnoop):**
```
CRC mismatch: expected 0x1234, got 0x5678
```

**Cause:** Corrupted ETI frame or implementation bug

**Solution:**
1. Regenerate ETI file
2. Check for file corruption
3. Report bug if persistent

### "MST CRC mismatch"

**Error (in dablin):**
```
ignored ETI frame due to wrong (MST) CRC
```

**Cause:** MST data corrupted or frame length incorrect

**Solution:**
1. Verify Frame Length (FL) calculation
2. Check subchannel sizes match configuration
3. Regenerate ETI with `--format raw`

### "Authentication failed"

**Error:**
```
ERROR Authentication failed
```

**Cause:** Incorrect password for remote control

**Solution:**
```yaml
# Check password in config
ensemble:
  remote_control:
    auth_password: 'correct_password'

# Verify in client
client = DABMuxClient(password='correct_password')
```

---

## FAQ

### Q: Why no audio in dablin?

**A:** Check:
1. Input file exists and is correct format
2. Input URI uses absolute path: `file:///full/path/audio.dabp`
3. Audio file matches configured bitrate
4. Use `etisnoop` to verify audio data present (not -90 dB)

### Q: How to fix MPEG CRC warnings?

**A:** Either:
1. Accept warnings (audio plays correctly)
2. Re-encode with CRC-enabled encoder (toolame, twolame)
3. Use DAB+ instead (HE-AAC with Reed-Solomon FEC)

### Q: How many services can I have?

**A:** Maximum:
- Services: 64
- Subchannels: 64
- Components: Unlimited (but limited by subchannel count)

**Practical limit:** Depends on ensemble bitrate (typically 8-16 services for Mode I)

### Q: What's the difference between ETI formats?

**A:**
- **RAW:** Pure ETI frames, 6144 bytes, 0x55 padding (for etisnoop, dablin, modulators)
- **FRAMED:** Frame count header + 2-byte length prefixes (internal use)
- **STREAMED:** Length prefixes only (network streaming)

**Recommendation:** Use `--format raw` for all tools

### Q: How to enable dynamic labels ("Now Playing")?

**A:**
```yaml
components:
  - uid: 'my_component'
    dynamic_label:
      text: 'Now Playing: Artist - Song'
      charset: 2  # UTF-8
```

Then update via remote control:
```bash
telnet localhost 9001
> set_label my_component "New song title"
```

### Q: Why is FIC fill rate high?

**A:** Too many FIGs or services. Solutions:
1. Reduce number of services
2. Disable optional FIGs (EAS if not needed)
3. Reduce announcement types
4. Use shorter labels

### Q: How to test without real receiver?

**A:** Use software tools:
1. **dablin:** Audio playback from ETI
2. **etisnoop:** FIG and structure analysis
3. **ODR-DabMod:** Software modulation (with SDR)

### Q: What sample rate for DAB+?

**A:** **48 kHz** (required by DAB+ standard)

```bash
odr-audioenc -i input.mp2 -o audio.dabp -b 48 -r 48000
                                             # Must be 48000 Hz
```

---

## Getting Help

**Still having issues?**

1. **Check logs:**
   ```bash
   python -m dabmux.cli -c config.yaml -o output.eti --verbose 2>&1 | tee debug.log
   ```

2. **Verify with tools:**
   ```bash
   etisnoop -i output.eti > analysis.txt
   ```

3. **Check documentation:**
   - [Quick Start Guide](QUICK_START.md)
   - [Configuration Reference](CONFIGURATION_REFERENCE.md)
   - [Remote Control Guide](REMOTE_CONTROL_GUIDE.md)

4. **Report bugs:**
   - Include configuration file (redact passwords)
   - Include debug log
   - Include etisnoop output
   - Include system info (OS, Python version)

---

**Last Updated:** 2026-02-22

**Status:** Production Ready

For feature requests and bug reports, see project README for contact information.
