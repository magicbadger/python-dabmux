# python-dabmux Examples

This directory contains example configurations for common use cases.

## Quick Start

### 1. Simple Single Service

The simplest configuration with one audio service:

```bash
# Encode audio
odr-audioenc -i music.wav -o music.dabp -b 48 --aaclc -r 48000

# Generate ETI
python -m dabmux.cli -c examples/01_simple_single_service.yaml -o output.eti -f raw

# Test playback
dablin output.eti
```

**Files:** `01_simple_single_service.yaml`

### 2. Multi-Service Multiplex

Multiple services at different bitrates:

```bash
# Encode all services
odr-audioenc -i music.wav -o music.dabp -b 64 --aaclc -r 48000
odr-audioenc -i news.wav -o news.dabp -b 48 --aaclc -r 48000
odr-audioenc -i talk.wav -o talk.dabp -b 32 --aaclc -r 48000 --mono

# Generate ETI
python -m dabmux.cli -c examples/02_multi_service.yaml -o output.eti -f raw
```

**Files:** `02_multi_service.yaml`

### 3. Live Streaming (UDP)

Network-based live streaming:

```bash
# On encoder machine
odr-audioenc -i /dev/audio -o udp://mux-server:9000 -b 48 --aaclc -r 48000

# On multiplexer machine
python -m dabmux.cli -c examples/03_live_streaming_udp.yaml -o output.eti -f raw
```

**Files:** `03_live_streaming_udp.yaml`

### 4. Live Streaming (FIFO)

Local live streaming via named pipes:

```bash
# Create FIFOs
mkfifo /tmp/station1.fifo /tmp/station2.fifo

# Start encoders (background)
odr-audioenc -i /dev/audio -o /tmp/station1.fifo -b 48 --aaclc -r 48000 &
odr-audioenc -i music.wav -o /tmp/station2.fifo -b 64 --aaclc -r 48000 &

# Start multiplexer
python -m dabmux.cli -c examples/04_live_streaming_fifo.yaml -o output.eti -f raw
```

**Files:** `04_live_streaming_fifo.yaml`

## Configuration Reference

### Ensemble Settings

```yaml
ensemble:
  id: 0xCE15              # 16-bit hex identifier
  label: "My Ensemble"    # Up to 16 characters
  short_label: "MyEns"    # Up to 8 characters
  ecc: 0xE1              # Extended Country Code
```

### Service Settings

```yaml
services:
  - uid: service1         # Unique identifier
    sid: 0x5001          # Service ID (16-bit hex)
    label: "Station"     # Up to 16 characters
    short_label: "Stn"   # Up to 8 characters
    type: audio          # Service type
    bitrate: 48          # Bitrate in kbps
    subchannel: service1 # Subchannel reference
    protection_level: 3  # Error protection (1-5)
```

### Subchannel Settings

```yaml
subchannels:
  - uid: service1
    bitrate: 48              # Must match service bitrate
    protection: EEP_3A       # Protection type (recommended for DAB+)
    input_uri: file://audio.dabp  # Input source
```

### Input URI Formats

**File Input:**
```yaml
input_uri: file:///path/to/audio.dabp
input_uri: /path/to/audio.dabp  # file:// prefix optional
```

**UDP Input:**
```yaml
input_uri: udp://0.0.0.0:9000  # Listen on all interfaces
input_uri: udp://127.0.0.1:9000  # Listen on localhost only
```

**FIFO Input:**
```yaml
input_uri: fifo:///tmp/audio.fifo
```

## Bitrate Recommendations

| Content Type | Bitrate | Quality | Use Case |
|--------------|---------|---------|----------|
| Speech       | 24 kbps | Good    | Talk radio, podcasts |
| Talk + Music | 32 kbps | Good    | Mixed content |
| Music        | 48 kbps | Acceptable | Space-constrained |
| Music        | 64 kbps | Good    | Standard quality |
| Music        | 80 kbps | Very Good | High quality |
| Music        | 96 kbps | Premium | Best quality |

## Protection Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| 1     | Minimal protection | Studio/cable transmission |
| 2     | Low protection | Good RF conditions |
| **3** | **Medium (recommended)** | **Normal broadcasting** |
| 4     | High protection | Poor RF conditions |
| 5     | Maximum protection | Severe interference |

**Note:** Level 3 (EEP_3A) is recommended for most DAB+ services.

## Capacity Planning

DAB Mode I capacity: ~1200 kbps total

Example allocations:
- **4 services @ 48 kbps** = 192 kbps (leaves ~1000 kbps for more)
- **3 services @ 64 kbps** = 192 kbps
- **2 services @ 96 kbps** = 192 kbps
- **Mixed:** 2×96 + 2×64 + 2×48 = 416 kbps

Remember to account for FEC overhead (~25%) when planning capacity.

## Testing

### With dablin (DAB player)

```bash
# Play ETI file
dablin output.eti

# Select specific service
dablin -s 0x5001 output.eti

# Verbose output
dablin -v output.eti
```

### With etisnoop (ETI analyzer)

```bash
# Analyze ETI structure
etisnoop output.eti

# Verbose analysis
etisnoop -v output.eti
```

## Troubleshooting

### "Failed to open DAB+ input"

**Cause:** Input file doesn't exist or is not a valid .dabp file

**Solution:**
1. Check file path is correct
2. Verify file was created by odr-audioenc
3. Ensure bitrate in config matches encoded bitrate

### "PAD/DLS not supported"

**Cause:** Trying to add PAD to pre-encoded .dabp files

**Solution:** PAD must be encoded during audio encoding:
```bash
odr-audioenc -i music.wav -o music.dabp -b 48 --pad 58 --dls nowplaying.txt
```

### "UDP buffer overflow"

**Cause:** Network too slow or multiplexer overloaded

**Solution:**
1. Check network latency
2. Reduce number of services
3. Use FIFO for local streaming instead

## Advanced Topics

### Custom Protection Profiles

```yaml
subchannels:
  - uid: service1
    bitrate: 48
    protection: UEP_3  # Unequal Error Protection
    # Or custom EEP
    protection: EEP_2B
```

### Multiple Output Formats

Generate ETI in multiple formats simultaneously by running multiple instances
or using output duplication.

## Further Reading

- [ODR-DabMux Documentation](https://github.com/Opendigitalradio/ODR-DabMux)
- [ODR-AudioEnc Documentation](https://github.com/Opendigitalradio/ODR-AudioEnc)
- [ETSI DAB Standards](https://www.etsi.org/technologies/radio/dab)

## License

These examples are provided as-is for educational and testing purposes.
