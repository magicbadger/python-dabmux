# Tutorial: DAB+ Setup

Set up DAB+ (HE-AAC v2) services for more efficient broadcasting with better quality at lower bitrates.

**Difficulty:** Intermediate
**Time:** 20 minutes

## What You'll Build

A DAB+ service that demonstrates:
- HE-AAC v2 audio encoding
- Optimal bitrate selection
- Quality comparison with DAB
- Capacity savings

## Why Use DAB+?

**DAB+ advantages:**
- **Better quality at low bitrates**: 48-72 kbps DAB+ ≈ 128 kbps DAB
- **More services**: Fit more stations in same bandwidth
- **Modern codec**: HE-AAC v2 is optimized for music and speech

**When to use DAB:**
- Very high bitrates (192+ kbps) where MPEG Layer II excels
- Compatibility with older receivers (pre-2010)

## Prerequisites

- python-dabmux installed
- ffmpeg with libfdk-aac support
- Understanding of [Basic Concepts](../getting-started/basic-concepts.md)

## Step 1: Install FFmpeg with FDK-AAC

### macOS

```bash
brew install ffmpeg --with-fdk-aac
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install ffmpeg libfdk-aac2
```

### Verify Installation

```bash
ffmpeg -codecs | grep libfdk_aac
```

Should show: `libfdk_aac` in the output.

## Step 2: Encode Audio to HE-AAC

Create DAB+ audio files at different bitrates:

### Music Content (72 kbps recommended)

```bash
ffmpeg -i music.wav \
  -codec:a libfdk_aac \
  -profile:a aac_he_v2 \
  -b:a 72k \
  -ar 48000 \
  music_dabplus_72.aac
```

### Speech/Talk Content (48 kbps recommended)

```bash
ffmpeg -i speech.wav \
  -codec:a libfdk_aac \
  -profile:a aac_he_v2 \
  -b:a 48k \
  -ar 48000 \
  speech_dabplus_48.aac
```

### High-Quality Music (96 kbps)

```bash
ffmpeg -i premium.wav \
  -codec:a libfdk_aac \
  -profile:a aac_he_v2 \
  -b:a 96k \
  -ar 48000 \
  premium_dabplus_96.aac
```

**Profile options:**
- `aac_he_v2`: HE-AAC v2 (best for DAB+)
- `aac_he`: HE-AAC v1 (also works)
- `aac_low`: AAC-LC (less efficient)

## Step 3: Create DAB+ Configuration

Create `dabplus_config.yaml`:

```yaml
ensemble:
  id: '0xDA8F'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'DAB+ Demo'
    short: 'DABplus'
  lto_auto: true

subchannels:
  # Music service - 72 kbps
  - uid: 'music_dabplus'
    id: 0
    type: 'dabplus'           # DAB+ type
    bitrate: 72
    start_address: 0
    protection:
      level: 2
      shortform: true
    input: 'file://music_dabplus_72.aac'

  # Speech service - 48 kbps
  - uid: 'speech_dabplus'
    id: 1
    type: 'dabplus'
    bitrate: 48
    start_address: 100
    protection:
      level: 2
      shortform: true
    input: 'file://speech_dabplus_48.aac'

services:
  - uid: 'music_service'
    id: '0x6001'
    label:
      text: 'Music Plus'
      short: 'Music+'
    pty: 10
    language: 9

  - uid: 'speech_service'
    id: '0x6002'
    label:
      text: 'Talk Plus'
      short: 'Talk+'
    pty: 1
    language: 9

components:
  - uid: 'music_comp'
    service_id: '0x6001'
    subchannel_id: 0
    type: 0

  - uid: 'speech_comp'
    service_id: '0x6002'
    subchannel_id: 1
    type: 0
```

## Step 4: Test DAB+ Output

Generate ETI frames:

```bash
python -m dabmux.cli -c dabplus_config.yaml -o dabplus.eti -n 1000
```

Verify both services multiplex correctly.

## Step 5: Compare DAB vs DAB+

Create comparison configs to see the difference.

### DAB Configuration (MPEG Layer II)

```yaml
subchannels:
  - uid: 'music_dab'
    type: 'audio'             # DAB (MPEG)
    bitrate: 128              # Need 128 kbps for good quality
```

### DAB+ Configuration (HE-AAC v2)

```yaml
subchannels:
  - uid: 'music_dabplus'
    type: 'dabplus'           # DAB+
    bitrate: 72               # Only 72 kbps for similar quality!
```

**Capacity savings:** 128 - 72 = 56 kbps saved per service!

## Bitrate Recommendations

### Music Content

| Quality | DAB (MPEG Layer II) | DAB+ (HE-AAC v2) |
|---------|---------------------|------------------|
| Acceptable | 96 kbps | 48 kbps |
| Good | 128 kbps | 64 kbps |
| Very Good | 160 kbps | 72 kbps |
| Excellent | 192 kbps | 80-96 kbps |
| Premium | 256 kbps | 96-128 kbps |

