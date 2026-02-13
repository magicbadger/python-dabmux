# Frequently Asked Questions

Common questions about python-dabmux and DAB multiplexing.

## General Questions

### What is python-dabmux?

python-dabmux is a pure Python implementation of a DAB/DAB+ multiplexer. It combines multiple audio streams into a single DAB ensemble for transmission, similar to ODR-DabMux but written in Python.

**Key features:**
- Complete ETI frame generation
- File and network inputs (UDP/TCP)
- ETI file and EDI network outputs
- PFT with Reed-Solomon FEC
- YAML configuration files
- 389 unit tests, 71% coverage

---

### Why use python-dabmux instead of ODR-DabMux?

**Choose python-dabmux if you want:**
- Pure Python implementation (easy to modify and integrate)
- Clear, readable code for learning DAB standards
- Easy installation with pip
- Python-based tooling and workflows

**Choose ODR-DabMux if you need:**
- Production-proven C++ implementation
- Maximum performance
- Lower resource usage
- Established ecosystem

**Both are great options!** python-dabmux is feature-complete and production-ready, but ODR-DabMux has been used in broadcast environments for years.

---

### Is python-dabmux production-ready?

**Yes!** python-dabmux is feature-complete with:
- All core features implemented (Phases 0-6 complete)
- 389 unit tests with 71% code coverage
- Full type annotations with mypy validation
- Standards-compliant (ETSI EN 300 799)

**Use cases:**
- ✅ Development and testing
- ✅ Small to medium deployments
- ✅ Educational purposes
- ✅ Integration with Python tools
- ⚠️ Large-scale production (consider ODR-DabMux for maximum performance)

---

### What Python version is required?

**Python 3.11 or later** is required.

python-dabmux uses modern Python features like:
- Type annotations with `|` union syntax
- Structural pattern matching
- Improved type hints

**Check your version:**
```bash
python --version
```

**Install Python 3.11+:**
```bash
# Ubuntu/Debian
sudo apt install python3.11

# macOS (Homebrew)
brew install python@3.11
```

---

## Configuration Questions

### How do I create a configuration file?

Create a YAML file with four main sections:

1. **ensemble**: Top-level parameters (ID, label, mode)
2. **subchannels**: Audio/data streams (bitrate, protection, input)
3. **services**: Radio stations (ID, labels, metadata)
4. **components**: Links between services and subchannels

**Minimal example:**
```yaml
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'My DAB'

subchannels:
  - uid: 'audio1'
    id: 0
    bitrate: 128
    input: 'file://audio.mp2'

services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'Radio One'

components:
  - service_id: '0x5001'
    subchannel_id: 0
```

**See:** [Configuration Reference](user-guide/configuration/index.md)

---

### What's the difference between service and subchannel?

**Services** are what listeners see (radio stations):
- Have names and labels
- Have programme type (News, Music, etc.)
- Multiple services per ensemble

**Subchannels** are the actual data streams:
- Carry audio or data
- Have bitrates and protection levels
- Connect to input sources

**Components** link services to subchannels:
- One service can have multiple components
- Most commonly: one audio component per service

**Think of it like this:**
- Service = "BBC Radio 1" (what you tune to)
- Subchannel = 128 kbps MPEG audio stream (the data)
- Component = Link between them

---

### Why do I need to quote hex values?

YAML interprets unquoted hex values as regular numbers.

**Wrong:**
```yaml
id: 0xCE15    # YAML sees this as number 52757
```

**Correct:**
```yaml
id: '0xCE15'  # YAML sees this as string, parser converts to hex
```

**Rule:** Always quote hex values in YAML configuration files.

---

### Can I use the same audio file for multiple services?

**Yes!** You can point multiple subchannels to the same input file:

```yaml
subchannels:
  - uid: 'sub1'
    id: 0
    input: 'file://audio.mp2'  # Same file
  - uid: 'sub2'
    id: 1
    input: 'file://audio.mp2'  # Same file
```

Each subchannel will independently read the file. This is useful for:
- Testing with one audio source
- Simulcasting the same content
- Different protection levels for same content

---

### How many services can I have in one ensemble?

**Theoretical limit:** 64 subchannels (6-bit subchannel ID)

**Practical limit:** Depends on **capacity units** available:
- Mode I: 864 CU total
- Each service uses CUs based on bitrate and protection level

