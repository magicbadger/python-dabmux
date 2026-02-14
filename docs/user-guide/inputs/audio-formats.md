# Audio Formats

Complete guide to encoding audio for DAB and DAB+ broadcasting.

## Overview

DAB supports two audio codecs:
- **MPEG Layer II** (traditional DAB)
- **HE-AAC v2** (DAB+, more efficient)

Both require **48 kHz sample rate** per DAB standard.

---

## DAB (MPEG Layer II)

### Overview

**Codec:** MPEG-1 Audio Layer II (MP2)
**Standard:** ISO/IEC 11172-3
**File extension:** `.mp2`
**Subchannel type:** `'audio'`

**Characteristics:**
- Mature, widely supported codec
- Good quality at 128+ kbps
- Lower efficiency than AAC
- Compatible with all DAB receivers

### Recommended Bitrates

| Bitrate | Quality | Use Case |
|---------|---------|----------|
| 32 kbps | Low | Mono speech minimum |
| 48 kbps | Fair | Mono speech |
| 64 kbps | Good | Mono speech/music |
| 80 kbps | Good | Stereo speech |
| 96 kbps | Good | Stereo music |
| 112 kbps | Very Good | Stereo music |
| **128 kbps** | **Excellent** | **Standard music (recommended)** |
| 160 kbps | Excellent | High-quality music |
| 192 kbps | Premium | Premium music |
| 224 kbps | Premium | Very high quality |
| 256 kbps | Premium | Maximum quality |

**General guidelines:**
- **Music:** 128-192 kbps
- **Speech:** 64-96 kbps
- **Premium:** 192+ kbps

### Encoding with ffmpeg

#### Basic Encoding

```bash
# Standard quality (128 kbps stereo)
ffmpeg -i input.wav -c:a mp2 -ar 48000 -b:a 128k output.mp2
```

#### Encoding Options

**From WAV file:**
```bash
ffmpeg -i input.wav \
  -c:a mp2 \
  -ar 48000 \
  -b:a 128k \
  output.mp2
```

**From FLAC:**
```bash
ffmpeg -i input.flac \
  -c:a mp2 \
  -ar 48000 \
  -b:a 192k \
  output.mp2
```

**From MP3:**
```bash
# Transcoding (quality loss)
ffmpeg -i input.mp3 \
  -c:a mp2 \
  -ar 48000 \
  -b:a 128k \
  output.mp2
```

**Mono speech:**
```bash
ffmpeg -i speech.wav \
  -c:a mp2 \
  -ar 48000 \
  -ac 1 \
  -b:a 64k \
  output.mp2
```

**High quality music:**
```bash
ffmpeg -i music.wav \
  -c:a mp2 \
  -ar 48000 \
  -b:a 192k \
  -q:a 0 \
  output.mp2
```

#### Quality Settings

**Quality scale (-q:a):**
- `-q:a 0`: Best quality
- `-q:a 5`: Medium quality
- `-q:a 9`: Lowest quality

```bash
# Maximum quality
ffmpeg -i input.wav \
  -c:a mp2 \
  -ar 48000 \
  -b:a 192k \
  -q:a 0 \
  output.mp2
```

#### Batch Encoding

```bash
#!/bin/bash
# Encode all WAV files to MPEG Layer II

for wav in *.wav; do
    base=$(basename "$wav" .wav)
    ffmpeg -i "$wav" \
      -c:a mp2 \
      -ar 48000 \
      -b:a 128k \
      "${base}.mp2"
done
```

---

## DAB+ (HE-AAC v2)

### Overview

**Codec:** High-Efficiency Advanced Audio Coding version 2
**Standard:** ISO/IEC 14496-3
**File extension:** `.aac`
**Subchannel type:** `'dabplus'`

**Characteristics:**
- Modern, efficient codec
- Excellent quality at low bitrates
- ~2× more efficient than MP2
- Requires DAB+ capable receiver

### Recommended Bitrates

| Bitrate | Quality | Use Case |
|---------|---------|----------|
| 32 kbps | Fair | Mono speech |
| 40 kbps | Good | Mono speech |
| 48 kbps | Very Good | Stereo speech |
| 56 kbps | Very Good | Stereo speech/music |
| 64 kbps | Excellent | Stereo music |
| **72 kbps** | **Excellent** | **Standard music (recommended)** |
| 80 kbps | Premium | High-quality music |
| 96 kbps | Premium | Premium music |

