# Simple Examples - Quick Start

Get a DAB audio service running in minutes with these simple examples.

## Option 1: Using the Simple Script (Easiest!)

The `simple_loop.py` script handles everything automatically:
- Encodes your audio to the correct format
- Creates the configuration
- Runs the multiplexer

### Basic Usage

```bash
# Loop any audio file (mp3, wav, flac, etc.)
python simple_loop.py yourmusic.mp3
```

This creates `output.eti` with a looping audio service.

### Custom Station Name

```bash
python simple_loop.py yourmusic.mp3 --station-name "Rock FM"
```

### Custom Output File

```bash
python simple_loop.py yourmusic.mp3 --output mystream.eti
```

### Stream to Network

```bash
# Stream to modulator via UDP
python simple_loop.py yourmusic.mp3 --edi udp://192.168.1.100:12000
```

### All Options

```bash
python simple_loop.py yourmusic.mp3 \
  --station-name "My Radio" \
  --ensemble-name "My DAB Network" \
  --bitrate 160 \
  --output stream.eti
```

### Available Options

- `-s`, `--station-name` - Station name (max 16 chars)
- `-e`, `--ensemble-name` - Ensemble name (max 16 chars)
- `-b`, `--bitrate` - Audio bitrate: 64, 96, 128, 160, 192 kbps (default: 128)
- `-o`, `--output` - Output ETI file
- `--edi` - Stream to network (udp://host:port or tcp://host:port)
- `--keep-encoded` - Keep the encoded .mp2 file after exit

### Help

```bash
python simple_loop.py --help
```

---

## Option 2: Using Configuration File

If you prefer manual control or already have encoded audio:

### Step 1: Encode Audio (if needed)

```bash
# Encode to MPEG Layer II (DAB format)
ffmpeg -i yourmusic.mp3 -c:a mp2 -ar 48000 -b:a 128k audio.mp2
```

### Step 2: Edit Configuration

Edit `simple_config.yaml` and change this line:

```yaml
input: 'file://audio.mp2'  # Point to your audio file
```

Optionally customize:
- Station name (label → text)
- Ensemble name (ensemble → label → text)
- Bitrate (subchannels → bitrate)
- Programme type (services → pty)

### Step 3: Run Multiplexer

```bash
# Generate ETI file (loops continuously)
python -m dabmux.cli -c simple_config.yaml -o output.eti --continuous

# Stream to network
python -m dabmux.cli -c simple_config.yaml --edi udp://192.168.1.100:12000 --continuous

# Both file and network
python -m dabmux.cli -c simple_config.yaml \
  -o output.eti \
  --edi udp://192.168.1.100:12000 \
  --continuous
```

---

## What Each Method Does

### simple_loop.py Script

**Automatic:**
1. ✅ Checks for ffmpeg
2. ✅ Encodes audio to correct format
3. ✅ Generates configuration
4. ✅ Runs multiplexer
5. ✅ Cleans up temporary files

**Best for:** Quick testing, any audio format

### simple_config.yaml File

**Manual control:**
1. You encode audio
2. You edit configuration
3. You run multiplexer

**Best for:** Production use, custom configurations

---

## Examples

### Example 1: Quick Test with MP3

```bash
# Encode and loop a music file
python simple_loop.py mymusic.mp3
```

Output: `output.eti` (looping continuously)

### Example 2: Custom Radio Station

```bash
# Create "Jazz FM" station at 160 kbps
python simple_loop.py jazz.mp3 \
  --station-name "Jazz FM" \
  --bitrate 160 \
  --output jazz_stream.eti
```

### Example 3: Live Network Streaming

```bash
# Stream to modulator at 192.168.1.100
python simple_loop.py music.mp3 \
  --station-name "Live Radio" \
  --edi udp://192.168.1.100:12000
```

### Example 4: File + Network

```bash
# Archive to file AND stream to network
python -m dabmux.cli -c simple_config.yaml \
  -o archive.eti \
  --edi udp://192.168.1.100:12000 \
  --continuous
```

---

## Understanding the Output

When you run either method with `--continuous`, the multiplexer:

1. **Reads** your audio file
2. **Generates** ETI frames (6144 bytes each, every 96ms)
3. **Loops** audio automatically when it reaches the end
4. **Runs** until you press Ctrl+C

### ETI File

If outputting to file:
- **File size** grows continuously
- **Rate:** ~64 KB/second for Mode I
- **1 hour** ≈ 225 MB

**To stop:** Press Ctrl+C

### Network Streaming

If using `--edi`:
- Streams to modulator in real-time
- No file created (unless also using `-o`)
- **Bandwidth:** ~590 kbps (Mode I without PFT)

---

## Audio Encoding Tips

### DAB (MPEG Layer II)

**Best quality:**
```bash
ffmpeg -i input.wav -c:a mp2 -ar 48000 -b:a 192k output.mp2
```

**Standard quality:**
```bash
ffmpeg -i input.mp3 -c:a mp2 -ar 48000 -b:a 128k output.mp2
```

**Speech:**
```bash
ffmpeg -i speech.wav -c:a mp2 -ar 48000 -b:a 64k output.mp2
```

### DAB+ (HE-AAC v2) - More Efficient

If you want to use DAB+ instead:

**Encode:**
```bash
ffmpeg -i input.mp3 -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 output.aac
```

**Update config:**
```yaml
subchannels:
  - type: 'dabplus'    # Changed from 'audio'
    bitrate: 72        # Changed from 128
    input: 'file://output.aac'  # Changed from .mp2
```

**Quality equivalence:**
- 72 kbps DAB+ ≈ 128 kbps DAB (music)
- 48 kbps DAB+ ≈ 96 kbps DAB (speech)

---

## Troubleshooting

### "ffmpeg not found"

Install ffmpeg:
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`
- **Windows:** Download from https://ffmpeg.org/

### "Input file not found"

Check the file path:
```bash
ls -l yourmusic.mp3  # Should show the file
```

Use absolute path if needed:
```bash
python simple_loop.py /full/path/to/yourmusic.mp3
```

### "Expected 48000 Hz, got 44100 Hz"

Your audio isn't 48 kHz. Re-encode:
```bash
ffmpeg -i input.mp3 -ar 48000 -c:a mp2 -b:a 128k output.mp2
```

### "ModuleNotFoundError: No module named 'yaml'"

Install dependencies:
```bash
pip install pyyaml
```

Or install full package:
```bash
pip install -e ".[dev]"
```

### High CPU Usage

Normal! Continuous multiplexing processes audio in real-time.

To reduce CPU:
1. Use file output (not network)
2. Generate limited frames: `-n 1000` instead of `--continuous`

### Memory Usage

Memory should be stable (~50-100 MB). If growing:
- Stop and restart the multiplexer
- Check for disk space issues

---

## Next Steps

### Add More Services

See `examples/multi_service_config.yaml` for multiple stations.

### Network Streaming

See [Network Streaming Tutorial](docs/tutorials/network-streaming.md) for:
- Firewall configuration
- UDP vs TCP
- Error correction with PFT

### Advanced Configuration

See [Configuration Reference](docs/user-guide/configuration/index.md) for:
- All parameter options
- Protection levels
- Programme types
- Language codes

### Production Deployment

See [User Guide](docs/user-guide/index.md) for:
- Systemd service setup
- Monitoring
- Logging
- Backup strategies

---

## Quick Reference

```bash
# Simplest - any audio file
python simple_loop.py music.mp3

# Custom station name
python simple_loop.py music.mp3 -s "My Radio"

# Higher quality
python simple_loop.py music.mp3 -b 192

# Stream to network
python simple_loop.py music.mp3 --edi udp://192.168.1.100:12000

# Manual config file
python -m dabmux.cli -c simple_config.yaml -o out.eti --continuous
```

---

**You're now ready to create looping DAB audio services!** 🎵📡

For complete documentation, see [docs/index.md](docs/index.md).