**Example (Mode I):**
- 6-7 services at 128 kbps each (moderate protection)
- 10-12 services at 64 kbps each (DAB+)
- Fewer services at higher bitrates

**Calculation:** Use a capacity calculator or let python-dabmux warn you if you exceed capacity.

---

## Audio and Input Questions

### What audio formats are supported?

**DAB (traditional):**
- MPEG-1 Audio Layer II (`.mp2` files)
- Bitrates: 32-384 kbps (typical: 128-192 kbps)

**DAB+ (modern):**
- HE-AAC v2 (`.aac` files)
- Bitrates: 32-192 kbps (typical: 48-72 kbps)

**Input methods:**
- File: `file://audio.mp2`
- UDP: `udp://239.1.2.3:5001`
- TCP: `tcp://192.168.1.100:5001`

---

### How do I convert audio to MPEG Layer II?

Use **ffmpeg** to convert any audio to MPEG Layer II:

```bash
# From WAV
ffmpeg -i input.wav -codec:a mp2 -b:a 128k output.mp2

# From MP3
ffmpeg -i input.mp3 -codec:a mp2 -b:a 128k output.mp2

# From AAC
ffmpeg -i input.m4a -codec:a mp2 -b:a 128k output.mp2

# Specify sample rate (48 kHz recommended)
ffmpeg -i input.wav -codec:a mp2 -b:a 128k -ar 48000 output.mp2
```

**Parameters:**
- `-codec:a mp2`: MPEG-1 Audio Layer II
- `-b:a 128k`: Bitrate (match your configuration)
- `-ar 48000`: Sample rate (24000, 32000, or 48000 Hz)

---

### Should I use DAB or DAB+?

**Use DAB (MPEG Layer II) if:**
- You need compatibility with older receivers
- You want higher bitrates (192+ kbps)
- You have existing MPEG equipment

**Use DAB+ (HE-AAC v2) if:**
- You want better quality at lower bitrates
- You need more services per ensemble
- Modern receivers (post-2010)

**Comparison:**

| Feature | DAB (MPEG Layer II) | DAB+ (HE-AAC v2) |
|---------|---------------------|------------------|
| Quality at 64 kbps | Fair | Good |
| Quality at 128 kbps | Excellent | Excellent |
| Bitrate range | 32-384 kbps | 32-192 kbps |
| Efficiency | Lower | Higher |
| Compatibility | Universal | Modern only |

**Recommendation:** Use DAB+ at 48-72 kbps for music, 32-48 kbps for speech/talk.

---

### Can I stream live audio into python-dabmux?

**Yes!** Use UDP or TCP network inputs:

```yaml
subchannels:
  - uid: 'live1'
    id: 0
    type: 'audio'
    bitrate: 128
    input: 'udp://239.1.2.3:5001'  # Listen for UDP stream
```

**Stream audio with ffmpeg:**
```bash
# Encode and stream to UDP
ffmpeg -re -i live_input.wav \
  -codec:a mp2 -b:a 128k -ar 48000 \
  -f rtp udp://239.1.2.3:5001
```

**Or use gstreamer, VLC, or any tool that outputs MPEG Layer II to UDP/TCP.**

---

## Output Questions

### What's the difference between ETI and EDI?

**ETI (Ensemble Transport Interface):**
- Raw frame format
- File-based or stream-based
- No built-in network protocol
- Used for: recording, testing, file-based transmission

**EDI (Ensemble Data Interface):**
- Network protocol for transmitting ETI
- Built on UDP or TCP
- Optional PFT (fragmentation and FEC)
- Used for: network transmission, multi-transmitter setups

**When to use:**
- **ETI files**: Testing, recording, file exchange
- **EDI network**: Live transmission, distributed systems

---

### What ETI file format should I use?

**Three formats available:**

1. **Raw ETI** (`-f raw`):
   - Plain frames, no additional structure
   - Smallest file size
   - Compatible with most tools
   - **Use for:** General purpose, maximum compatibility

2. **Streamed ETI** (`-f streamed`):
   - Frames with timing information
   - Used for timed playback
   - **Use for:** Synchronized replay, timestamped archives

3. **Framed ETI** (`-f framed`, default):
   - 8-byte aligned frames with delimiters
   - Easy to parse and process
   - **Use for:** Processing, analysis, development

