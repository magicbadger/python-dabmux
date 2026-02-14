# ETI Files

Complete guide to ETI (Ensemble Transport Interface) file output.

## Overview

ETI files contain DAB multiplex data in binary format. Each file consists of sequential ETI frames that can be played out to a transmitter or archived.

**Key properties:**
- Binary format
- Fixed frame size (depends on transmission mode)
- Self-contained (includes all multiplex data)
- Standard format (ETSI EN 300 799)

---

## ETI Frame Structure

### Mode I Frame (Most Common)

**Total size:** 6144 bytes per frame

```
┌─────────────────────┬───────┐
│ Section             │ Bytes │
├─────────────────────┼───────┤
│ ERR                 │     1 │
│ FSYNC               │     3 │
│ FC (Frame Char.)    │     4 │
│ STC (Stream Char.)  │   4×N │  N = number of subchannels
│ EOH (End of Header) │     4 │
│ FIC (Fast Info)     │    96 │
│ MST (Main Service)  │  5760 │
│ EOF (End of Frame)  │     4 │
│ TIST (Timestamp)    │     4 │  Optional
└─────────────────────┴───────┘
```

### Frame Components

#### ERR (Error Status)
- 1 byte
- Indicates frame errors (normally 0x00)

#### FSYNC (Frame Synchronization)
- 3 bytes: `0x073AB6`
- Used to locate frame boundaries

#### FC (Frame Characterization)
- 4 bytes
- Contains mode, frame count, subfunctions

#### STC (Stream Characterization)
- 4 bytes per subchannel
- Subchannel ID, start address, length

#### EOH (End of Header)
- 4 bytes
- CRC of header (FC + STC)

#### FIC (Fast Information Channel)
- 96 bytes (Mode I)
- Contains FIGs (metadata)

#### MST (Main Service Transport)
- 5760 bytes (Mode I)
- Subchannel audio/data

#### EOF (End of Frame)
- 4 bytes
- CRC of frame

#### TIST (Timestamp)
- 4 bytes (optional)
- Frame timestamp for synchronization

---

## Basic File Output

### Generate ETI File

```bash
python -m dabmux.cli -c config.yaml -o output.eti
```

**Default behavior:**
- Generates frames until interrupted (Ctrl+C)
- Or until `-n` frame count reached

### Limited Frame Count

```bash
# Generate exactly 1000 frames
python -m dabmux.cli -c config.yaml -o output.eti -n 1000
```

**File size calculation:**
```
Mode I: 1000 frames × 6144 bytes = 6,144,000 bytes (~6 MB)
```

### Duration Calculation

**Mode I frame duration:** 96 ms

**Examples:**
- 1 second: ~10.42 frames
- 1 minute: ~625 frames (~3.75 MB)
- 1 hour: ~37,500 frames (~225 MB)
- 24 hours: ~900,000 frames (~5.4 GB)

**Calculate frames for duration:**
```bash
# 5 minutes of content
frames=$((5 * 60 * 1000 / 96))  # 3125 frames
python -m dabmux.cli -c config.yaml -o output.eti -n $frames
```

---

## Continuous Generation

### Loop Input Files

```bash
python -m dabmux.cli -c config.yaml -o output.eti --continuous
```

**Behavior:**
- Input files loop automatically at end
- Generates frames indefinitely
- Stop with Ctrl+C

**Use cases:**
- Test signal generation
- Looped content playout
- Long-running tests

---

## ETI with Timestamps

### Enable TIST

```bash
python -m dabmux.cli -c config.yaml -o output.eti --tist
```

**Adds 4-byte timestamp to each frame:**
- Resolution: ~61 nanoseconds
- Epoch: 1970-01-01 00:00:00 UTC
- Used for transmitter synchronization

**Frame size with TIST:**
- Mode I: 6144 + 4 = 6148 bytes per frame

**Purpose:**
- Single Frequency Networks (SFN)
- Multi-transmitter synchronization
- Precise timing reference

See [Timestamps](../../advanced/timestamps-sync.md) for details.

---

## File Management

### File Naming

**Date-based naming:**
```bash
python -m dabmux.cli -c config.yaml \
  -o "/archive/$(date +%Y%m%d_%H%M%S).eti"
```

**Example output:** `/archive/20260213_143022.eti`

**Sequential naming:**
```bash
#!/bin/bash
counter=0
while true; do
    python -m dabmux.cli -c config.yaml \
      -o "output_${counter}.eti" \
      -n 37500  # 1 hour
    counter=$((counter + 1))
done
```

### File Rotation

**Hourly rotation:**
```bash
#!/bin/bash
# Generate 1 hour ETI files continuously

while true; do
    filename="/archive/$(date +%Y%m%d_%H0000).eti"
    echo "Starting $filename"

    # 1 hour = ~37500 frames for Mode I
    python -m dabmux.cli -c config.yaml -o "$filename" -n 37500

    echo "Completed $filename"
done
```

**Using cron:**
```bash
# crontab -e
0 * * * * /usr/local/bin/generate_eti_hour.sh
```

---

## Verifying ETI Files

### Check File Size

