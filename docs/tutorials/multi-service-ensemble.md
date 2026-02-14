# Tutorial: Multi-Service Ensemble

Build a complete DAB ensemble with multiple radio stations, mixing DAB and DAB+ services.

**Difficulty:** Intermediate
**Time:** 25 minutes

## What You'll Build

A DAB ensemble with:
- 4 radio stations
- Mix of DAB (MPEG Layer II) and DAB+ (HE-AAC)
- Different bitrates optimized for content type
- Proper capacity allocation

## Prerequisites

- Completed [Basic Single Service Tutorial](basic-single-service.md)
- Multiple audio files (or reuse one file for testing)
- Understanding of [Basic Concepts](../getting-started/basic-concepts.md)

## Step 1: Plan Your Ensemble

Let's design a realistic DAB ensemble:

| Station | Type | Bitrate | Content | Protection |
|---------|------|---------|---------|------------|
| Music FM | DAB | 192 kbps | Music (high quality) | Level 3 |
| News 24 | DAB+ | 64 kbps | Speech/News | Level 2 |
| Pop Hits | DAB+ | 80 kbps | Music | Level 2 |
| Classical | DAB+ | 96 kbps | Classical music | Level 3 |

**Total capacity needed:** ~432 kbps (Mode I has ~864 CUs available)

## Step 2: Prepare Audio Files

Create or prepare 4 audio files:

```bash
# Music station: High-quality MPEG Layer II
ffmpeg -i music.wav -codec:a mp2 -b:a 192k -ar 48000 music_192.mp2

# News station: HE-AAC for speech
ffmpeg -i news.wav -codec:a libfdk_aac -profile:a aac_he -b:a 64k -ar 48000 news_64.aac

# Pop station: HE-AAC
ffmpeg -i pop.wav -codec:a libfdk_aac -profile:a aac_he -b:a 80k -ar 48000 pop_80.aac

# Classical station: HE-AAC
ffmpeg -i classical.wav -codec:a libfdk_aac -profile:a aac_he -b:a 96k -ar 48000 classical_96.aac
```

**Testing tip:** For testing, you can use the same audio file for all services. Just copy it:
```bash
cp music_192.mp2 station1.mp2
cp music_192.mp2 station2.mp2
# etc.
```

## Step 3: Create Configuration

Create `multi_service.yaml`:

```yaml
# Multi-Service DAB Ensemble Configuration

ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Multi DAB'
    short: 'MultiDAB'
  lto_auto: true

# Subchannels - the actual audio streams
subchannels:
  # Subchannel 0: Music FM (high-quality DAB)
  - uid: 'music_audio'
    id: 0
    type: 'audio'              # DAB (MPEG Layer II)
    bitrate: 192
    start_address: 0           # First subchannel
    protection:
      level: 3                 # Higher protection for premium content
      shortform: true
    input: 'file://music_192.mp2'

  # Subchannel 1: News 24 (speech-optimized DAB+)
  - uid: 'news_audio'
    id: 1
    type: 'dabplus'            # DAB+ (HE-AAC)
    bitrate: 64
    start_address: 200         # After music channel
    protection:
      level: 2
      shortform: true
    input: 'file://news_64.aac'

  # Subchannel 2: Pop Hits (DAB+)
  - uid: 'pop_audio'
    id: 2
    type: 'dabplus'
    bitrate: 80
    start_address: 300
    protection:
      level: 2
      shortform: true
    input: 'file://pop_80.aac'

  # Subchannel 3: Classical (higher-quality DAB+)
  - uid: 'classical_audio'
    id: 3
    type: 'dabplus'
    bitrate: 96
    start_address: 400
    protection:
      level: 3
      shortform: true
    input: 'file://classical_96.aac'

# Services - the radio stations listeners see
services:
  # Service 1: Music FM
  - uid: 'music_service'
    id: '0x5001'
    label:
      text: 'Music FM'
      short: 'MusicFM'
    pty: 10                    # Pop Music
    language: 9                # English

  # Service 2: News 24
  - uid: 'news_service'
    id: '0x5002'
    label:
      text: 'News 24'
      short: 'News24'
    pty: 1                     # News
    language: 9

  # Service 3: Pop Hits
  - uid: 'pop_service'
    id: '0x5003'
    label:
      text: 'Pop Hits Radio'
      short: 'PopHits'
    pty: 10                    # Pop Music
    language: 9

  # Service 4: Classical
  - uid: 'classical_service'
    id: '0x5004'
    label:
      text: 'Classical FM'
      short: 'Classic'
    pty: 6                     # Classical Music
    language: 9

# Components - links between services and subchannels
components:
  - uid: 'music_comp'
    service_id: '0x5001'
    subchannel_id: 0
    type: 0

  - uid: 'news_comp'
    service_id: '0x5002'
    subchannel_id: 1
    type: 0

  - uid: 'pop_comp'
    service_id: '0x5003'
    subchannel_id: 2
    type: 0

  - uid: 'classical_comp'
    service_id: '0x5004'
    subchannel_id: 3
    type: 0
```

