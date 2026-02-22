# Quick Start Guide

Get your DAB/DAB+ multiplexer running in 5 minutes!

---

## Prerequisites

```bash
# Python 3.10 or higher
python3 --version

# Install dependencies
pip install -r requirements.txt
```

---

## Basic DAB+ Setup

### 1. Create Configuration File

Create `my_dab.yaml`:

```yaml
ensemble:
  id: 0xCE15
  ecc: 0xE1
  label:
    text: 'My DAB Station'
    short_text: 'MyDAB'
  transmission_mode: 'I'

  # Enable date/time
  datetime:
    enabled: true

subchannels:
  # Audio subchannel (48 kbps DAB+)
  - uid: 'audio_main'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file://path/to/audio.dabp'

services:
  - uid: 'my_service'
    id: 0x5001
    label:
      text: 'My Radio'
      short_text: 'MyRadio'
    pty: 10  # Pop Music
    language: 9  # English

components:
  - uid: 'audio_component'
    service_id: '0x5001'
    subchannel_id: 0
    label:
      text: 'Main Programme'
      short_text: 'Main'
```

### 2. Encode Audio

```bash
# Install odr-audioenc
# https://github.com/Opendigitalradio/ODR-AudioEnc

# Encode MP2 to DAB+
odr-audioenc -i input.mp2 -o audio.dabp -b 48 -r 48000
```

### 3. Generate ETI Output

```bash
python -m dabmux.cli -c my_dab.yaml -o output.eti -f raw
```

### 4. Verify Output

```bash
# Install etisnoop (optional but recommended)
# https://github.com/Opendigitalradio/etisnoop

etisnoop -i output.eti
```

---

## Common Scenarios

### Multi-Service DAB+

```yaml
subchannels:
  - uid: 'music'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file://music.dabp'

  - uid: 'news'
    id: 1
    type: 'dabplus'
    bitrate: 32
    protection: 'EEP_2A'
    input_uri: 'file://news.dabp'

services:
  - uid: 'music_service'
    id: 0x5001
    label:
      text: 'Music Channel'
      short_text: 'Music'

  - uid: 'news_service'
    id: 0x5002
    label:
      text: 'News Channel'
      short_text: 'News'

components:
  - uid: 'music_comp'
    service_id: '0x5001'
    subchannel_id: 0

  - uid: 'news_comp'
    service_id: '0x5002'
    subchannel_id: 1
```

### With MOT Slideshow

```yaml
subchannels:
  - uid: 'audio'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file://audio.dabp'

  # Add MOT subchannel
  - uid: 'slideshow'
    id: 1
    type: 'packet'
    bitrate: 16
    protection: 'EEP_2A'

services:
  - uid: 'my_service'
    id: 0x5001
    label:
      text: 'My Radio'

components:
  - uid: 'audio_comp'
    service_id: '0x5001'
    subchannel_id: 0

  # Add MOT component
  - uid: 'slideshow_comp'
    service_id: '0x5001'
    subchannel_id: 1
    is_packet_mode: true
    packet:
      address: 0
      ua_types:
        - type: 2  # MOT Slideshow
    carousel_enabled: true
    carousel_directory: '/path/to/images'
```

**Prepare images:**
```bash
mkdir -p /path/to/images
# Add JPEG images (320x240, < 50 KB each)
cp album_art.jpg /path/to/images/001_art.jpg
```

See [MOT Carousel Guide](MOT_CAROUSEL_GUIDE.md) for details.

### With Remote Control

```yaml
ensemble:
  # ... existing config ...

  remote_control:
    zmq_enabled: true
    zmq_bind: 'tcp://*:9000'
    telnet_enabled: true
    telnet_port: 9001
    auth_enabled: true
    auth_password: 'your_password_here'
```

**Connect via telnet:**
```bash
telnet localhost 9001
# Enter password when prompted
> get_statistics
> set_label my_component "Now Playing: New Song"
> help
```

**Connect via ZMQ (Python):**
```python
import zmq
import json

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:9000")

request = {
    "command": "get_statistics",
    "args": {},
    "auth": "your_password_here"
}
socket.send_json(request)
response = socket.recv_json()
print(response)
```

### With EDI Output

```yaml
ensemble:
  # ... existing config ...

  edi_output:
    enabled: true
    protocol: 'udp'
    destination: '192.168.1.100:12000'
    enable_pft: true
    pft_fec: 2
    enable_tist: true
```

**For TCP:**
```yaml
  edi_output:
    enabled: true
    protocol: 'tcp'
    destination: '192.168.1.100:12000'
    tcp_mode: 'client'  # or 'server'
```

---

## CLI Options

```bash
# Basic usage
python -m dabmux.cli -c config.yaml -o output.eti

# Options
-c, --config        Configuration file (YAML)
-o, --output        Output file (ETI)
-f, --format        Output format (raw, framed, streamed)
-n, --num-frames    Number of frames to generate (default: infinite)
--tist              Enable TIST timestamps
--edi               Enable EDI output
--verbose           Verbose logging
```

**Examples:**
```bash
# Generate 1000 frames
python -m dabmux.cli -c config.yaml -o output.eti -f raw -n 1000

# Continuous output with EDI
python -m dabmux.cli -c config.yaml -o output.eti --edi

# With timestamps
python -m dabmux.cli -c config.yaml -o output.eti --tist
```

---

## Testing Your Output

### With etisnoop

```bash
# Analyze ETI structure
etisnoop -i output.eti

# Check specific FIGs
etisnoop -i output.eti | grep "FIG 0/"

# Verify services
etisnoop -i output.eti | grep -i "service"
```

### With dablin (Audio Playback)

```bash
# Install dablin
# https://github.com/Opendigitalradio/dablin

# Play ETI file
dablin -f output.eti
```

### With Professional DAB Receiver

1. Feed ETI to DAB modulator
2. Transmit on appropriate frequency
3. Verify reception with professional receiver
4. Check:
   - Audio quality
   - Service labels
   - MOT slideshow (if enabled)
   - EPG data (if enabled)

---

## Common Issues

### "No input source"
**Solution:** Ensure input file exists and path is correct
```bash
ls -l /path/to/audio.dabp
```

### "Invalid protection level"
**Solution:** Use valid EEP levels: EEP_1A, EEP_2A, EEP_3A, EEP_4A, EEP_1B, EEP_2B, EEP_3B, EEP_4B

### "Audio not playing in dablin"
**Solution:** Check audio encoding format
```bash
# Re-encode with correct parameters
odr-audioenc -i input.mp2 -o audio.dabp -b 48 -r 48000 -c 2
```

### "MOT images not appearing"
**Solution:** See [MOT Carousel Guide](MOT_CAROUSEL_GUIDE.md) troubleshooting section

---

## Next Steps

- **[Configuration Reference](CONFIGURATION.md)** - Complete configuration guide
- **[MOT Carousel Guide](MOT_CAROUSEL_GUIDE.md)** - Add images and multimedia
- **[Remote Control Guide](REMOTE_CONTROL.md)** - Runtime control via ZMQ/Telnet
- **[EDI Output Guide](EDI_OUTPUT.md)** - IP-based distribution
- **[Examples](../examples/)** - More configuration examples

---

## Getting Help

- Check logs for error messages
- Use `--verbose` flag for detailed output
- See `TODO.md` for known limitations
- Report issues on GitHub (if applicable)

---

**Ready to broadcast!** 📻