```bash
# Mode I without TIST
ls -lh output.eti

# Should be multiple of 6144 bytes
size=$(stat -f%z output.eti)  # macOS
# size=$(stat -c%s output.eti)  # Linux

frames=$((size / 6144))
echo "File contains $frames frames"
```

### Verify Frame Sync

```bash
# Check for valid FSYNC pattern (0x073AB6)
hexdump -C output.eti | head -20 | grep "07 3a b6"
```

Expected output:
```
00000000  00 07 3a b6 ...
```

### Extract Frame Info

```python
#!/usr/bin/env python3
import struct

def read_eti_header(filename):
    with open(filename, 'rb') as f:
        err = struct.unpack('B', f.read(1))[0]
        fsync = f.read(3)
        fc = f.read(4)

        print(f"ERR: 0x{err:02X}")
        print(f"FSYNC: {fsync.hex()}")
        print(f"Frame valid: {fsync.hex() == '073ab6'}")

read_eti_header('output.eti')
```

---

## Playout to Transmitter

### Real-time Playout

**Using external tools:**

Most DAB modulators accept ETI files via stdin:

```bash
# Play ETI file at correct frame rate
python3 << 'EOF'
import time
import sys

FRAME_SIZE = 6144
FRAME_DURATION = 0.096  # 96 ms for Mode I

with open('output.eti', 'rb') as f:
    start_time = time.time()
    frame_num = 0

    while True:
        frame = f.read(FRAME_SIZE)
        if not frame:
            break

        sys.stdout.buffer.write(frame)
        sys.stdout.buffer.flush()

        # Wait for frame timing
        frame_num += 1
        expected_time = start_time + (frame_num * FRAME_DURATION)
        sleep_time = expected_time - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
EOF
```

### Looped Playout

```bash
#!/bin/bash
# Loop ETI file to modulator

while true; do
    # Read and send ETI frames with timing
    python3 playout_eti.py output.eti | nc modulator_ip modulator_port
done
```

---

## Converting ETI Files

### Extract Audio Stream

**Using ODR-DabMux tools (if available):**

```bash
# Extract subchannel 0
odr-eti2mpa output.eti -s 0 -o extracted.mp2
```

### Analyze ETI Content

**Frame count:**
```bash
size=$(stat -c%s output.eti)
frames=$((size / 6144))
duration=$(echo "scale=2; $frames * 0.096" | bc)
echo "$frames frames = $duration seconds"
```

**Example:**
```
37500 frames = 3600.00 seconds = 1 hour
```

---

## Storage and Archival

### Compression

ETI files compress well:

```bash
# gzip compression (~30-40% reduction)
gzip output.eti
# Creates output.eti.gz

# Decompress
gunzip output.eti.gz

# xz compression (~40-50% reduction)
xz -9 output.eti
# Creates output.eti.xz

# Decompress
unxz output.eti.xz
```

**Compression ratios (approximate):**
- gzip: 60-70% of original size
- xz: 50-60% of original size
- bzip2: 55-65% of original size

**1-hour file:**
- Original: ~225 MB
- gzipped: ~135-160 MB
- xz: ~110-135 MB

### Archive Script

```bash
#!/bin/bash
# Archive and compress ETI files

ARCHIVE_DIR="/archive"
SOURCE_DIR="/output"

# Move and compress files older than 1 day
find "$SOURCE_DIR" -name "*.eti" -mtime +1 | while read file; do
    echo "Archiving $file"
    xz -9 "$file"
    mv "${file}.xz" "$ARCHIVE_DIR/"
done

# Delete archives older than 30 days
find "$ARCHIVE_DIR" -name "*.eti.xz" -mtime +30 -delete
```

### Disk Space Management

**Monitor disk usage:**
```bash
#!/bin/bash
# Alert if disk usage > 80%

usage=$(df /archive | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$usage" -gt 80 ]; then
    echo "WARNING: Disk usage at ${usage}%"
    # Send alert (email, SMS, etc.)
    # Delete oldest files
    find /archive -name "*.eti.xz" -mtime +7 -delete
fi
```

---

## Advanced Usage

### Multiple Output Files

**Parallel generation:**
```bash
# Generate multiple configurations simultaneously

python -m dabmux.cli -c config1.yaml -o output1.eti -n 1000 &
python -m dabmux.cli -c config2.yaml -o output2.eti -n 1000 &
python -m dabmux.cli -c config3.yaml -o output3.eti -n 1000 &

wait
echo "All files generated"
```

### Combining with Network Output

```bash
# Write file AND stream to network
python -m dabmux.cli -c config.yaml \
  -o archive.eti \
  --edi udp://192.168.1.100:12000 \
  --continuous
```

**Use cases:**
- Live broadcast with archival
- Redundancy and backup
- Monitoring and analysis

---

## Troubleshooting

### File Too Small

**Problem:** File smaller than expected

**Check:**
```bash
# Mode I should be multiple of 6144
size=$(stat -c%s output.eti)
remainder=$((size % 6144))

if [ $remainder -ne 0 ]; then
    echo "ERROR: File size not multiple of frame size"
    echo "Size: $size, Remainder: $remainder"
fi
```

**Causes:**
- Process terminated early
- Disk full
- Permission denied