## Step 4: Understand Start Addresses

The `start_address` field determines where each subchannel begins in the Main Service Transport (MST).

**How to calculate:**
1. First subchannel always starts at 0
2. Each subsequent subchannel starts after the previous one
3. Calculate based on bitrate + protection overhead

**Simplified approach:** Use multiples of 50 or 100 for spacing. python-dabmux will validate if they fit.

**Example:**
- Subchannel 0: start_address 0
- Subchannel 1: start_address 200 (after subchannel 0)
- Subchannel 2: start_address 300 (after subchannel 1)
- Subchannel 3: start_address 400 (after subchannel 2)

## Step 5: Test Configuration

Test that all services are configured correctly:

```bash
python -m dabmux.cli -c multi_service.yaml -o test.eti -n 10 -vvv
```

**Check for:**
```
INFO: Added service 'Music FM' (0x5001)
INFO: Added service 'News 24' (0x5002)
INFO: Added service 'Pop Hits Radio' (0x5003)
INFO: Added service 'Classical FM' (0x5004)
INFO: Added subchannel 0: audio, 192 kbps
INFO: Added subchannel 1: dabplus, 64 kbps
INFO: Added subchannel 2: dabplus, 80 kbps
INFO: Added subchannel 3: dabplus, 96 kbps
```

## Step 6: Generate Output

Generate a full multiplex:

```bash
python -m dabmux.cli -c multi_service.yaml -o multi_service.eti -n 5000
```

**Expected:**
- 4 services multiplexed together
- All services in one ETI stream
- File size: ~30 MB (5000 frames × ~6000 bytes)

## Step 7: Verify Services

Check that all services are present in the FIG data:

```bash
# Generate a small sample
python -m dabmux.cli -c multi_service.yaml -o sample.eti -n 100 -vvv
```

Look for FIG generation messages showing all services.

## Understanding Programme Types (PTY)

The `pty` field categorizes stations:

| PTY | Category | Use For |
|-----|----------|---------|
| 0 | None | Unspecified |
| 1 | News | News stations |
| 2 | Current Affairs | Talk/discussion |
| 3 | Information | General information |
| 4 | Sport | Sports content |
| 5 | Education | Educational |
| 6 | Drama | Drama/culture |
| 6 | Classical Music | Classical |
| 7 | Rock Music | Rock |
| 8 | Easy Listening | Easy listening |
| 9 | Light Classical | Light classical |
| 10 | Pop Music | Pop |
| 11 | Jazz Music | Jazz |
| 12 | Country Music | Country |

Choose the PTY that best matches your station's content.

## Capacity Management

### Checking Available Capacity

Mode I provides **864 Capacity Units (CUs)**.

**Rough calculation:**
- 128 kbps DAB with level 2 protection ≈ 84 CUs
- 192 kbps DAB with level 3 protection ≈ 150 CUs
- 64 kbps DAB+ with level 2 protection ≈ 48 CUs
- 80 kbps DAB+ with level 2 protection ≈ 60 CUs
- 96 kbps DAB+ with level 3 protection ≈ 78 CUs

**Our ensemble:**
- Music FM: ~150 CUs
- News 24: ~48 CUs
- Pop Hits: ~60 CUs
- Classical: ~78 CUs
- **Total: ~336 CUs** (plenty of room!)

### If You Exceed Capacity

**Error:**
```
ERROR: Total subchannel capacity exceeds available CUs
```

**Solutions:**
1. **Reduce bitrates**: Lower some services to 48-64 kbps (DAB+)
2. **Lower protection**: Use level 1 or 2 instead of 3
3. **Remove services**: Fewer stations
4. **Use DAB+ more**: More efficient than DAB

## Advanced: Mixing Content Types

### Speech-Optimized Service

For talk/news stations, use lower bitrates:

```yaml
- uid: 'talk_audio'
  type: 'dabplus'
  bitrate: 48                  # Low bitrate, fine for speech
  protection:
    level: 2
```

### High-Quality Music Service

For premium music content:

```yaml
- uid: 'premium_audio'
  type: 'audio'                # DAB for high quality
  bitrate: 256                 # Very high quality
  protection:
    level: 3
```

### Balanced Ensemble

Mix high and low bitrate services to maximize quality within capacity:

