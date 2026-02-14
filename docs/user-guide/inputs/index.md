# Input Sources

Overview of input sources for audio and data streams in python-dabmux.

## What Are Inputs?

Inputs are the sources of audio or data that feed into subchannels. Each subchannel must have exactly one input source specified via the `input` URI parameter.

**Input URI format:**
```
protocol://path_or_address
```

## Available Input Types

python-dabmux supports three input types:

| Type | Protocol | Use Case | Example |
|------|----------|----------|---------|
| **File** | `file://` | Pre-recorded audio files | `file://audio.mp2` |
| **UDP** | `udp://` | Network streaming (multicast/unicast) | `udp://239.1.2.3:5001` |
| **TCP** | `tcp://` | Network streaming (reliable) | `tcp://192.168.1.100:5002` |

---

## Quick Start

### File Input

```yaml
subchannels:
  - uid: 'audio1'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'file://audio.mp2'
```

### UDP Input

```yaml
subchannels:
  - uid: 'live_stream'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'udp://239.1.2.3:5001'
```

### TCP Input

```yaml
subchannels:
  - uid: 'reliable_stream'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'tcp://192.168.1.100:5002'
```

---

## Input Type Selection

### File Inputs

**Use when:**
- Testing with pre-recorded content
- Scheduled programming
- Looped audio playout
- Development and debugging

**Advantages:**
- Simple and reliable
- No network dependencies
- Repeatable testing
- Easy to manage

**Limitations:**
- Static content only
- No live streaming
- Must prepare files in advance

See [File Inputs](file-inputs.md) for details.

### UDP Inputs

**Use when:**
- Live streaming over IP
- Multicast distribution
- Low-latency required
- Multiple receivers

**Advantages:**
- Low latency
- Multicast support (one-to-many)
- Standard streaming protocol
- Network efficiency

**Limitations:**
- Packet loss possible
- No delivery guarantee
- Requires network configuration

See [Network Inputs](network-inputs.md) for details.

### TCP Inputs

**Use when:**
- Reliable delivery required
- Point-to-point streaming
- Network has packet loss
- Quality over latency

**Advantages:**
- Guaranteed delivery
- No packet loss
- Error correction built-in
- Simple configuration

**Limitations:**
- Higher latency than UDP
- No multicast support
- Single sender/receiver only

See [Network Inputs](network-inputs.md) for details.

---

## Audio Format Requirements

### DAB (MPEG Layer II)

**Subchannel type:** `'audio'`

**File format:** MPEG-1 Audio Layer II (`.mp2`)

**Encoding:**
```bash
ffmpeg -i input.wav -c:a mp2 -b:a 128k output.mp2
```

**Requirements:**
- Sample rate: 48 kHz (DAB standard)
- Channels: Stereo or mono
- Bitrate: Must match subchannel bitrate

### DAB+ (HE-AAC v2)

**Subchannel type:** `'dabplus'`

**File format:** HE-AAC v2 (`.aac`)

**Encoding:**
```bash
ffmpeg -i input.wav -c:a aac -b:a 72k -profile:a aac_he_v2 output.aac
```

**Requirements:**
- Sample rate: 48 kHz (DAB standard)
- Profile: HE-AAC v2
- Bitrate: Must match subchannel bitrate

See [Audio Formats](audio-formats.md) for complete encoding guide.

---

## Input Buffer Management

python-dabmux automatically manages input buffers:

1. **Frame timing:** Reads audio data based on ETI frame timing
2. **Buffering:** Internal buffers smooth out timing variations
3. **Underrun handling:** Inserts silence if input stalls
4. **Overrun prevention:** Drops excess data if input too fast

**Buffer behavior:**
- File inputs: Read at frame rate
- Network inputs: Buffered for jitter tolerance
- Continuous mode: Loops file inputs automatically

---

## Input Configuration Examples

### Multiple File Inputs

```yaml
subchannels:
  - uid: 'music'
    id: 0
    type: 'audio'
    input: 'file://music.mp2'

  - uid: 'news'
    id: 1
    type: 'dabplus'
    input: 'file://news.aac'
```

### Mixed Network and File

