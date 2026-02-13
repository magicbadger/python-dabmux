# CLI Reference

Complete command-line interface reference for python-dabmux.

## Synopsis

```bash
python -m dabmux.cli [OPTIONS]
```

Or if installed globally:

```bash
dabmux [OPTIONS]
```

## Required Arguments

### `-c, --config FILE`

Path to the configuration file (YAML format).

**Example:**
```bash
dabmux -c config.yaml -o output.eti
dabmux --config /path/to/config.yaml -o output.eti
```

**See also:** [Configuration Reference](configuration/index.md)

## Output Options

You must specify **one** output option (file or EDI network).

### `-o, --output FILE`

Write ETI frames to a file.

**Example:**
```bash
dabmux -c config.yaml -o output.eti
dabmux -c config.yaml --output /path/to/output.eti
```

**File formats:**
- Raw ETI (`.eti`)
- Streamed ETI (with timestamps)
- Framed ETI (aligned frames)

**See also:** [ETI Files](outputs/eti-files.md)

### `--edi URL`

Send EDI output over the network (UDP or TCP).

**Format:** `udp://host:port` or `tcp://host:port`

**Example:**
```bash
# UDP unicast
dabmux -c config.yaml --edi udp://192.168.1.100:12000

# UDP multicast
dabmux -c config.yaml --edi udp://239.1.2.3:12000

# TCP
dabmux -c config.yaml --edi tcp://192.168.1.100:12000
```

**See also:** [EDI Network](outputs/edi-network.md)

## ETI File Format Options

### `-f, --format {raw,streamed,framed}`

ETI file output format. Only used with `-o/--output`.

**Default:** `framed`

**Options:**

- **`raw`**: Plain ETI frames with no additional structure
  - Smallest file size
  - No timing information
  - Compatible with most tools

- **`streamed`**: ETI frames with timing information
  - Includes timestamps
  - Useful for synchronized playback

- **`framed`**: Aligned ETI frames with delimiters
  - 8-byte aligned
  - Frame boundaries marked
  - Easiest to parse

**Example:**
```bash
# Raw ETI
dabmux -c config.yaml -o output.eti -f raw

# Streamed ETI (with timestamps)
dabmux -c config.yaml -o output.eti -f streamed

# Framed ETI (default)
dabmux -c config.yaml -o output.eti -f framed
```

## PFT Options

PFT (Protection, Fragmentation and Transport) options. Only used with `--edi`.

### `--pft`

Enable PFT for EDI output.

**Benefits:**
- Fragments large packets to fit MTU
- Adds sequence numbers
- Enables optional FEC

**Example:**
```bash
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft
```

**See also:** [PFT Fragmentation](outputs/pft-fragmentation.md)

### `--pft-fec`

Enable Forward Error Correction (FEC) for PFT.

**Requires:** `--pft`

**Benefits:**
- Recovers lost packets
- Uses Reed-Solomon encoding
- Increases bandwidth usage

**Example:**
```bash
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fec
```

**See also:** [Reed-Solomon FEC](../advanced/reed-solomon.md)

### `--pft-fec-m M`

Maximum number of recoverable fragments for PFT FEC.

**Requires:** `--pft` and `--pft-fec`

**Default:** `2`

**Range:** 1-20 (higher values = more recovery capability but more bandwidth)

**Example:**
```bash
# Can recover up to 5 lost fragments
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fec --pft-fec-m 5
```

**Trade-off:** Higher M = better error recovery but higher bandwidth usage.

### `--pft-fragment-size SIZE`

Maximum fragment size in bytes for PFT.

**Requires:** `--pft`

**Default:** `1400`

**Typical values:**
- `1400`: Safe for standard Ethernet (1500 MTU)
- `1200`: Conservative for networks with overhead
- `8000`: Jumbo frames (if supported)

**Example:**
```bash
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fragment-size 1200
```

**Note:** Must be smaller than network MTU to avoid IP fragmentation.

## Frame Generation Options

### `-n, --num-frames N`

Number of ETI frames to generate.

**Default:** `1`

**Example:**
```bash
# Generate 100 frames
dabmux -c config.yaml -o output.eti -n 100

# Generate 10,000 frames (about 16 minutes of Mode I)
dabmux -c config.yaml -o output.eti --num-frames 10000
```

**Calculation:**
- Mode I: 96 ms per frame (625 frames ≈ 1 minute)
- Mode II: 24 ms per frame (2500 frames ≈ 1 minute)

### `--continuous`

Generate frames continuously until interrupted (Ctrl+C).

**Behavior:**
- Loops input files when they reach the end
- Runs indefinitely until stopped
- Useful for live transmission

**Example:**
```bash
# Run until stopped
dabmux -c config.yaml -o output.eti --continuous

# Stream EDI continuously
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --continuous
```

**Stop:** Press `Ctrl+C` to gracefully stop.

## Timestamp Options

### `--tist`

Enable TIST (Time-Stamp) field in ETI frames.

**Use cases:**
- Synchronized multi-transmitter networks (SFN)
- Timed playback
- Precise frame timing

**Example:**
```bash
dabmux -c config.yaml -o output.eti --tist
```

**See also:** [Timestamps & Sync](../advanced/timestamps-sync.md)

### `--tist-offset MS`

TIST offset in milliseconds.

**Requires:** `--tist`

**Default:** `0.0`

**Use cases:**
- Compensate for processing delays
- Align multiple multiplexers
- Add fixed delay

**Example:**
```bash
# Add 100ms offset
dabmux -c config.yaml -o output.eti --tist --tist-offset 100.0

# Negative offset (advance)
dabmux -c config.yaml -o output.eti --tist --tist-offset -50.0
```