- 1× 192 kbps DAB (premium music)
- 2× 80 kbps DAB+ (regular music)
- 3× 48 kbps DAB+ (news/talk)

This gives 6 services within Mode I capacity.

## Testing Scenarios

### Continuous Operation

Run the multiplex continuously:

```bash
python -m dabmux.cli -c multi_service.yaml -o output.eti --continuous
```

All 4 services will multiplex together continuously.

### With Timestamps

Add timestamps for synchronized transmission:

```bash
python -m dabmux.cli -c multi_service.yaml -o output.eti --tist -n 5000
```

### Different Services per File

Test with different audio files to verify each service is independent:

```bash
# Create distinct test files
ffmpeg -i /dev/urandom -f s16le -ar 48000 -ac 2 -t 60 -codec:a mp2 -b:a 192k test1.mp2
ffmpeg -i /dev/urandom -f s16le -ar 48000 -ac 2 -t 60 -codec:a libfdk_aac -profile:a aac_he -b:a 64k test2.aac
```

## Troubleshooting

### Error: Duplicate service ID

```
ERROR: Duplicate service ID: 0x5001
```

**Solution:** Ensure each service has a unique ID:
```yaml
services:
  - id: '0x5001'  # Unique
  - id: '0x5002'  # Unique
  - id: '0x5003'  # Unique
```

### Error: Component references unknown subchannel

```
ERROR: Component references unknown subchannel_id: 5
```

**Solution:** Verify `subchannel_id` in components matches a subchannel `id`:
```yaml
subchannels:
  - id: 0       # ← This ID
components:
  - subchannel_id: 0  # ← Must match
```

### One service is silent

**Problem:** One service produces no audio

**Possible causes:**
1. Input file not found or wrong format
2. Mismatched bitrate (config vs. file)
3. Wrong audio type (audio vs. dabplus)

**Solution:**
- Verify input file: `ffprobe service.mp2`
- Check type matches format (MPEG = audio, AAC = dabplus)
- Ensure bitrate in config matches file

## Next Steps

### Add Network Inputs

Continue to [Network Streaming Tutorial](network-streaming.md) to use UDP/TCP inputs instead of files.

### Add PFT for Network Output

Continue to [PFT with FEC Tutorial](pft-with-fec.md) to add error correction for network transmission.

### Optimize for Your Use Case

Read the [Configuration Reference](../user-guide/configuration/index.md) to fine-tune:
- Protection levels
- Bitrate allocation
- Label customization

## Summary

Congratulations! You've created a multi-service DAB ensemble. You learned:

- ✅ Configuring multiple services in one ensemble
- ✅ Mixing DAB and DAB+ services
- ✅ Managing capacity allocation
- ✅ Using appropriate bitrates for different content types
- ✅ Understanding start addresses and subchannel organization

## Complete Configuration

Here's the complete configuration for reference:

```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'Multi DAB'
    short: 'MultiDAB'
  lto_auto: true

subchannels:
  - {uid: music_audio, id: 0, type: audio, bitrate: 192, start_address: 0,
     protection: {level: 3, shortform: true}, input: 'file://music_192.mp2'}
  - {uid: news_audio, id: 1, type: dabplus, bitrate: 64, start_address: 200,
     protection: {level: 2, shortform: true}, input: 'file://news_64.aac'}
  - {uid: pop_audio, id: 2, type: dabplus, bitrate: 80, start_address: 300,
     protection: {level: 2, shortform: true}, input: 'file://pop_80.aac'}
  - {uid: classical_audio, id: 3, type: dabplus, bitrate: 96, start_address: 400,
     protection: {level: 3, shortform: true}, input: 'file://classical_96.aac'}

services:
  - {uid: music_service, id: '0x5001', label: {text: Music FM, short: MusicFM}, pty: 10, language: 9}
  - {uid: news_service, id: '0x5002', label: {text: News 24, short: News24}, pty: 1, language: 9}
  - {uid: pop_service, id: '0x5003', label: {text: Pop Hits Radio, short: PopHits}, pty: 10, language: 9}
  - {uid: classical_service, id: '0x5004', label: {text: Classical FM, short: Classic}, pty: 6, language: 9}

components:
  - {uid: music_comp, service_id: '0x5001', subchannel_id: 0, type: 0}
  - {uid: news_comp, service_id: '0x5002', subchannel_id: 1, type: 0}
  - {uid: pop_comp, service_id: '0x5003', subchannel_id: 2, type: 0}
  - {uid: classical_comp, service_id: '0x5004', subchannel_id: 3, type: 0}
```

Save this as `multi_service.yaml` and multiplex 4 services together!
