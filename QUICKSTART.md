# Quick Start Guide

Get your first DAB multiplex running in 3 simple steps!

## Prerequisites

- Python 3.9 or later
- ffmpeg (for audio encoding)

## Step 1: Install

```bash
git clone https://github.com/yourusername/python-dabmux.git
cd python-dabmux
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Step 2: Create Audio

Create a test audio file in MPEG Layer II format:

```bash
# If you have a WAV file
ffmpeg -i yourfile.wav -c:a mp2 -ar 48000 -b:a 128k audio.mp2

# Or create a 10-second sine wave test tone (440 Hz)
ffmpeg -f lavfi -i "sine=frequency=440:duration=10" \
  -c:a mp2 -ar 48000 -b:a 128k audio.mp2
```

## Step 3: Create Configuration

Create a file named `config.yaml`:

```yaml
ensemble:
  id: '0xCE15'
  label:
    text: 'Test Ensemble'

subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    protection:
      level: 2
      shortform: true
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'Radio One'
    pty: 10      # Pop Music
    language: 9  # English

components:
  - uid: 'comp1'
    service_id: '0x5001'
    subchannel_id: 0
    type: 0
```

## Step 4: Run!

### Generate ETI File

```bash
python -m dabmux.cli -c config.yaml -o output.eti -n 100
```

This creates `output.eti` with 100 frames (~10 seconds).

### Check Output

```bash
ls -lh output.eti
# Should be: 100 frames × 6144 bytes = 614,400 bytes (~600 KB)
```

## Success! 🎉

You've created your first DAB multiplex! The `output.eti` file contains:

- 100 ETI frames (Ensemble Transport Interface)
- 1 radio station: "Radio One"
- 128 kbps MPEG Layer II audio
- Complete FIG metadata (ensemble info, labels, etc.)

## Next Steps

### Loop Your Audio (Continuous Mode)

```bash
# Generate continuously until Ctrl+C
python -m dabmux.cli -c config.yaml -o output.eti --continuous
```

The audio file will loop automatically.

### Stream Over Network (EDI)

```bash
# Stream to a modulator at 192.168.1.100
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --continuous
```

### Add Error Correction (PFT)

```bash
# Stream with Reed-Solomon FEC for lossy networks
python -m dabmux.cli -c config.yaml \
  --edi udp://192.168.1.100:12000 \
  --pft \
  --pft-fec 3 \
  --pft-fec-m 3 \
  --continuous
```

### Create Multiple Services

See `examples/multi_service_config.yaml` for a 4-station configuration.

## Common Issues

### "Input file not found: audio.mp2"

- Make sure `audio.mp2` is in the same directory as `config.yaml`
- Or use absolute path: `input: 'file:///full/path/to/audio.mp2'`

### "ffmpeg: command not found"

Install ffmpeg:
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` or `sudo yum install ffmpeg`
- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### "Expected 48000 Hz, got 44100 Hz"

Re-encode your audio at 48 kHz:

```bash
ffmpeg -i input.wav -ar 48000 -c:a mp2 -b:a 128k audio.mp2
```

## Learn More

**📚 Complete Documentation:** [docs/index.md](docs/index.md)

**Essential Guides:**
- [First Multiplex Tutorial](docs/getting-started/first-multiplex.md) - Detailed walkthrough
- [Configuration Reference](docs/user-guide/configuration/index.md) - All config options
- [Audio Formats Guide](docs/user-guide/inputs/audio-formats.md) - Encoding audio
- [Troubleshooting](docs/troubleshooting/common-errors.md) - Solve common errors

**Example Configurations:**
- `examples/basic_config.yaml` - Single service
- `examples/multi_service_config.yaml` - Multi-service ensemble

## Getting Help

- **Documentation:** [docs/index.md](docs/index.md)
- **FAQ:** [docs/faq.md](docs/faq.md)
- **Issues:** [GitHub Issues](https://github.com/yourusername/python-dabmux/issues)

---

**Now you're ready to build DAB multiplexes!** 🚀
