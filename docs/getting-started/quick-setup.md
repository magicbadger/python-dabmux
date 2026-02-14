# Quick Setup: Audio to Multiplexed Stream

Get from audio file to multiplexed DAB stream in **5 minutes**.

## What You Need

- Audio file (any format: WAV, MP3, FLAC, etc.)
- python-dabmux installed
- ffmpeg installed

---

## Method 1: File Output (Simplest)

### Step 1: Encode Audio (30 seconds)

```bash
# Convert your audio to DAB format (MPEG Layer II, 48 kHz)
ffmpeg -i yourmusic.mp3 -c:a mp2 -ar 48000 -b:a 128k audio.mp2
```

### Step 2: Create Config (1 minute)

Save as `quick.yaml`:

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'My DAB Stream'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    protection:
      level: 2
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'My Station'

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
```

### Step 3: Generate Stream (30 seconds)

```bash
# Generate ETI file (loops audio continuously)
python -m dabmux.cli -c quick.yaml -o stream.eti --continuous
```

**Done!** Your DAB multiplex is now generating in `stream.eti`.

Press Ctrl+C to stop.

---

## Method 2: Network Streaming (Live)

### Step 1: Same Audio Encoding

```bash
ffmpeg -i yourmusic.mp3 -c:a mp2 -ar 48000 -b:a 128k audio.mp2
```

### Step 2: Same Config

Use `quick.yaml` from above.

### Step 3: Stream to Network

```bash
# Stream to modulator at 192.168.1.100 port 12000
python -m dabmux.cli -c quick.yaml \
  --edi udp://192.168.1.100:12000 \
  --continuous
```

**Change `192.168.1.100:12000` to your modulator's IP and port.**

---

## Method 3: Live Audio Input

### Stream Directly from Microphone/Soundcard

**Step 1: Stream Audio with ffmpeg**

```bash
# Encode live audio and send to multiplexer via UDP
ffmpeg -f alsa -i hw:0 \
  -c:a mp2 -ar 48000 -b:a 128k \
  -f mp2 udp://127.0.0.1:5001
```

Replace `-f alsa -i hw:0` with your audio input:
- **Linux:** `-f alsa -i hw:0` (ALSA device 0)
- **macOS:** `-f avfoundation -i ":0"` (Audio device 0)
- **Windows:** `-f dshow -i audio="Microphone"`

**Step 2: Update Config for Network Input**

Save as `live.yaml`:

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'Live Stream'

subchannels:
  - uid: 'live_audio'
    id: 0
    type: 'audio'
    bitrate: 128
    protection:
      level: 2
    input: 'udp://127.0.0.1:5001'  # Receive from ffmpeg

services:
  - uid: 'live_service'
    id: '0x5001'
    label:
      text: 'Live Radio'

components:
  - uid: 'live_comp'
    service_id: '0x5001'
    subchannel_id: 0
```

**Step 3: Run Multiplexer**

```bash
# Output to network
python -m dabmux.cli -c live.yaml \
  --edi udp://192.168.1.100:12000 \
  --continuous
```

**Now you have live audio → DAB multiplex → transmitter!**

---

## Complete Example: Looped Music Stream

**Scenario:** Loop a music file and stream to transmitter.

```bash
# 1. Encode audio
ffmpeg -i music.mp3 -c:a mp2 -ar 48000 -b:a 128k music.mp2

# 2. Create config (quick.yaml above)

# 3. Stream with error correction (PFT)
python -m dabmux.cli -c quick.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 3 \
  --pft-fec-m 3 \
  --continuous
```

**Features:**
- ✅ Loops music.mp2 automatically
- ✅ Streams over network to modulator
- ✅ Reed-Solomon FEC (corrects packet loss)
- ✅ Runs until Ctrl+C

---

## Using DAB+ (More Efficient)

DAB+ uses ~50% less bandwidth for same quality!

### Step 1: Encode to HE-AAC v2

```bash
# DAB+ format (72 kbps ≈ 128 kbps DAB quality)
ffmpeg -i yourmusic.mp3 \
  -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 \
  audio.aac
```

### Step 2: Update Config

Change two lines in your config:

```yaml
subchannels:
  - uid: 'audio1'
    id: 0
    type: 'dabplus'          # ← Changed from 'audio'
    bitrate: 72              # ← Changed from 128
    protection:
      level: 2
    input: 'file://audio.aac'  # ← Changed from .mp2
```

### Step 3: Run Same Command

```bash
python -m dabmux.cli -c quick.yaml -o stream.eti --continuous
```

**Result:** Same quality, 44% less bandwidth!

---

## Command Reference

### Basic Commands

```bash
# File output (loops audio)
python -m dabmux.cli -c config.yaml -o output.eti --continuous

# Network output
python -m dabmux.cli -c config.yaml --edi udp://IP:PORT --continuous

# File + Network (both)
python -m dabmux.cli -c config.yaml -o output.eti \
  --edi udp://IP:PORT --continuous

# With error correction
python -m dabmux.cli -c config.yaml --edi udp://IP:PORT \
  --pft --pft-fec 3 --pft-fec-m 3 --continuous
```

### Audio Encoding Commands

```bash
# DAB (MPEG Layer II)
ffmpeg -i input.mp3 -c:a mp2 -ar 48000 -b:a 128k output.mp2

# DAB+ (HE-AAC v2) - Music
ffmpeg -i input.mp3 -c:a aac -ar 48000 -b:a 72k \
  -profile:a aac_he_v2 output.aac

# DAB+ - Speech
ffmpeg -i input.mp3 -c:a aac -ar 48000 -b:a 48k \
  -profile:a aac_he_v2 output.aac

# Live capture (Linux/ALSA)
ffmpeg -f alsa -i hw:0 -c:a mp2 -ar 48000 -b:a 128k \
  -f mp2 udp://127.0.0.1:5001
```

