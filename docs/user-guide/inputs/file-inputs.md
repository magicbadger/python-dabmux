# File Inputs

Complete guide to using file-based inputs for audio and data streams.

## Overview

File inputs read pre-recorded audio or data from files on disk. They're the simplest input type and ideal for testing, scheduled programming, and looped playout.

**URI format:**
```
file://path/to/file.ext
```

---

## Basic Configuration

### Relative Path

```yaml
subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'file://audio.mp2'
```

Relative to current working directory where dabmux is run.

### Absolute Path (Linux/macOS)

```yaml
subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'file:///home/user/dab/audio.mp2'
```

Note the three slashes: `file:///` (protocol + absolute path)

### Absolute Path (Windows)

```yaml
subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'file://C:/Users/user/dab/audio.mp2'
```

Use forward slashes even on Windows.

---

## Supported File Formats

### MPEG Layer II Files (.mp2)

**For:** DAB audio subchannels

**Subchannel configuration:**
```yaml
type: 'audio'
input: 'file://audio.mp2'
```

**Requirements:**
- Format: MPEG-1 Audio Layer II
- Sample rate: 48000 Hz
- Bitrate: Must match subchannel bitrate
- Channels: Stereo (2 channels) or mono

**Creating MPEG files:**
```bash
# Stereo at 128 kbps
ffmpeg -i input.wav -c:a mp2 -ar 48000 -b:a 128k output.mp2

# Mono at 64 kbps
ffmpeg -i input.wav -c:a mp2 -ar 48000 -ac 1 -b:a 64k output.mp2

# Specific quality
ffmpeg -i input.wav -c:a mp2 -ar 48000 -b:a 160k -q:a 0 output.mp2
```

### HE-AAC Files (.aac)

**For:** DAB+ audio subchannels

**Subchannel configuration:**
```yaml
type: 'dabplus'
input: 'file://audio.aac'
```

**Requirements:**
- Format: HE-AAC v2
- Sample rate: 48000 Hz
- Bitrate: Must match subchannel bitrate
- Profile: aac_he_v2

**Creating AAC files:**
```bash
# Standard quality (72 kbps)
ffmpeg -i input.wav -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 output.aac

# Speech (48 kbps)
ffmpeg -i input.wav -c:a aac -ar 48000 -b:a 48k -profile:a aac_he_v2 output.aac

# Premium (96 kbps)
ffmpeg -i input.wav -c:a aac -ar 48000 -b:a 96k -profile:a aac_he_v2 output.aac
```

### Raw Binary Data (.bin)

**For:** Data subchannels

**Subchannel configuration:**
```yaml
type: 'packet'  # or 'data'
input: 'file://data.bin'
```

**Requirements:**
- Raw binary format
- Bitrate must be specified
- Data rate must match subchannel bitrate

---

## File Validation

python-dabmux validates file inputs:

### Format Validation

```bash
# Test configuration with validation
python -m dabmux.cli -c config.yaml -o /dev/null -n 1
```

**Checks performed:**
1. File exists and readable
2. Format matches subchannel type (.mp2 for audio, .aac for dabplus)
3. Audio sample rate is 48 kHz
4. Bitrate matches configuration
5. File contains valid frames

### Common Validation Errors

**File not found:**
```
ERROR: Input file not found: audio.mp2
```
**Solution:** Check path, verify file exists

**Format mismatch:**
```
ERROR: Expected MPEG frame, got AAC superframe
```
**Solution:** Match file format to subchannel type

**Sample rate mismatch:**
```
ERROR: Expected 48000 Hz, got 44100 Hz
```
**Solution:** Re-encode at 48 kHz:
```bash
ffmpeg -i input.mp2 -ar 48000 output.mp2
```

**Bitrate mismatch:**
```
ERROR: File bitrate 192 kbps doesn't match configured 128 kbps
```
**Solution:** Re-encode at correct bitrate or update configuration

---

## Looping and Continuous Playout

### Single Run (Default)

```bash
python -m dabmux.cli -c config.yaml -o output.eti -n 1000
```

Generates 1000 frames then stops. File is read once.

### Continuous Mode

```bash
python -m dabmux.cli -c config.yaml -o output.eti --continuous
```

**Behavior:**
- Reads file from start to end
- **Automatically loops** when reaching EOF
- Continues until interrupted (Ctrl+C)
- No gaps between loops

**Use cases:**
- Test signal playout
- Scheduled programming loops
- Background music
- Emergency announcements

### Limited Duration