```yaml
subchannels:
  # Live network stream
  - uid: 'live'
    id: 0
    type: 'audio'
    input: 'udp://239.1.2.3:5001'

  # Pre-recorded backup
  - uid: 'backup'
    id: 1
    type: 'audio'
    input: 'file://backup.mp2'
```

### Multicast Distribution

```yaml
subchannels:
  # Encoder sends to multicast group
  - uid: 'multicast_1'
    id: 0
    type: 'audio'
    input: 'udp://239.1.2.3:5001'

  - uid: 'multicast_2'
    id: 1
    type: 'audio'
    input: 'udp://239.1.2.4:5002'
```

---

## Continuous Mode

For live streaming or looped playout, use `--continuous`:

```bash
python -m dabmux.cli -c config.yaml -o output.eti --continuous
```

**Behavior:**
- File inputs: Loop automatically when reaching end
- Network inputs: Continue reading indefinitely
- Runs until interrupted (Ctrl+C)

---

## Input Validation

python-dabmux validates inputs:

1. **URI format:** Checks protocol and format
2. **File existence:** Verifies file inputs exist
3. **Audio format:** Validates format matches type
4. **Bitrate match:** Ensures file bitrate matches configuration
5. **Sample rate:** Verifies 48 kHz

**Common validation errors:**

```
ERROR: Input file not found: audio.mp2
ERROR: Expected MPEG frame, got invalid data
ERROR: Bitrate mismatch: expected 128 kbps, got 192 kbps
```

---

## Performance Considerations

### File Inputs

- **I/O:** Minimal overhead, disk speed not critical
- **CPU:** Negligible
- **Memory:** Small buffer per input

### Network Inputs

- **Network:** Bitrate × 1.1 (10% overhead)
- **Latency:** UDP: 1-10ms, TCP: 10-50ms
- **Jitter tolerance:** ~100ms buffer
- **CPU:** Minimal for receiving

### Multiple Inputs

- **Scaling:** Linear with number of inputs
- **Typical:** 10+ inputs easily supported
- **Bottleneck:** Usually ETI generation, not inputs

---

## Troubleshooting

### File Input Issues

**File not found:**
```
ERROR: Input file not found: audio.mp2
```
Solution: Check path, use absolute paths

**Wrong format:**
```
ERROR: Expected MPEG frame, got AAC
```
Solution: Match file format to subchannel type

See [Input Issues](../../troubleshooting/input-issues.md) for more.

### Network Input Issues

**No data received:**
```
WARNING: Input timeout, inserting silence
```
Solution: Check network connectivity, firewall

**Packet loss:**
```
WARNING: Input underrun detected
```
Solution: Increase buffer, use TCP, or higher protection

See [Network Issues](../../troubleshooting/network-issues.md) for more.

---

## Best Practices

### File Inputs

1. **Absolute paths:** Use absolute paths in production
2. **Pre-validate:** Test files before deployment
3. **Backup:** Keep backup files for failover
4. **Naming:** Use descriptive filenames

### Network Inputs

1. **Dedicated network:** Use separate network for streaming
2. **Multicast:** Prefer multicast for one-to-many
3. **Monitoring:** Monitor input statistics
4. **Redundancy:** Have backup inputs configured

### General

1. **Match bitrates:** Ensure file/stream bitrate matches config
2. **48 kHz:** Always use 48 kHz sample rate
3. **Test first:** Test with short files before production
4. **Monitor logs:** Watch for warnings and errors

---

## Input Statistics

Enable verbose mode to see input statistics:

```bash
python -m dabmux.cli -c config.yaml -o output.eti -v
```

**Statistics shown:**
- Bytes read per input
- Buffer fill levels
- Underrun/overrun counts
- Network packet statistics

---

## See Also

- [File Inputs](file-inputs.md): Detailed file input documentation
- [Network Inputs](network-inputs.md): UDP/TCP streaming guide
- [Audio Formats](audio-formats.md): Complete encoding reference
- [Subchannels](../configuration/subchannels.md): Subchannel configuration
- [Tutorials](../../tutorials/index.md): Step-by-step guides
