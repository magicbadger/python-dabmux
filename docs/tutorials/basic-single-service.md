# Tutorial: Basic Single Service

Create your first DAB multiplex with a single radio station in under 15 minutes.

**Difficulty:** Beginner
**Time:** 15 minutes

## What You'll Build

A minimal DAB ensemble with:
- One radio station: "Test Radio"
- 128 kbps MPEG Layer II audio
- File-based input
- ETI file output

## Prerequisites

- python-dabmux installed ([Installation Guide](../getting-started/installation.md))
- Basic command-line knowledge
- An MPEG Layer II audio file (`.mp2`)

## Step 1: Prepare Audio File

You need an MPEG Layer II audio file. If you don't have one, convert any audio file:

```bash
# Install ffmpeg if needed
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# Convert to MPEG Layer II
ffmpeg -i your_audio.wav -codec:a mp2 -b:a 128k -ar 48000 test_audio.mp2
```

**Verify the file:**
```bash
ffprobe test_audio.mp2
```

Expected output should show:
- Codec: mp2 (MPEG-1 Audio Layer II)
- Bitrate: 128 kbps
- Sample rate: 48000 Hz

## Step 2: Create Configuration File

Create a file named `single_service.yaml`:

```yaml
# Single Service DAB Configuration

ensemble:
  id: '0xCE01'                    # Unique ensemble ID
  ecc: '0xE1'                     # Extended Country Code (Germany)
  transmission_mode: 'I'           # Mode I (standard)
  label:
    text: 'Test Ensemble'
    short: 'Test'
  lto_auto: true                  # Automatic local time offset

subchannels:
  - uid: 'test_audio'             # Unique identifier
    id: 0                         # Subchannel ID
    type: 'audio'                 # DAB audio (MPEG Layer II)
    bitrate: 128                  # Must match audio file
    start_address: 0              # First subchannel starts at 0
    protection:
      level: 2                    # Moderate protection
      shortform: true
    input: 'file://test_audio.mp2'  # Path to your audio file

services:
  - uid: 'test_radio'
    id: '0x4001'                  # Service ID
    label:
      text: 'Test Radio'          # Station name (max 16 chars)
      short: 'Test'               # Short name (max 8 chars)
    pty: 1                        # Programme Type (1=News)
    language: 9                   # Language code (9=English)

components:
  - uid: 'test_component'
    service_id: '0x4001'          # Links to service above
    subchannel_id: 0              # Links to subchannel above
    type: 0                       # Audio component
```

## Step 3: Test Configuration

Before generating output, test that the configuration is valid:

```bash
python -m dabmux.cli -c single_service.yaml -o test.eti -n 1 -vvv
```

**What this does:**
- `-c single_service.yaml`: Load configuration
- `-o test.eti`: Output to file
- `-n 1`: Generate just 1 frame (test)
- `-vvv`: Verbose output for debugging

**Expected output:**
```
INFO: Loading configuration from single_service.yaml
INFO: Created ensemble 'Test Ensemble' (0xCE01)
INFO: Added service 'Test Radio' (0x4001)
INFO: Added subchannel 0: audio, 128 kbps, protection level 2
INFO: Starting multiplexer
INFO: Generated 1 frame(s)
INFO: Multiplexing complete
```

## Step 4: Generate ETI Frames

Now generate a meaningful amount of frames:

```bash
python -m dabmux.cli -c single_service.yaml -o output.eti -n 1000
```

**Frame calculation:**
- Mode I: 96 ms per frame
- 1000 frames = 96 seconds ≈ 1.6 minutes of audio

**Expected output:**
```
INFO: Loading configuration from single_service.yaml
INFO: Starting multiplexer
INFO: Generated 1000 frame(s)
INFO: Output written to output.eti
```

## Step 5: Verify Output

Check the generated ETI file:

```bash
# Check file size
ls -lh output.eti

# Expected size: ~6 MB (6000 bytes per frame × 1000 frames)
```

**Examine the file:**
```bash
# View first 64 bytes (should show ETI sync pattern)
hexdump -C output.eti | head -4
```

**Expected output:**
```
00000000  00 07 3a b6 c8 14 00 00  00 00 05 40 e3 8f ff ff  |..:........@....|
          └─SYNC─┘ └───FC──┘ └───STC──┘ └──EOH─┘
```

The first 4 bytes should be: `00 07 3A B6` (ETI sync pattern)

## Step 6: Generate More Frames

For longer content, generate more frames:

```bash
# Generate 10 minutes of audio (Mode I)
# 10 minutes = 600 seconds ≈ 6250 frames
python -m dabmux.cli -c single_service.yaml -o output_10min.eti -n 6250
```

**File size calculation:**
```
Frame size: ~6000 bytes
6250 frames × 6000 bytes = 37.5 MB
```

## Step 7: Experiment with Settings

### Change Station Name