**Efficiency comparison:**
- 48 kbps HE-AAC ≈ 96 kbps MP2 (speech)
- 72 kbps HE-AAC ≈ 128 kbps MP2 (music)
- 96 kbps HE-AAC ≈ 160 kbps MP2 (music)

**General guidelines:**
- **Music:** 72-96 kbps
- **Speech:** 48-56 kbps
- **Premium:** 96+ kbps

### Encoding with ffmpeg

#### Basic Encoding

```bash
# Standard quality (72 kbps stereo music)
ffmpeg -i input.wav \
  -c:a aac \
  -ar 48000 \
  -b:a 72k \
  -profile:a aac_he_v2 \
  output.aac
```

**Important:** Always specify `-profile:a aac_he_v2` for DAB+

#### Encoding Options

**Speech (48 kbps):**
```bash
ffmpeg -i speech.wav \
  -c:a aac \
  -ar 48000 \
  -b:a 48k \
  -profile:a aac_he_v2 \
  output.aac
```

**Standard music (72 kbps):**
```bash
ffmpeg -i music.wav \
  -c:a aac \
  -ar 48000 \
  -b:a 72k \
  -profile:a aac_he_v2 \
  output.aac
```

**Premium music (96 kbps):**
```bash
ffmpeg -i music.wav \
  -c:a aac \
  -ar 48000 \
  -b:a 96k \
  -profile:a aac_he_v2 \
  output.aac
```

**From various sources:**
```bash
# From FLAC
ffmpeg -i input.flac \
  -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 \
  output.aac

# From MP3 (transcoding)
ffmpeg -i input.mp3 \
  -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 \
  output.aac

# From ALSA (live capture)
ffmpeg -f alsa -i hw:0 \
  -c:a aac -ar 48000 -b:a 72k -profile:a aac_he_v2 \
  output.aac
```

#### Batch Encoding

```bash
#!/bin/bash
# Encode all WAV files to HE-AAC

for wav in *.wav; do
    base=$(basename "$wav" .wav)
    ffmpeg -i "$wav" \
      -c:a aac \
      -ar 48000 \
      -b:a 72k \
      -profile:a aac_he_v2 \
      "${base}.aac"
done
```

---

## Audio Processing

### Normalization

**Loudness normalization (EBU R128 standard):**
```bash
ffmpeg -i input.wav \
  -af loudnorm=I=-16:LRA=11:TP=-1.5 \
  normalized.wav
```

**Parameters:**
- `I=-16`: Target integrated loudness (LUFS)
- `LRA=11`: Loudness range
- `TP=-1.5`: True peak limit

**Two-pass normalization (more accurate):**
```bash
# Pass 1: Measure
ffmpeg -i input.wav \
  -af loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json \
  -f null -

# Use measured values in pass 2
ffmpeg -i input.wav \
  -af loudnorm=I=-16:LRA=11:TP=-1.5:measured_I=-20:measured_LRA=10:measured_TP=-2 \
  -c:a mp2 -ar 48000 -b:a 128k \
  output.mp2
```

### Resampling

**Convert sample rate to 48 kHz:**
```bash
# High-quality resampling
ffmpeg -i input_44100.wav \
  -af aresample=resampler=soxr:osr=48000 \
  -ar 48000 \
  output_48000.wav
```

**Convert and encode in one step:**
```bash
ffmpeg -i input_44100.wav \
  -af aresample=resampler=soxr:osr=48000 \
  -c:a mp2 -ar 48000 -b:a 128k \
  output.mp2
```

### Channel Mixing

**Stereo to mono:**
```bash
ffmpeg -i stereo.wav \
  -ac 1 \
  -c:a mp2 -ar 48000 -b:a 64k \
  mono.mp2
```

**Mono to stereo (duplicate):**
```bash
ffmpeg -i mono.wav \
  -ac 2 \
  -c:a mp2 -ar 48000 -b:a 128k \
  stereo.mp2
```

### Fade In/Out

**Prevent clicks at loop points:**
```bash
ffmpeg -i input.wav \
  -af "afade=t=in:st=0:d=0.1,afade=t=out:st=59.9:d=0.1" \
  -c:a mp2 -ar 48000 -b:a 128k \
  output.mp2
```