```bash
# Generate 5 minutes (3750 frames at 96ms each)
python -m dabmux.cli -c config.yaml -o output.eti -n 3750
```

---

## Multiple File Inputs

### Different File Types

```yaml
subchannels:
  # DAB music
  - uid: 'music_dab'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'file://music.mp2'

  # DAB+ news
  - uid: 'news_dabplus'
    id: 1
    type: 'dabplus'
    bitrate: 64
    input: 'file://news.aac'

  # DAB+ talk
  - uid: 'talk_dabplus'
    id: 2
    type: 'dabplus'
    bitrate: 48
    input: 'file://talk.aac'
```

All files loop independently in continuous mode.

### Organized Directory Structure

```
audio/
  ├── music/
  │   ├── station1.mp2
  │   └── station2.aac
  ├── news/
  │   └── news24.aac
  └── talk/
      └── talk.aac
```

**Configuration:**
```yaml
subchannels:
  - uid: 'station1'
    input: 'file://audio/music/station1.mp2'

  - uid: 'station2'
    input: 'file://audio/music/station2.aac'

  - uid: 'news'
    input: 'file://audio/news/news24.aac'
```

---

## File Management Best Practices

### Production Setup

1. **Absolute paths:** Always use absolute paths
   ```yaml
   input: 'file:///opt/dab/audio/station1.mp2'
   ```

2. **Dedicated directory:** Keep all audio files in one location
   ```
   /opt/dab/audio/
     ├── station1.mp2
     ├── station2.aac
     └── backup.mp2
   ```

3. **Backup files:** Have backup/failover files ready
   ```yaml
   # Primary
   input: 'file:///opt/dab/audio/live.mp2'

   # Backup (separate subchannel/service)
   input: 'file:///opt/dab/audio/backup.mp2'
   ```

4. **File permissions:** Ensure dabmux process can read files
   ```bash
   chmod 644 /opt/dab/audio/*.mp2
   chown dabmux:dabmux /opt/dab/audio/*
   ```

### Testing Setup

1. **Relative paths OK:** Fine for development
   ```yaml
   input: 'file://test_audio.mp2'
   ```

2. **Test files:** Keep separate test directory
   ```
   tests/audio/
     ├── test_128k.mp2
     ├── test_64k.aac
     └── test_48k.aac
   ```

3. **Short files:** Use short test files (30-60 seconds)
   ```bash
   # Create 30-second test file
   ffmpeg -i input.wav -t 30 -c:a mp2 -b:a 128k test.mp2
   ```

---

## File Preparation Workflow

### From WAV Source

```bash
# Step 1: Normalize audio
ffmpeg -i source.wav -af loudnorm normalized.wav

# Step 2: Encode to DAB format (MPEG Layer II)
ffmpeg -i normalized.wav -c:a mp2 -ar 48000 -b:a 128k output.mp2

# Step 3: Verify encoding
ffprobe output.mp2
```

### Batch Processing

```bash
#!/bin/bash
# Batch encode all WAV files to MPEG Layer II

for wav in *.wav; do
    base=$(basename "$wav" .wav)
    ffmpeg -i "$wav" -c:a mp2 -ar 48000 -b:a 128k "${base}.mp2"
done
```

### Quality Check

```bash
# Check file format
ffprobe -hide_banner audio.mp2

# Should show:
#   Audio: mp2, 48000 Hz, stereo, s16p, 128 kb/s

# Check duration
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 audio.mp2

# Playback test
ffplay audio.mp2
```

---

## Performance and Optimization

### File I/O Performance

- **Disk speed:** Not critical, even slow disks work fine
- **SSD vs HDD:** Both suitable, SSD offers lower latency
- **Network storage:** NFS/SMB works but add latency
- **Caching:** OS file cache handles repeated reads efficiently

### Memory Usage

- **Buffer per input:** ~100-500 KB
- **Multiple files:** Linear scaling
- **Example:** 10 file inputs ≈ 5 MB total

### CPU Usage

- **File reading:** Negligible CPU usage
- **Decoding:** None (raw MPEG/AAC frames used directly)
- **Bottleneck:** Usually ETI frame generation, not file I/O

---

## Advanced Usage

### Automatic Failover

Use external script to switch files on failure:

```bash
#!/bin/bash
# Simple failover script

PRIMARY="/opt/dab/audio/live.mp2"
BACKUP="/opt/dab/audio/backup.mp2"

# Monitor primary file
while true; do
    if [ ! -f "$PRIMARY" ]; then
        echo "Primary missing, using backup"
        ln -sf "$BACKUP" "$PRIMARY"
    fi
    sleep 10
done
```