**Recommendation:** Use **framed** (default) unless you need specific compatibility.

---

### When should I use PFT?

**Use PFT (Protection, Fragmentation and Transport) when:**
- Transmitting over unreliable networks
- MTU limitations require fragmentation
- Packet loss is expected
- Running distributed transmitter network (SFN)

**PFT provides:**
- Fragmentation (split large packets to fit MTU)
- Sequence numbers (detect missing packets)
- Reed-Solomon FEC (recover lost packets)

**Enable with:**
```bash
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fec
```

**Without PFT:** Use for reliable networks (wired, local)

**With PFT:** Use for lossy networks (wireless, WAN, Internet)

---

### Can I output to both file and network simultaneously?

**Not directly.** python-dabmux outputs to one destination at a time.

**Workarounds:**

1. **Run two instances:**
   ```bash
   # Terminal 1: File output
   dabmux -c config.yaml -o output.eti --continuous

   # Terminal 2: Network output (different config)
   dabmux -c config.yaml --edi udp://239.1.2.3:12000 --continuous
   ```

2. **Use tee for UDP:**
   ```bash
   # Output to file, use external tools to multicast
   dabmux -c config.yaml -o output.eti
   # Then use separate tool to transmit file over network
   ```

3. **Post-process:**
   ```bash
   # Generate file first
   dabmux -c config.yaml -o output.eti

   # Then transmit file
   cat output.eti | socat - UDP4-DATAGRAM:239.1.2.3:12000
   ```

---

## Performance Questions

### How much CPU does python-dabmux use?

**Typical usage:**
- **Mode I**: 10-20% of one CPU core at 10.4 frames/second
- **Multiple services**: Scales linearly with number of services
- **PFT with FEC**: +10-15% overhead

**Factors affecting performance:**
- Number of services
- FIG types enabled
- PFT and FEC
- Input sources (network inputs have lower overhead than files)

**Optimization:**
- Use raw ETI format for output (smaller files)
- Disable unnecessary FIG types
- Use `-q` quiet mode (less logging overhead)

---

### Can python-dabmux run on a Raspberry Pi?

**Yes!** python-dabmux runs on Raspberry Pi 3 and later.

**Requirements:**
- Raspberry Pi 3 or newer (ARM processor)
- Python 3.11+
- 512 MB RAM minimum
- Recommended: Raspberry Pi 4 with 2+ GB RAM

**Performance:**
- RPi 3: 1-2 services comfortably
- RPi 4: 4-6 services

**Tips:**
- Use Raspberry Pi OS Lite (no GUI) for lower overhead
- Use file outputs or local network only (avoid Wi-Fi for streaming)
- Use `-q` quiet mode to reduce logging

---

### How much bandwidth does EDI use?

**Without PFT:**
- Approximately **bitrate × 1.15** (15% overhead for headers)
- Example: 6 services × 128 kbps = 768 kbps → ~880 kbps network traffic

**With PFT (no FEC):**
- Approximately **bitrate × 1.25** (25% overhead)
- Example: 768 kbps → ~960 kbps

**With PFT + FEC:**
- Depends on `--pft-fec-m` parameter
- Add **~10-20% more** for FEC redundancy
- Example: 768 kbps → ~1100 kbps (with m=2)

**Calculate for your setup:**
```
Total bitrate = sum of all subchannel bitrates
Network bandwidth = Total bitrate × (1.15 to 1.35)
```

---

## Transmission Questions

### What's the next step after generating ETI?

**ETI is just the multiplex data.** To broadcast, you need:

1. **Modulator:** Converts ETI to RF signal
   - Hardware: Professional DAB modulators
   - Software: ODR-DabMod (open source)

2. **Transmitter:** Amplifies and transmits RF signal
   - RF power amplifier
   - Antenna tuned for DAB frequencies

**Typical chain:**
```
python-dabmux → ETI → ODR-DabMod → RF → Transmitter → Antenna
```

**For testing:**
- Use SDR (Software-Defined Radio) with ODR-DabMod
- Desktop DAB radios can decode test transmissions

---

### What DAB frequencies can I use?

**Depends on your country and license!**

**DAB Band III (most common):**
- 174-240 MHz
- Channels 5A-13F
- Used in Europe, Asia, Australia

**DAB L-Band:**
- 1452-1492 MHz
- Used in some countries for local/mobile services