Edit `single_service.yaml`:
```yaml
services:
  - uid: 'test_radio'
    id: '0x4001'
    label:
      text: 'My Cool Radio'    # Changed!
      short: 'MyCool'           # Changed!
```

Regenerate:
```bash
python -m dabmux.cli -c single_service.yaml -o output.eti -n 100
```

### Change Bitrate

Edit subchannel bitrate:
```yaml
subchannels:
  - uid: 'test_audio'
    bitrate: 192                # Higher quality (was 128)
```

**Important:** Make sure your audio file matches the new bitrate, or convert it:
```bash
ffmpeg -i test_audio.mp2 -codec:a mp2 -b:a 192k -ar 48000 test_audio_192.mp2
```

Update input path:
```yaml
    input: 'file://test_audio_192.mp2'
```

### Change Protection Level

Edit protection:
```yaml
subchannels:
  - uid: 'test_audio'
    protection:
      level: 3                  # Stronger (was 2)
```

Higher protection = more robust but uses more capacity.

## Testing Different Scenarios

### Continuous Operation

Loop the input file continuously:
```bash
python -m dabmux.cli -c single_service.yaml -o output.eti --continuous
```

Press `Ctrl+C` to stop.

### Different Output Formats

**Raw ETI:**
```bash
python -m dabmux.cli -c single_service.yaml -o output.eti -f raw -n 1000
```

**Framed ETI** (default, easiest to parse):
```bash
python -m dabmux.cli -c single_service.yaml -o output.eti -f framed -n 1000
```

**Streamed ETI** (with timestamps):
```bash
python -m dabmux.cli -c single_service.yaml -o output.eti -f streamed --tist -n 1000
```

## Troubleshooting

### Error: Input file not found

```
ERROR: Input file not found: test_audio.mp2
```

**Solution:**
- Check the file exists: `ls test_audio.mp2`
- Use absolute path: `input: 'file:///full/path/to/test_audio.mp2'`

### Error: Invalid MPEG frame header

```
ERROR: Invalid MPEG frame header
```

**Solution:**
- Verify file format: `ffprobe test_audio.mp2`
- Re-encode: `ffmpeg -i source.wav -codec:a mp2 -b:a 128k test_audio.mp2`

### Error: Configuration parse error

```
ERROR: YAML parse error
```

**Solution:**
- Check indentation (use spaces, not tabs)
- Verify hex values are quoted: `id: '0xCE01'`
- Check colons have spaces after them

### File size smaller than expected

**Problem:** Generated file is too small

**Solution:**
- Check if input audio file is long enough
- Input file loops when it reaches the end
- Use `--continuous` flag for infinite looping

## Understanding What Happened

Let's review what python-dabmux did:

1. **Loaded configuration**: Parsed `single_service.yaml`
2. **Created ensemble**: Set up "Test Ensemble" with ID 0xCE01
3. **Added service**: Created "Test Radio" service
4. **Configured subchannel**: Allocated 128 kbps audio stream
5. **Opened input**: Connected to `test_audio.mp2`
6. **Generated FIGs**: Created metadata (ensemble info, service labels, etc.)
7. **Multiplexed frames**: For each frame:
   - Read audio data from input
   - Generated FIGs
   - Assembled ETI frame (headers, FIC, MST, CRC)
   - Wrote to output file
8. **Closed files**: Clean shutdown

## Next Steps

Now that you have a working single-service multiplex:

### Add More Services

Continue to [Multi-Service Ensemble Tutorial](multi-service-ensemble.md) to learn how to add multiple radio stations.

### Try DAB+

Continue to [DAB+ Setup Tutorial](dab-plus-setup.md) for better quality at lower bitrates.

### Network Output

Continue to [Network Streaming Tutorial](network-streaming.md) to output EDI over the network.

### Learn More

- [Configuration Reference](../user-guide/configuration/index.md): All configuration options
- [CLI Reference](../user-guide/cli-reference.md): All command-line options
- [Basic Concepts](../getting-started/basic-concepts.md): DAB terminology

## Summary

Congratulations! You've created your first DAB multiplex. You learned:

- ✅ How to write a basic configuration file
- ✅ Running python-dabmux from the command line
- ✅ Generating ETI output files
- ✅ Verifying the output
- ✅ Experimenting with different settings

This is the foundation for all DAB multiplexing with python-dabmux!

## Complete Configuration Reference

Here's the complete working configuration for reference:

```yaml
ensemble:
  id: '0xCE01'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Test Ensemble'
    short: 'Test'
  lto_auto: true

subchannels:
  - uid: 'test_audio'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'file://test_audio.mp2'

services:
  - uid: 'test_radio'
    id: '0x4001'
    label:
      text: 'Test Radio'
      short: 'Test'
    pty: 1
    language: 9

components:
  - uid: 'test_component'
    service_id: '0x4001'
    subchannel_id: 0
    type: 0
```

**Save this as `single_service.yaml` and you're ready to multiplex!**