### Dynamic File Updates

```bash
# Update audio file without stopping multiplexer
# 1. Write new file to temporary location
ffmpeg -i new_source.wav -c:a mp2 -b:a 128k /tmp/new.mp2

# 2. Atomically replace old file
mv /tmp/new.mp2 /opt/dab/audio/live.mp2

# Multiplexer will start reading new file on next loop
```

### Scheduled Programming

Use cron to switch content:

```bash
# crontab -e

# Morning show (6 AM)
0 6 * * * ln -sf /opt/dab/audio/morning.mp2 /opt/dab/audio/current.mp2

# Afternoon show (2 PM)
0 14 * * * ln -sf /opt/dab/audio/afternoon.mp2 /opt/dab/audio/current.mp2

# Evening show (7 PM)
0 19 * * * ln -sf /opt/dab/audio/evening.mp2 /opt/dab/audio/current.mp2
```

**Configuration:**
```yaml
input: 'file:///opt/dab/audio/current.mp2'  # Symlink
```

---

## Troubleshooting

### File Won't Play

**Problem:** File exists but multiplexer rejects it

**Diagnosis:**
```bash
# Check file format
ffprobe -hide_banner audio.mp2

# Expected for DAB:
# Stream #0:0: Audio: mp2, 48000 Hz, stereo, s16p, 128 kb/s

# Expected for DAB+:
# Stream #0:0: Audio: aac (HE-AACv2), 48000 Hz, stereo, fltp, 72 kb/s
```

**Solution:** Re-encode with correct parameters

### Clicks/Pops at Loop Point

**Problem:** Audible artifact when file loops

**Cause:** File doesn't start/end at zero crossing

**Solution:** Add fade in/out:
```bash
ffmpeg -i input.wav \
  -af "afade=t=in:st=0:d=0.1,afade=t=out:st=59.9:d=0.1" \
  -c:a mp2 -b:a 128k output.mp2
```

### File Updates Not Detected

**Problem:** Changed file but old version still playing

**Cause:** File changed mid-read; multiplexer has file handle open

**Solution:**
1. Use atomic move (mv) instead of overwriting
2. Restart multiplexer after file change
3. Use continuous mode with symlink switching

### Permission Denied

**Problem:**
```
ERROR: Cannot open file: Permission denied
```

**Solution:**
```bash
# Check file permissions
ls -l audio.mp2

# Fix permissions
chmod 644 audio.mp2

# If running as service, check user permissions
sudo -u dabmux ls -l audio.mp2
```

---

## Examples

### Single File Loop

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'Test Loop'

subchannels:
  - uid: 'loop'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'file://loop.mp2'

services:
  - uid: 'service'
    id: '0x5001'
    label:
      text: 'Test Signal'

components:
  - uid: 'comp'
    service_id: '0x5001'
    subchannel_id: 0
```

**Run:**
```bash
python -m dabmux.cli -c config.yaml -o test.eti --continuous
```

### Multi-File Production

```yaml
ensemble:
  id: '0xCE20'
  label:
    text: 'Production'

subchannels:
  - uid: 'main'
    id: 0
    type: 'audio'
    bitrate: 160
    input: 'file:///opt/dab/audio/main_160k.mp2'

  - uid: 'news'
    id: 1
    type: 'dabplus'
    bitrate: 64
    input: 'file:///opt/dab/audio/news_64k.aac'

  - uid: 'music'
    id: 2
    type: 'dabplus'
    bitrate: 80
    input: 'file:///opt/dab/audio/music_80k.aac'

services:
  - uid: 'main_svc'
    id: '0x5001'
    label:
      text: 'Main Station'

  - uid: 'news_svc'
    id: '0x5002'
    label:
      text: 'News 24/7'

  - uid: 'music_svc'
    id: '0x5003'
    label:
      text: 'Music Radio'

components:
  - uid: 'main_comp'
    service_id: '0x5001'
    subchannel_id: 0

  - uid: 'news_comp'
    service_id: '0x5002'
    subchannel_id: 1

  - uid: 'music_comp'
    service_id: '0x5003'
    subchannel_id: 2
```

---

## See Also

- [Input Sources Overview](index.md): All input types
- [Network Inputs](network-inputs.md): UDP/TCP streaming
- [Audio Formats](audio-formats.md): Complete encoding guide
- [Configuration Examples](../configuration/examples.md): More examples
- [Troubleshooting](../../troubleshooting/input-issues.md): Solving input problems