**Parameters:**
- `t=in`: Fade in
- `st=0`: Start time (seconds)
- `d=0.1`: Duration (seconds)

### Compression/Limiting

**Dynamic range compression:**
```bash
ffmpeg -i input.wav \
  -af "compand=attacks=0.3:decays=0.8:points=-80/-80|-45/-15|-27/-9|0/-7|20/-7" \
  -c:a mp2 -ar 48000 -b:a 128k \
  output.mp2
```

**Simple limiter:**
```bash
ffmpeg -i input.wav \
  -af "alimiter=limit=0.95:level=false" \
  -c:a mp2 -ar 48000 -b:a 128k \
  output.mp2
```

---

## Quality Comparison

### DAB vs DAB+

**At equivalent perceived quality:**

| Content | DAB (MP2) | DAB+ (HE-AAC) | Savings |
|---------|-----------|---------------|---------|
| Speech | 96 kbps | 48 kbps | 50% |
| Music | 128 kbps | 72 kbps | 44% |
| Premium | 192 kbps | 96 kbps | 50% |

**Capacity comparison (Mode I: 864 CU):**

| Scenario | DAB Services | DAB+ Services |
|----------|--------------|---------------|
| 128/72 kbps music | ~10 services | ~12 services |
| With protection level 2 | 10 × 84 CU | 12 × 60 CU |
| Total capacity used | ~840 CU | ~720 CU |

### Listening Tests

**Critical listening quality (music):**
- **128 kbps MP2:** Good, minor artifacts on complex passages
- **192 kbps MP2:** Excellent, transparent for most listeners
- **72 kbps HE-AAC:** Very good, comparable to 128 kbps MP2
- **96 kbps HE-AAC:** Excellent, comparable to 160+ kbps MP2

**Speech quality:**
- **64 kbps MP2:** Good
- **48 kbps HE-AAC:** Excellent (better than 64 kbps MP2)
- **96 kbps MP2:** Excellent
- **56 kbps HE-AAC:** Excellent (comparable to 96 kbps MP2)

---

## Validation and Testing

### Verify Encoding

**Check file format:**
```bash
ffprobe -hide_banner output.mp2
```

**Expected output (DAB):**
```
Stream #0:0: Audio: mp2, 48000 Hz, stereo, s16p, 128 kb/s
```

**Expected output (DAB+):**
```
Stream #0:0: Audio: aac (HE-AACv2), 48000 Hz, stereo, fltp, 72 kb/s
```

### Validate Parameters

**Check sample rate:**
```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=sample_rate \
  -of default=noprint_wrappers=1:nokey=1 \
  output.mp2
```

Should output: `48000`

**Check bitrate:**
```bash
ffprobe -v error -select_streams a:0 \
  -show_entries stream=bit_rate \
  -of default=noprint_wrappers=1:nokey=1 \
  output.mp2
```

Should output bitrate in bits/s (e.g., `128000` for 128 kbps)

**Check duration:**
```bash
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 \
  output.mp2
```

### Test Playback

**Play file:**
```bash
ffplay output.mp2
# or
ffplay output.aac
```

**Analyze audio:**
```bash
# Show audio waveform
ffplay -f lavfi "amovie=output.mp2,asplit[a][b];[a]avectorscope[out0];[b]showwaves[out1]"

# Show spectrum
ffplay -f lavfi "amovie=output.mp2,asplit[a][b];[a]showspectrum[out0];[b]showwaves[out1]"
```

---

## Troubleshooting

### Wrong Sample Rate

**Error:**
```
ERROR: Expected 48000 Hz, got 44100 Hz
```

**Solution:**
```bash
# Resample to 48 kHz
ffmpeg -i input_44100.wav \
  -ar 48000 \
  -c:a mp2 -b:a 128k \
  output.mp2
```

### Wrong Codec

**Error:**
```
ERROR: Expected MPEG frame, got AAC superframe
```

**Solution:** Check subchannel type matches file format
- `.mp2` files → `type: 'audio'`
- `.aac` files → `type: 'dabplus'`

### Bitrate Mismatch

**Error:**
```
ERROR: File bitrate 192 kbps doesn't match configured 128 kbps
```