## Logging Options

### `-v, --verbose`

Increase verbosity level. Can be repeated.

**Levels:**
- No `-v`: Warnings and errors only
- `-v`: Warnings, errors
- `-vv`: Info, warnings, errors
- `-vvv`: Debug, info, warnings, errors

**Example:**
```bash
# Normal verbosity
dabmux -c config.yaml -o output.eti

# Info messages
dabmux -c config.yaml -o output.eti -vv

# Debug messages
dabmux -c config.yaml -o output.eti -vvv
```

### `-q, --quiet`

Quiet mode (errors only).

**Use case:** When you only want to see errors, no progress or status messages.

**Example:**
```bash
dabmux -c config.yaml -o output.eti -q
```

**Note:** Mutually exclusive with `-v`.

## Version and Help

### `--version`

Show version and exit.

**Example:**
```bash
dabmux --version
```

**Output:**
```
python-dabmux 0.6.0
```

### `-h, --help`

Show help message and exit.

**Example:**
```bash
dabmux --help
```

## Complete Examples

### Basic Single Service

Generate 1000 frames from a single audio service:

```bash
dabmux -c basic_config.yaml -o output.eti -n 1000
```

### Multi-Service Ensemble

Generate a multi-service ensemble with debug logging:

```bash
dabmux -c multi_service.yaml -o output.eti -n 5000 -vvv
```

### Network Streaming with PFT

Stream EDI over UDP multicast with PFT and FEC:

```bash
dabmux -c config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --pft-fec \
  --pft-fec-m 3 \
  --continuous
```

### Live Transmission

Continuous operation with timestamps:

```bash
dabmux -c live_config.yaml \
  --edi udp://239.1.2.3:12000 \
  --pft \
  --tist \
  --continuous \
  -vv
```

### Timed Recording

Generate exactly 10 minutes of Mode I frames (6250 frames):

```bash
dabmux -c config.yaml \
  -o recording.eti \
  -n 6250 \
  -f framed \
  --tist
```

### Development Testing

Quick test with raw ETI output:

```bash
dabmux -c test_config.yaml -o test.eti -f raw -n 10 -q
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Configuration file not found |
| `1` | Configuration error (invalid YAML, validation failed) |
| `1` | Output error (can't write file, network unreachable) |
| `1` | Unexpected error |

## Common Usage Patterns

### File Output Workflow

1. **Create configuration:** `config.yaml`
2. **Test with a few frames:**
   ```bash
   dabmux -c config.yaml -o test.eti -n 10
   ```
3. **Generate full output:**
   ```bash
   dabmux -c config.yaml -o output.eti -n 10000
   ```

### Network Streaming Workflow

1. **Test configuration:**
   ```bash
   dabmux -c config.yaml -o test.eti -n 1
   ```
2. **Start streaming:**
   ```bash
   dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --continuous
   ```
3. **Monitor logs:**
   ```bash
   dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --continuous -vv
   ```

### Debugging Workflow

1. **Enable debug logging:**
   ```bash
   dabmux -c config.yaml -o debug.eti -n 10 -vvv
   ```
2. **Check frame generation:**
   ```bash
   hexdump -C debug.eti | head
   ```
3. **Verify configuration:**
   ```bash
   dabmux -c config.yaml --help
   ```

## Environment Variables

python-dabmux respects standard Python environment variables:

- `PYTHONPATH`: Additional module search paths
- `PYTHONUNBUFFERED`: Unbuffered output (useful for logging)

**Example:**
```bash
PYTHONUNBUFFERED=1 dabmux -c config.yaml -o output.eti --continuous
```

## Configuration File Format

See [Configuration Reference](configuration/index.md) for complete YAML configuration format.

## Performance Tips

1. **Use raw format for large files:** Smallest file size
   ```bash
   dabmux -c config.yaml -o output.eti -f raw
   ```

2. **Disable logging for production:** Use `-q` for minimal overhead
   ```bash
   dabmux -c config.yaml -o output.eti -q --continuous
   ```

3. **Adjust PFT fragment size:** Match your network MTU
   ```bash
   dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fragment-size 1400
   ```

4. **Use TCP for reliable delivery:** When packet loss is unacceptable
   ```bash
   dabmux -c config.yaml --edi tcp://192.168.1.100:12000
   ```

## Troubleshooting

### Configuration Not Found

```
ERROR: Configuration file not found: config.yaml
```

**Solution:** Check file path and current directory:
```bash
ls -l config.yaml
dabmux -c /absolute/path/to/config.yaml -o output.eti
```

### Invalid EDI URL

```
ERROR: Invalid EDI URL: 239.1.2.3:12000 (must start with udp:// or tcp://)
```

**Solution:** Add protocol prefix:
```bash
dabmux -c config.yaml --edi udp://239.1.2.3:12000
```

### Permission Denied

```
ERROR: Permission denied: output.eti
```

**Solution:** Check file permissions or write to a different location:
```bash
chmod 644 output.eti  # Fix permissions
# Or write elsewhere
dabmux -c config.yaml -o /tmp/output.eti
```

### Network Unreachable

```
ERROR: Network unreachable: 239.1.2.3:12000
```

**Solution:** Check network configuration:
```bash
# Test connectivity
ping 239.1.2.3
# Check multicast routes
netstat -rn | grep 239
```

## See Also

- [Configuration Reference](configuration/index.md): Complete YAML configuration
- [ETI Files](outputs/eti-files.md): ETI file format details
- [EDI Network](outputs/edi-network.md): EDI network output
- [Troubleshooting](../troubleshooting/common-errors.md): Common errors and solutions
- [Examples](configuration/examples.md): Configuration examples