### Invalid FSYNC

**Problem:** File doesn't contain valid FSYNC

**Diagnosis:**
```bash
# Check first few bytes
hexdump -C output.eti | head -5
```

**Should see:** `00 07 3a b6` at start of each frame

**If not:**
- File corrupted
- Wrong file format
- Partial write

### Permission Denied

**Problem:**
```
ERROR: Cannot create output.eti: Permission denied
```

**Solutions:**
```bash
# Check directory permissions
ls -ld $(dirname output.eti)

# Create directory if needed
mkdir -p /output
chmod 755 /output

# Check user permissions
touch /output/test && rm /output/test
```

### Disk Full

**Problem:**
```
ERROR: Cannot write to output.eti: No space left on device
```

**Solutions:**
```bash
# Check disk space
df -h /output

# Free space
rm old_files*.eti
# Or compress
gzip old_files*.eti

# Set up monitoring
du -sh /output
```

---

## Best Practices

### File Generation

1. **Use absolute paths:** `/archive/output.eti` not `output.eti`
2. **Pre-check disk space:** Before long generation runs
3. **Use timestamped names:** Easy identification and organization
4. **Monitor generation:** Use `-v` for verbose output
5. **Test first:** Generate small files before production runs

### Storage

1. **Compress old files:** Save 40-50% disk space
2. **Regular rotation:** Move old files to archive
3. **Backup important files:** Off-site or cloud storage
4. **Monitor disk usage:** Alert before full
5. **Document naming scheme:** Consistent file naming

### Production

1. **Redundancy:** Generate to multiple disks
2. **Validation:** Check files after generation
3. **Monitoring:** Log file sizes and timing
4. **Automation:** Use scripts for rotation/archival
5. **Disaster recovery:** Have backup generation ready

---

## Examples

### Test File Generation

```bash
# Generate 10-second test file
frames=$((10 * 1000 / 96))  # ~104 frames
python -m dabmux.cli -c config.yaml -o test.eti -n $frames
```

### Hourly Archive

```bash
#!/bin/bash
# Generate 1-hour ETI file

DATE=$(date +%Y%m%d_%H0000)
OUTPUT="/archive/dab_${DATE}.eti"

echo "Generating $OUTPUT"
python -m dabmux.cli -c config.yaml -o "$OUTPUT" -n 37500

# Compress
echo "Compressing $OUTPUT"
xz -9 "$OUTPUT"

echo "Completed ${OUTPUT}.xz"
```

### Continuous with Daily Rotation

```bash
#!/bin/bash
# Generate ETI with daily file rotation

while true; do
    DATE=$(date +%Y%m%d)
    OUTPUT="/archive/dab_${DATE}.eti"

    echo "Starting $OUTPUT"

    # Generate until end of day
    end_of_day=$(date -d "tomorrow 00:00:00" +%s)
    now=$(date +%s)
    seconds=$((end_of_day - now))
    frames=$((seconds * 1000 / 96))

    python -m dabmux.cli -c config.yaml -o "$OUTPUT" -n $frames

    echo "Completed $OUTPUT"

    # Compress yesterday's file
    yesterday=$(date -d "yesterday" +%Y%m%d)
    if [ -f "/archive/dab_${yesterday}.eti" ]; then
        xz -9 "/archive/dab_${yesterday}.eti" &
    fi
done
```

---

## ETI File Structure Details

### Frame Header Fields

**FC (Frame Characterization) breakdown:**

```
Byte 0: FCT (Frame Count in ETI)
        - Incrementing counter (0-249)
        - Wraps around

Byte 1: NST (Number of Streams)
        - Number of subchannels
        - 0-63

Byte 2-3: Flags and subfunctions
```

### Complete Frame Dump

```python
#!/usr/bin/env python3
import struct

def dump_eti_frame(filename, frame_num=0):
    FRAME_SIZE = 6144
    with open(filename, 'rb') as f:
        f.seek(frame_num * FRAME_SIZE)

        # ERR
        err = struct.unpack('B', f.read(1))[0]
        print(f"ERR: 0x{err:02X}")

        # FSYNC
        fsync = f.read(3)
        print(f"FSYNC: {fsync.hex()}")

        # FC
        fc = f.read(4)
        fct = fc[0]
        nst = fc[1]
        print(f"Frame Count: {fct}")
        print(f"Num Subchannels: {nst}")

        # STC (4 bytes × NST)
        for i in range(nst):
            stc = f.read(4)
            scid = (stc[0] >> 2) & 0x3F
            sad = ((stc[0] & 0x03) << 8) | stc[1]
            stl = (stc[2] << 2) | (stc[3] >> 6)
            print(f"Subchannel {i}: ID={scid}, Start={sad}, Length={stl}")

dump_eti_frame('output.eti')
```

---

## See Also

- [Output Formats Overview](index.md): All output types
- [EDI Network](edi-network.md): Network streaming
- [PFT Fragmentation](pft-fragmentation.md): Forward error correction
- [Architecture: ETI Frames](../../architecture/eti-frames.md): Frame structure diagrams
- [CLI Reference](../cli-reference.md): Complete command options