---

## Configuration Template

Save this as your template and customize:

```yaml
ensemble:
  id: '0xCE15'                    # Change to unique ID
  ecc: '0xE1'                     # 0xE1=Germany, 0xE2=UK, 0xF0=France
  label:
    text: 'YOUR NAME HERE'        # Max 16 characters
    short: 'SHORT'                # Max 8 characters

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'                 # or 'dabplus' for HE-AAC
    bitrate: 128                  # 128 for DAB, 72 for DAB+
    protection:
      level: 2                    # 0=weak, 2=normal, 4=strong
      shortform: true
    input: 'file://audio.mp2'     # or 'udp://IP:PORT'

services:
  - uid: 'service1'
    id: '0x5001'                  # Unique service ID
    label:
      text: 'STATION NAME'        # Max 16 characters
      short: 'STATION'            # Max 8 characters
    pty: 10                       # 1=News, 10=Pop, 14=Classical
    language: 9                   # 9=English, 8=German, 15=French

components:
  - uid: 'comp1'
    service_id: '0x5001'          # Match service id above
    subchannel_id: 0              # Match subchannel id above
    type: 0
```

---

## Troubleshooting

### "Input file not found"

**Error:** `ERROR: Input file not found: audio.mp2`

**Fix:** Use absolute path or check file exists:
```bash
ls -l audio.mp2
# If exists, use absolute path:
input: 'file:///full/path/to/audio.mp2'
```

### "Expected 48000 Hz, got 44100 Hz"

**Error:** Sample rate mismatch

**Fix:** Re-encode at 48 kHz:
```bash
ffmpeg -i input.mp2 -ar 48000 output.mp2
```

### "Type mismatch"

**Error:** `ERROR: Expected MPEG frame, got AAC`

**Fix:** Match file type to config:
- `.mp2` files → `type: 'audio'`
- `.aac` files → `type: 'dabplus'`

### Network stream not received

**Check:**
```bash
# Test if modulator is reachable
ping 192.168.1.100

# Test UDP port (send test data)
echo "test" | nc -u 192.168.1.100 12000

# Check firewall allows UDP port 12000
```

### Audio quality poor

**Solutions:**
1. **Increase bitrate:**
   - DAB: Try 160 or 192 kbps
   - DAB+: Try 80 or 96 kbps

2. **Better source:** Use lossless source (WAV, FLAC)

3. **Higher protection:**
   ```yaml
   protection:
     level: 3  # or 4 for maximum
   ```

---

## Next Steps

### Add More Stations

See [Multi-Service Tutorial](../tutorials/multi-service-ensemble.md) for adding multiple radio stations to one multiplex.

### Network Streaming

See [Network Streaming Tutorial](../tutorials/network-streaming.md) for detailed UDP/TCP setup, firewall configuration, and monitoring.

### Error Correction

See [PFT Tutorial](../tutorials/pft-with-fec.md) for Reed-Solomon FEC configuration and testing.

### Full Documentation

- [Configuration Reference](../user-guide/configuration/index.md) - All configuration options
- [Audio Formats](../user-guide/inputs/audio-formats.md) - Complete encoding guide
- [CLI Reference](../user-guide/cli-reference.md) - All command-line options
- [Troubleshooting](../troubleshooting/common-errors.md) - Common errors and solutions

---

## Production Checklist

Before going live:

- [ ] Test audio encoding quality (listen to encoded file)
- [ ] Verify configuration (test with `-n 100` for 100 frames)
- [ ] Check network connectivity (ping modulator)
- [ ] Enable verbose logging (`-v`) for monitoring
- [ ] Set up systemd service for auto-restart (Linux)
- [ ] Configure firewall rules (allow UDP port)
- [ ] Enable PFT with FEC for unreliable networks
- [ ] Set up monitoring/alerts
- [ ] Document your configuration
- [ ] Have backup audio files ready

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ AUDIO → DAB MULTIPLEX QUICK REFERENCE                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 1. ENCODE AUDIO                                          │
│    DAB:  ffmpeg -i in.mp3 -c:a mp2 -ar 48000 \         │
│                 -b:a 128k out.mp2                        │
│    DAB+: ffmpeg -i in.mp3 -c:a aac -ar 48000 \         │
│                 -b:a 72k -profile:a aac_he_v2 out.aac   │
│                                                          │
│ 2. CREATE CONFIG.YAML (see template above)              │
│                                                          │
│ 3. RUN MULTIPLEXER                                       │
│    File:    python -m dabmux.cli -c config.yaml \      │
│                    -o out.eti --continuous               │
│    Network: python -m dabmux.cli -c config.yaml \      │
│                    --edi udp://IP:PORT --continuous      │
│    + FEC:   Add --pft --pft-fec 3 --pft-fec-m 3        │
│                                                          │
│ BITRATES:                                                │
│   DAB Music:  128-192 kbps    DAB+ Music:  72-96 kbps   │
│   DAB Speech: 64-96 kbps      DAB+ Speech: 48-56 kbps   │
│                                                          │
│ SAMPLE RATE: Always 48000 Hz (48 kHz)                   │
└─────────────────────────────────────────────────────────┘
```

---

**You're now ready to create DAB multiplexes from any audio source!** 🎵📡

For detailed explanations and advanced features, see the [complete documentation](../index.md).