### Speech/Talk Content

| Quality | DAB | DAB+ |
|---------|-----|------|
| Acceptable | 64 kbps | 32 kbps |
| Good | 80 kbps | 40 kbps |
| Very Good | 96 kbps | 48 kbps |
| Excellent | 128 kbps | 56-64 kbps |

**Recommendation:** Use 48 kbps DAB+ for speech, 72 kbps DAB+ for music.

## Step 6: Build Efficient Ensemble

Create an ensemble with 6 services using DAB+:

```yaml
ensemble:
  id: '0xDA8F'
  label:
    text: 'Efficient DAB+'

subchannels:
  # 3 music services @ 72 kbps = 216 kbps
  - {uid: music1, id: 0, type: dabplus, bitrate: 72, start_address: 0, input: 'file://music1.aac'}
  - {uid: music2, id: 1, type: dabplus, bitrate: 72, start_address: 100, input: 'file://music2.aac'}
  - {uid: music3, id: 2, type: dabplus, bitrate: 72, start_address: 200, input: 'file://music3.aac'}

  # 3 talk services @ 48 kbps = 144 kbps
  - {uid: talk1, id: 3, type: dabplus, bitrate: 48, start_address: 300, input: 'file://talk1.aac'}
  - {uid: talk2, id: 4, type: dabplus, bitrate: 48, start_address: 400, input: 'file://talk2.aac'}
  - {uid: talk3, id: 5, type: dabplus, bitrate: 48, start_address: 500, input: 'file://talk3.aac'}

# Total: 360 kbps for 6 services
# With DAB, would need ~720 kbps for similar quality!
```

## Encoding Best Practices

### Sample Rate

Always use **48 kHz** for DAB+:

```bash
ffmpeg -i input.wav -codec:a libfdk_aac -profile:a aac_he_v2 -b:a 72k -ar 48000 output.aac
```

### Stereo vs Mono

For speech, consider mono to save bitrate:

```bash
# Stereo (default)
ffmpeg -i input.wav -codec:a libfdk_aac -b:a 48k output_stereo.aac

# Mono (half the bitrate)
ffmpeg -i input.wav -codec:a libfdk_aac -b:a 24k -ac 1 output_mono.aac
```

### VBR vs CBR

Use **CBR (Constant Bitrate)** for DAB:

```bash
ffmpeg -i input.wav -codec:a libfdk_aac -profile:a aac_he_v2 -b:a 72k output.aac
```

DAB requires constant bitrate for multiplexing.

## Troubleshooting

### FFmpeg doesn't have libfdk-aac

**Error:**
```
Unknown encoder 'libfdk_aac'
```

**Solution:** Install FFmpeg with FDK-AAC support or use alternative:

```bash
# Alternative: use native AAC encoder (lower quality)
ffmpeg -i input.wav -codec:a aac -b:a 72k -profile:a aac_he_v2 output.aac
```

### Audio quality issues

**Problem:** DAB+ audio sounds poor

**Solutions:**
1. Increase bitrate (try 80 or 96 kbps)
2. Check source audio quality
3. Use HE-AAC v2 profile: `-profile:a aac_he_v2`
4. Ensure sample rate is 48 kHz

### Type mismatch error

**Error:**
```
ERROR: Expected DAB+ superframe, got MPEG frame
```

**Solution:** Check `type` in config matches audio format:
- `.aac` files → `type: 'dabplus'`
- `.mp2` files → `type: 'audio'`

## Next Steps

### Add Network Inputs

Continue to [Network Streaming Tutorial](network-streaming.md) to stream DAB+ over the network.

### Mix DAB and DAB+

See [Multi-Service Ensemble Tutorial](multi-service-ensemble.md) for mixing both types.

### Deploy to Production

Read [User Guide](../user-guide/index.md) for production deployment best practices.

## Summary

You've learned DAB+ setup including:

- ✅ Encoding audio to HE-AAC v2
- ✅ Configuring DAB+ services
- ✅ Optimal bitrate selection
- ✅ Capacity management
- ✅ Quality comparison with DAB

DAB+ enables more services with better quality at lower bitrates!

## Quick Reference

### Encoding Commands

```bash
# Music (72 kbps)
ffmpeg -i music.wav -codec:a libfdk_aac -profile:a aac_he_v2 -b:a 72k -ar 48000 music.aac

# Speech (48 kbps)
ffmpeg -i speech.wav -codec:a libfdk_aac -profile:a aac_he_v2 -b:a 48k -ar 48000 speech.aac

# Premium (96 kbps)
ffmpeg -i premium.wav -codec:a libfdk_aac -profile:a aac_he_v2 -b:a 96k -ar 48000 premium.aac
```

### Configuration Template

```yaml
subchannels:
  - uid: 'dabplus_service'
    type: 'dabplus'           # Key: use 'dabplus' not 'audio'
    bitrate: 72               # Recommended for music
    input: 'file://audio.aac' # HE-AAC file
```
