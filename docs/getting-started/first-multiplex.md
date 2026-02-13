# Your First Multiplex

In this tutorial, you'll create your first DAB ensemble and generate ETI output. We'll start simple with a single radio station.

## What We'll Build

A basic DAB ensemble with:

- One radio station: "Radio One"
- 128 kbps MPEG Layer II audio
- ETI file output

## Step 1: Prepare Audio Input

python-dabmux needs MPEG Layer II audio files as input. For this tutorial, you can either:

1. Use your own MPEG Layer II files (`.mp2` extension)
2. Or create a test file from any audio using ffmpeg:

```bash
# Install ffmpeg if needed
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
# Windows: Download from ffmpeg.org

# Convert any audio file to MPEG Layer II
ffmpeg -i input.wav -codec:a mp2 -b:a 128k audio.mp2
```

Place your `audio.mp2` file in a directory where you'll run python-dabmux.

## Step 2: Create Configuration File

Create a file named `config.yaml` with the following content:

```yaml
# Basic DAB Multiplex Configuration

ensemble:
  # Ensemble ID - a unique 16-bit identifier
  id: '0xCE15'

  # Extended Country Code - 0xE1 for Germany
  ecc: '0xE1'

  # Transmission mode - I is most common (1536 kHz bandwidth)
  transmission_mode: 'I'

  # Ensemble label (visible to listeners)
  label:
    text: 'My First DAB'
    short: 'DAB'

  # Automatic local time offset
  lto_auto: true

# Subchannels define the audio streams
subchannels:
  - uid: 'audio1'              # Unique identifier
    id: 0                      # Subchannel ID (0-63)
    type: 'audio'              # Type: audio, dabplus, packet, data
    bitrate: 128               # 128 kbps
    start_address: 0           # Start position in Capacity Units
    protection:
      level: 2                 # Protection level (0=weakest, 4=strongest)
      shortform: true          # Use short form protection table
    input: 'file://audio.mp2'  # Path to input file

# Services define the radio stations
services:
  - uid: 'service1'
    id: '0x5001'               # Service ID (unique 16-bit hex)
    label:
      text: 'Radio One'        # Station name (max 16 characters)
      short: 'Radio1'          # Short name (max 8 characters)
    pty: 1                     # Programme Type (1=News)
    language: 9                # Language code (9=English)

# Components link services to subchannels
components:
  - uid: 'comp1'
    service_id: '0x5001'       # Must match a service ID above
    subchannel_id: 0           # Must match a subchannel ID above
    type: 0                    # Component type (0=Audio)
```

## Step 3: Run the Multiplexer

Now run python-dabmux with your configuration:

```bash
python -m dabmux.cli -c config.yaml -o output.eti
```

You should see output like:

```
INFO: Loading configuration from config.yaml
INFO: Created ensemble 'My First DAB' (0xCE15)
INFO: Added service 'Radio One' (0x5001)
INFO: Added subchannel 0: audio, 128 kbps, protection level 2
INFO: Starting multiplexer
INFO: Generated 1000 ETI frames
INFO: Output written to output.eti
INFO: Multiplexing complete
```

## Step 4: Verify the Output

Check that the ETI file was created:

```bash
# Check file size (should be around 6 MB for 1000 frames)
ls -lh output.eti

# File info
file output.eti
```

## Understanding What Just Happened

Let's break down what python-dabmux did:

1. **Loaded Configuration**: Read `config.yaml` and validated all parameters
2. **Created Ensemble**: Set up a DAB ensemble with ID 0xCE15
3. **Added Service**: Created "Radio One" service with label and metadata
4. **Configured Subchannel**: Allocated bandwidth for 128 kbps audio with protection level 2
5. **Opened Input**: Connected to `audio.mp2` file
6. **Generated FIGs**: Created Fast Information Groups with ensemble and service information
7. **Multiplexed Frames**: Combined audio data with FIGs into ETI frames
8. **Wrote Output**: Saved ETI frames to `output.eti`

## Step 5: Explore Configuration Options

### Change the Station Name

Edit the service label in `config.yaml`:

```yaml
services:
  - uid: 'service1'
    id: '0x5001'
    label:
      text: 'My Cool Radio'    # Changed!
      short: 'MyCool'          # Changed!
```

### Adjust Audio Bitrate

Change the subchannel bitrate:

```yaml
subchannels:
  - uid: 'audio1'
    bitrate: 192               # Higher quality (was 128)
```

### Use a Different Input File

Point to another audio file:

```yaml
subchannels:
  - uid: 'audio1'
    input: 'file:///path/to/other/audio.mp2'  # Full path
```

## Common Configuration Mistakes

### Wrong Input Path

❌ **Wrong:**
```yaml
input: 'audio.mp2'  # Missing file:// prefix
```

✅ **Correct:**
```yaml
input: 'file://audio.mp2'  # With prefix
```

### Mismatched IDs

❌ **Wrong:**
```yaml
components:
  - service_id: '0x5001'      # Service ID
    subchannel_id: 1          # But subchannel has id: 0
```

✅ **Correct:**
```yaml
components:
  - service_id: '0x5001'      # Matches service above
    subchannel_id: 0          # Matches subchannel above
```

### Invalid Bitrate

❌ **Wrong:**
```yaml
bitrate: 150  # Not a standard DAB bitrate
```

✅ **Correct:**
```yaml
bitrate: 128  # Valid: 32, 48, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384
```

## Next Steps

Now that you've created a basic multiplex, try:

### Add More Stations

See [Multi-Service Ensemble Tutorial](../tutorials/multi-service-ensemble.md) to add multiple radio stations.

### Network Output

Instead of files, output EDI over the network:

```bash
python -m dabmux.cli -c config.yaml --edi udp://239.1.2.3:12000
```

See [Network Streaming Tutorial](../tutorials/network-streaming.md).

### Continuous Operation

Loop the input file for continuous transmission:

```bash
python -m dabmux.cli -c config.yaml -o output.eti --continuous
```

### DAB+ (HE-AAC v2)

Use DAB+ for better audio quality at lower bitrates:

See [DAB+ Setup Tutorial](../tutorials/dab-plus-setup.md).

## Troubleshooting

### Input File Not Found

```
ERROR: Input file not found: audio.mp2
```

**Solution**: Check the file path. Use absolute paths if needed:

```yaml
input: 'file:///home/user/audio.mp2'  # Linux/macOS
input: 'file://C:/Users/user/audio.mp2'  # Windows
```

### Invalid Frame Size

```
ERROR: Invalid MPEG frame header
```

**Solution**: Ensure your input file is MPEG Layer II format:

```bash
ffmpeg -i input.wav -codec:a mp2 -b:a 128k audio.mp2
```

### Configuration Errors

```
ERROR: Invalid configuration: Unknown key 'labeltext'
```

**Solution**: Check YAML syntax. Common issues:
- Incorrect indentation (use spaces, not tabs)
- Typos in key names
- Missing quotes around hex values

## Learn More

- [Basic Concepts](basic-concepts.md): Understand DAB terminology
- [Configuration Reference](../user-guide/configuration/index.md): All configuration options
- [CLI Reference](../user-guide/cli-reference.md): All command-line options
- [Tutorials](../tutorials/index.md): More hands-on guides

## Summary

Congratulations! You've created your first DAB multiplex. You learned how to:

- ✅ Create a YAML configuration file
- ✅ Define ensemble, services, and subchannels
- ✅ Run the multiplexer with CLI
- ✅ Generate ETI output files

Continue to [Basic Concepts](basic-concepts.md) to deepen your understanding, or jump into [Tutorials](../tutorials/index.md) for more advanced scenarios.