**Important:**
- **Broadcasting requires a license** in most countries
- Unlicensed transmission is illegal and interferes with licensed services
- **For testing:** Use very low power (<1 mW) in a shielded environment
- **For production:** Obtain proper broadcast license from your regulatory authority

---

### Can I receive python-dabmux output with a regular DAB radio?

**Yes, but you need a modulator!**

1. **Generate ETI:**
   ```bash
   dabmux -c config.yaml -o output.eti
   ```

2. **Modulate with ODR-DabMod:**
   ```bash
   odr-dabmod output.eti -o output.iq
   ```

3. **Transmit with SDR:**
   - HackRF, LimeSDR, USRP, etc.
   - Use very low power for testing

4. **Tune your DAB radio** to the configured frequency

**Warning:** Only transmit in a shielded environment or with proper license.

---

## Troubleshooting Questions

### Why am I getting "Invalid MPEG frame header"?

**Common causes:**

1. **Wrong file format:**
   - File is not MPEG Layer II
   - Use `file` and `ffprobe` to check format

2. **Corrupted file:**
   - Re-encode the audio file
   - Check disk integrity

3. **Wrong subchannel type:**
   - Type is `dabplus` but file is MPEG Layer II
   - Change type to `audio`

4. **Network stream issues:**
   - UDP packets arriving out of order
   - Incomplete frames
   - Try TCP instead of UDP

**Solution:**
```bash
# Verify file format
ffprobe audio.mp2

# Re-encode if needed
ffmpeg -i audio.mp2 -codec:a mp2 -b:a 128k audio_fixed.mp2
```

---

### Why can't python-dabmux find my configuration file?

**Common causes:**

1. **Wrong path:**
   ```bash
   # Check current directory
   pwd
   ls -l config.yaml
   ```

2. **Wrong filename:**
   ```bash
   # Maybe it's config.yml not config.yaml?
   ls -l *.yaml *.yml
   ```

3. **File in different directory:**
   ```bash
   # Use absolute path
   dabmux -c /full/path/to/config.yaml -o output.eti
   ```

**Solution:** Use absolute paths for production:
```bash
dabmux -c /etc/dabmux/config.yaml -o /var/dabmux/output.eti
```

---

### How do I debug configuration problems?

**Enable maximum verbosity:**
```bash
dabmux -c config.yaml -o test.eti -n 1 -vvv
```

**Check YAML syntax:**
- Use online YAML validators
- Check indentation (spaces, not tabs)
- Verify quotes around hex values

**Test with minimal config:**
```yaml
# Simplest possible config
ensemble:
  id: '0xCE15'
  label:
    text: 'Test'

subchannels:
  - uid: 'sub1'
    id: 0
    bitrate: 128
    input: 'file://audio.mp2'

services:
  - uid: 'svc1'
    id: '0x5001'
    label:
      text: 'Test'

components:
  - service_id: '0x5001'
    subchannel_id: 0
```

**See:** [Troubleshooting Guide](troubleshooting/index.md)

---

## Getting Help

### Where can I get more help?

1. **Documentation:**
   - [User Guide](user-guide/index.md)
   - [Tutorials](tutorials/index.md)
   - [Troubleshooting](troubleshooting/index.md)

2. **GitHub:**
   - [Issues](https://github.com/python-dabmux/python-dabmux/issues)
   - [Discussions](https://github.com/python-dabmux/python-dabmux/discussions)

3. **Community:**
   - OpenDigitalRadio community
   - DAB forums and mailing lists

---

### How can I contribute?

Contributions welcome!

1. **Report bugs:** [GitHub Issues](https://github.com/python-dabmux/python-dabmux/issues)
2. **Suggest features:** [GitHub Discussions](https://github.com/python-dabmux/python-dabmux/discussions)
3. **Submit code:** [Pull Requests](https://github.com/python-dabmux/python-dabmux/pulls)
4. **Improve documentation:** This documentation is in the `docs/` directory

**See:** [Contributing Guide](development/contributing.md)

---

## See Also

- [Getting Started](getting-started/index.md): Installation and first multiplex
- [User Guide](user-guide/index.md): Complete usage documentation
- [Tutorials](tutorials/index.md): Hands-on guides
- [Troubleshooting](troubleshooting/index.md): Problem solving
- [Glossary](glossary.md): DAB terminology
