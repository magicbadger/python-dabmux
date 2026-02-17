# DAB+ Examples

This directory contains example configurations for the python-dabmux DAB multiplexer.

## mexico_example.yaml

Complete working example demonstrating DAB+ (HE-AAC v2) audio broadcasting.

### Prerequisites

- [odr-audioenc](https://github.com/Opendigitalradio/ODR-AudioEnc) - DAB+ audio encoder
- [dablin](https://github.com/Opendigitalradio/dablin) - DAB/DAB+ player (optional, for testing)

### Workflow

#### 1. Encode audio to DAB+ format (.dabp)

```bash
# Convert source to WAV
ffmpeg -i mexico.aac -ar 48000 -ac 2 mexico_audio.wav

# Encode with odr-audioenc
odr-audioenc -i mexico_audio.wav -b 48 -c 2 -r 48000 --ps -o mexico_encoded.dabp
```

**Parameters:**
- `-b 48`: 48 kbps bitrate
- `-c 2`: Stereo (2 channels)
- `-r 48000`: 48 kHz sample rate
- `--ps`: Enable Parametric Stereo (for HE-AAC v2)

#### 2. Generate ETI file

```bash
python -m dabmux.cli -c examples/mexico_example.yaml -o mexico_example.eti -f raw -n 300
```

**Parameters:**
- `-c`: Configuration file
- `-o`: Output ETI file
- `-f raw`: RAW format (for dablin compatibility)
- `-n 300`: Generate 300 frames (~7 seconds)

#### 3. Play with dablin

```bash
dablin -s 0x5001 < mexico_example.eti
```

### Configuration Details

**Ensemble:**
- ID: `0xCE15`
- ECC: `0xE1` (Europe)
- Label: "Mexico DAB+"

**Service:**
- ID: `0x5001`
- Label: "Mexico Music"

**Subchannel:**
- Type: DAB+ (HE-AAC v2)
- Bitrate: 48 kbps
- Protection: UEP level 2
- Input: Pre-encoded .dabp file from odr-audioenc

### Technical Notes

**DAB+ File Format (.dabp):**
- Contains RS(120,110) error correction already applied
- Superframe size: `(bitrate / 8) * 120` bytes
  - For 48 kbps: 720 bytes per superframe
- Access Unit (AU) size: `superframe_size / 5`
  - For 48 kbps: 144 bytes per AU
- Each superframe covers 5 ETI frames (120ms total, 24ms per frame)

**Supported Bitrates:**
- 24 kbps: 360 bytes/superframe, 72 bytes/AU
- 32 kbps: 480 bytes/superframe, 96 bytes/AU
- 48 kbps: 720 bytes/superframe, 144 bytes/AU
- 64 kbps: 960 bytes/superframe, 192 bytes/AU
- 80 kbps: 1200 bytes/superframe, 240 bytes/AU

### Expected Output

```
FICDecoder: EId 0xCE15: ensemble label 'Mexico DAB+'
FICDecoder: SId 0x5001: programme service label 'Mexico Music'
EnsemblePlayer: format: HE-AAC v2, 48 kHz Stereo @ 48 kBit/s
[Clean audio playback with smooth timer progression]
```

### Troubleshooting

**No audio output:**
- Verify .dabp file is correctly encoded with odr-audioenc
- Check bitrate in config matches encoding bitrate
- Ensure file path in config is absolute (starting with `file://`)

**"(AU #2)" warnings:**
- This indicates AU alignment issues
- Verify using latest DABPFileInput implementation
- Confirm file size is exact multiple of superframe size (720 bytes for 48 kbps)

**Format not detected:**
- Ensure audio was encoded with `--ps` flag for HE-AAC v2
- Check that sample rate is 48 kHz