**Solution:** Re-encode at correct bitrate or update configuration

### Profile Not Supported

**Error:**
```
ERROR: AAC profile not HE-AAC v2
```

**Solution:** Ensure `-profile:a aac_he_v2`:
```bash
ffmpeg -i input.wav \
  -c:a aac -ar 48000 -b:a 72k \
  -profile:a aac_he_v2 \
  output.aac
```

### Audio Quality Issues

**Problem:** Poor audio quality despite high bitrate

**Diagnosis:**
```bash
# Check encoding parameters
ffprobe -hide_banner file.mp2

# Visualize spectrum
ffplay -f lavfi "amovie=file.mp2,showspectrum"
```

**Solutions:**
1. Use higher bitrate
2. Check source quality (don't transcode lossy)
3. Use proper encoder settings (-q:a 0 for MP2)
4. Ensure 48 kHz sample rate
5. Apply normalization

---

## Best Practices

### Source Material

1. **Start with lossless:** Use WAV, FLAC, or high-quality source
2. **Avoid transcoding:** Don't encode from MP3/AAC (quality loss)
3. **Match levels:** Normalize before encoding
4. **48 kHz native:** Use 48 kHz sources when possible

### Encoding Settings

1. **DAB music:** 128-192 kbps MP2
2. **DAB+ music:** 72-96 kbps HE-AAC v2
3. **Speech:** 48-64 kbps (DAB+ preferred)
4. **Always 48 kHz:** Required by DAB standard
5. **Quality flag:** Use `-q:a 0` for MP2

### Testing

1. **Validate format:** Use ffprobe
2. **Test playback:** Listen before deployment
3. **Check levels:** Ensure proper loudness
4. **Monitor quality:** Watch for artifacts
5. **Compare codecs:** Test both DAB and DAB+

### Production

1. **Batch processing:** Automate encoding workflows
2. **Archive originals:** Keep lossless source files
3. **Version control:** Track encoding settings used
4. **Documentation:** Document bitrate choices
5. **Monitoring:** Log encoding statistics

---

## Complete Examples

### Music Station (DAB)

```bash
# High-quality music encoding workflow
# 1. Normalize
ffmpeg -i source.wav \
  -af loudnorm=I=-16:LRA=11:TP=-1.5 \
  normalized.wav

# 2. Encode to MPEG Layer II
ffmpeg -i normalized.wav \
  -c:a mp2 \
  -ar 48000 \
  -b:a 192k \
  -q:a 0 \
  music_192k.mp2

# 3. Verify
ffprobe -hide_banner music_192k.mp2

# 4. Test
ffplay music_192k.mp2
```

### Music Station (DAB+)

```bash
# Efficient music encoding workflow
# 1. Normalize
ffmpeg -i source.wav \
  -af loudnorm=I=-16:LRA=11:TP=-1.5 \
  normalized.wav

# 2. Encode to HE-AAC v2
ffmpeg -i normalized.wav \
  -c:a aac \
  -ar 48000 \
  -b:a 72k \
  -profile:a aac_he_v2 \
  music_72k.aac

# 3. Verify
ffprobe -hide_banner music_72k.aac

# 4. Test
ffplay music_72k.aac
```

### Speech/News Station

```bash
# Speech-optimized encoding
ffmpeg -i speech.wav \
  -af "loudnorm=I=-16:LRA=11:TP=-1.5,highpass=f=80,lowpass=f=8000" \
  -c:a aac \
  -ar 48000 \
  -b:a 48k \
  -profile:a aac_he_v2 \
  speech_48k.aac
```

### Live Streaming

```bash
# Capture from sound card and encode
ffmpeg -f alsa -i hw:0 \
  -af "loudnorm=I=-16:LRA=11:TP=-1.5" \
  -c:a mp2 \
  -ar 48000 \
  -b:a 128k \
  -f mp2 \
  udp://239.1.2.3:5001
```

---

## See Also

- [Input Sources Overview](index.md): All input types
- [File Inputs](file-inputs.md): File-based input guide
- [Network Inputs](network-inputs.md): Live streaming guide
- [Subchannels](../configuration/subchannels.md): Subchannel configuration
- [DAB+ Tutorial](../../tutorials/dab-plus-setup.md): Step-by-step DAB+ setup
