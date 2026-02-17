# Common Errors

This guide covers the most common errors you'll encounter with python-dabmux and how to solve them.

## Configuration Errors

### 1. Configuration File Not Found

**Error:**
```
ERROR: Configuration file not found: config.yaml
```

**Cause:** The configuration file doesn't exist or the path is wrong.

**Solutions:**
```bash
# Check if file exists
ls -l config.yaml

# Use absolute path
dabmux -c /full/path/to/config.yaml -o output.eti

# Check current directory
pwd
```

---

### 2. Missing Ensemble Section

**Error:**
```
ERROR: Missing 'ensemble' section in configuration
```

**Cause:** Configuration file doesn't have required `ensemble:` section.

**Solution:**
```yaml
# Add ensemble section at the top
ensemble:
  id: '0xCE15'
  ecc: '0xE1'
  transmission_mode: 'I'
  label:
    text: 'My Ensemble'
```

---

### 3. Invalid Hex Value Format

**Error:**
```
ERROR: Invalid value for ensemble ID: CE15
```

**Cause:** Hex values must be quoted and start with `0x`.

**Wrong:**
```yaml
ensemble:
  id: CE15          # Missing 0x prefix and quotes
  ecc: E1           # Missing 0x prefix and quotes
```

**Correct:**
```yaml
ensemble:
  id: '0xCE15'      # Quoted with 0x prefix
  ecc: '0xE1'       # Quoted with 0x prefix
```

---

### 4. YAML Indentation Error

**Error:**
```
ERROR: YAML parse error: mapping values are not allowed here
```

**Cause:** Incorrect indentation (tabs vs spaces, wrong number of spaces).

**Wrong:**
```yaml
ensemble:
 id: '0xCE15'       # 1 space (inconsistent)
  ecc: '0xE1'       # 2 spaces
    label:          # 4 spaces (should be 2)
    text: 'DAB'     # 4 spaces (should be 4)
```

**Correct:**
```yaml
ensemble:
  id: '0xCE15'      # 2 spaces
  ecc: '0xE1'       # 2 spaces
  label:            # 2 spaces
    text: 'DAB'     # 4 spaces (nested)
```

**Tip:** Use spaces, not tabs. Most editors have "Convert tabs to spaces" option.

---

### 5. Mismatched Service ID

**Error:**
```
ERROR: Component references unknown service_id: 0x5999
```

**Cause:** Component `service_id` doesn't match any service `id`.

**Wrong:**
```yaml
services:
  - id: '0x5001'    # Service ID is 0x5001
components:
  - service_id: '0x5999'  # References non-existent service!
```

**Correct:**
```yaml
services:
  - id: '0x5001'
components:
  - service_id: '0x5001'  # Matches service above
```

---

### 6. Mismatched Subchannel ID

**Error:**
```
ERROR: Component references unknown subchannel_id: 5
```

**Cause:** Component `subchannel_id` doesn't match any subchannel `id`.

**Wrong:**
```yaml
subchannels:
  - id: 0           # Subchannel ID is 0
components:
  - subchannel_id: 5  # References non-existent subchannel!
```

**Correct:**
```yaml
subchannels:
  - id: 0
components:
  - subchannel_id: 0  # Matches subchannel above
```

---

### 7. Invalid Bitrate

**Error:**
```
ERROR: Invalid bitrate: 150 (not a standard DAB bitrate)
```

**Cause:** Bitrate is not a standard DAB value.

**Standard DAB bitrates:** 32, 48, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384

**Wrong:**
```yaml
bitrate: 150      # Not standard
```

**Correct:**
```yaml
bitrate: 160      # Standard DAB bitrate
```

---

### 8. Invalid Protection Level

**Error:**
```
ERROR: Protection level must be 0-4, got: 5
```

**Cause:** Protection level out of valid range.

**Valid range:** 0 (weakest) to 4 (strongest)

**Wrong:**
```yaml
protection:
  level: 5        # Too high
```

**Correct:**
```yaml
protection:
  level: 2        # Valid (0-4)
```

---

## Input Errors

### 9. Input File Not Found

**Error:**
```
ERROR: Input file not found: audio.mp2
```

**Cause:** Audio file doesn't exist or path is wrong.

**Solutions:**
```bash
# Check if file exists
ls -l audio.mp2

# Use absolute path in config
```

```yaml
# Relative path (from current directory)
input: 'file://audio.mp2'

# Absolute path (recommended for production)
input: 'file:///absolute/path/to/audio.mp2'
```

---

### 10. Missing file:// Prefix

**Error:**
```
ERROR: Invalid input URI: audio.mp2
```

**Cause:** Input path must start with `file://`, `udp://`, or `tcp://`.

**Wrong:**
```yaml
input: 'audio.mp2'          # Missing protocol
input: '/path/to/audio.mp2' # Missing protocol
```

**Correct:**
```yaml
input: 'file://audio.mp2'            # Relative path
input: 'file:///path/to/audio.mp2'   # Absolute path
```

---

### 11. Invalid MPEG Frame Header

**Error:**
```
ERROR: Invalid MPEG frame header in file: audio.mp2
```

**Cause:** Input file is not valid MPEG Layer II audio.

**Solutions:**

1. **Verify file format:**
   ```bash
   file audio.mp2
   ffprobe audio.mp2
   ```

2. **Convert to MPEG Layer II:**
   ```bash
   ffmpeg -i input.wav -codec:a mp2 -b:a 128k audio.mp2
   ```

3. **Check encoding parameters:**
   - Must be MPEG-1 Audio Layer II
   - Bitrate must match configuration
   - Sample rate: 24000, 32000, or 48000 Hz

---

### 12. Network Input Connection Failed

**Error:**
```
ERROR: Failed to connect to UDP source: 239.1.2.3:5001
```

**Causes:**
- Network interface not configured for multicast
- Firewall blocking UDP traffic
- Wrong IP address or port

**Solutions:**

1. **Test network connectivity:**
   ```bash
   # Test UDP port is open
   nc -u -l 5001

   # Check multicast routes
   netstat -rn | grep 239
   ```

2. **Configure multicast (Linux):**
   ```bash
   # Add multicast route
   sudo route add -net 224.0.0.0 netmask 240.0.0.0 dev eth0
   ```

3. **Check firewall:**
   ```bash
   # Linux (ufw)
   sudo ufw allow 5001/udp

   # Linux (iptables)
   sudo iptables -A INPUT -p udp --dport 5001 -j ACCEPT
   ```

---

### 13. Input Buffer Underrun

**Error:**
```
WARNING: Input buffer underrun on subchannel 0
```

**Cause:** Input source can't provide data fast enough.

**Solutions:**

1. **For file inputs:**
   - Check file is not corrupted
   - Ensure disk I/O is fast enough
   - Use local storage, not network drives

2. **For network inputs:**
   - Check network bandwidth
   - Reduce network congestion
   - Use wired instead of wireless
   - Increase buffer size (if supported)

3. **For continuous operation:**
   ```bash
   # Use --continuous to loop inputs
   dabmux -c config.yaml -o output.eti --continuous
   ```

---

### 14. Wrong Audio Format (DAB vs DAB+)

**Error:**
```
ERROR: Expected DAB+ superframe, got MPEG frame
```

**Cause:** Subchannel type doesn't match input audio format.

**Wrong:**
```yaml
subchannels:
  - type: 'dabplus'            # DAB+ type
    input: 'file://audio.mp2'  # But input is MPEG (DAB)
```

**Correct:**
```yaml
# For MPEG Layer II files
subchannels:
  - type: 'audio'              # DAB type
    input: 'file://audio.mp2'

# For HE-AAC files
subchannels:
  - type: 'dabplus'            # DAB+ type
    input: 'file://audio.aac'
```

---

## Output Errors

### 15. Cannot Write Output File

**Error:**
```
ERROR: Permission denied: output.eti
```

**Causes:**
- No write permission in directory
- File already exists and is read-only
- Disk full

**Solutions:**

1. **Check permissions:**
   ```bash
   # Check directory permissions
   ls -ld .

   # Fix permissions
   chmod 755 .
   chmod 644 output.eti
   ```

2. **Check disk space:**
   ```bash
   df -h .
   ```

3. **Use different output location:**
   ```bash
   dabmux -c config.yaml -o /tmp/output.eti
   ```

---

### 16. Invalid EDI URL

**Error:**
```
ERROR: Invalid EDI URL: 239.1.2.3:12000 (must start with udp:// or tcp://)
```

**Cause:** EDI URL missing protocol prefix.

**Wrong:**
```bash
dabmux -c config.yaml --edi 239.1.2.3:12000
```

**Correct:**
```bash
# UDP
dabmux -c config.yaml --edi udp://239.1.2.3:12000

# TCP
dabmux -c config.yaml --edi tcp://192.168.1.100:12000
```

---

### 17. Network Unreachable

**Error:**
```
ERROR: Network unreachable: 239.1.2.3:12000
```

**Causes:**
- Wrong network interface
- Multicast routing not configured
- Network disconnected

**Solutions:**

1. **Check network interface:**
   ```bash
   ip addr show
   ifconfig
   ```

2. **Configure multicast routing (Linux):**
   ```bash
   # Add route for multicast
   sudo route add -net 224.0.0.0 netmask 240.0.0.0 dev eth0

   # Or use ip command
   sudo ip route add 224.0.0.0/4 dev eth0
   ```

3. **Test connectivity:**
   ```bash
   # Ping multicast address (may not work for all multicast addresses)
   ping 239.1.2.3

   # Use netcat to test UDP
   nc -u 239.1.2.3 12000
   ```

---

### 18. PFT Requires --pft Flag

**Error:**
```
ERROR: --pft-fec requires --pft to be enabled
```

**Cause:** Trying to use PFT options without enabling PFT.

**Wrong:**
```bash
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft-fec
```

**Correct:**
```bash
dabmux -c config.yaml --edi udp://239.1.2.3:12000 --pft --pft-fec
```

---

## Runtime Errors

### 19. Interrupted by User

**Message:**
```
INFO: Received interrupt signal, shutting down...
```

**Cause:** User pressed Ctrl+C (this is normal, not an error).

**Graceful shutdown:** python-dabmux closes files and network connections cleanly.

**To stop:**
- Press `Ctrl+C` once
- Wait for shutdown message
- Don't press Ctrl+C multiple times

---

### 20. Out of Memory

**Error:**
```
ERROR: MemoryError: Unable to allocate array
```

**Causes:**
- Generating too many frames at once
- Memory leak (rare)
- Insufficient system memory

**Solutions:**

1. **Generate frames in batches:**
   ```bash
   # Instead of generating millions of frames at once
   dabmux -c config.yaml -o output.eti -n 10000  # Smaller batch
   ```

2. **Use continuous mode with file output:**
   ```bash
   # Continuously append to file (uses constant memory)
   dabmux -c config.yaml -o output.eti --continuous
   ```

3. **Check system memory:**
   ```bash
   free -h        # Linux
   vm_stat        # macOS
   ```

---

### 21. Python Version Too Old

**Error:**
```
ERROR: Python 3.11 or later is required
```

**Cause:** python-dabmux requires Python 3.11+.

**Solutions:**

1. **Check Python version:**
   ```bash
   python --version
   python3 --version
   ```

2. **Install Python 3.11+:**
   ```bash
   # Ubuntu/Debian
   sudo apt install python3.11

   # macOS (Homebrew)
   brew install python@3.11

   # Or download from python.org
   ```

3. **Use specific Python version:**
   ```bash
   python3.11 -m dabmux.cli -c config.yaml -o output.eti
   ```

---

### 22. Module Not Found

**Error:**
```
ERROR: ModuleNotFoundError: No module named 'dabmux'
```

**Cause:** python-dabmux not installed or virtual environment not activated.

**Solutions:**

1. **Check installation:**
   ```bash
   pip list | grep dabmux
   ```

2. **Install python-dabmux:**
   ```bash
   pip install python-dabmux
   # Or for development:
   pip install -e .
   ```

3. **Activate virtual environment:**
   ```bash
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

---

### 23. Label Too Long

**Error:**
```
ERROR: Label text exceeds 16 characters: "This is a very long label"
```

**Cause:** DAB labels limited to 16 characters, short labels to 8.

**Wrong:**
```yaml
label:
  text: 'This is a very long label'  # 25 characters!
  short: 'Long Label'                # 10 characters!
```

**Correct:**
```yaml
label:
  text: 'Long Label'       # 10 characters (max 16)
  short: 'LongLbl'         # 7 characters (max 8)
```

---

### 24. Capacity Exceeded

**Error:**
```
ERROR: Total subchannel capacity exceeds available CUs for Mode I
```

**Cause:** Sum of all subchannel bitrates (with protection) exceeds available bandwidth.

**Mode I capacity:** 864 Capacity Units (CU)

**Solutions:**

1. **Reduce bitrates:**
   ```yaml
   subchannels:
     - bitrate: 128  # Reduce from 192
   ```

2. **Lower protection levels:**
   ```yaml
   protection:
     level: 2       # Reduce from 3 (uses fewer CUs)
   ```

3. **Remove services:**
   - Fewer services = more bandwidth per service

4. **Use DAB+ instead of DAB:**
   - DAB+: 48-96 kbps (good quality)
   - DAB: 128-192 kbps (similar quality)

---

### 25. Duplicate IDs

**Error:**
```
ERROR: Duplicate service ID: 0x5001
```

**Cause:** Multiple services or subchannels with same ID.

**Wrong:**
```yaml
services:
  - id: '0x5001'
    label:
      text: 'Service 1'
  - id: '0x5001'     # Duplicate!
    label:
      text: 'Service 2'
```

**Correct:**
```yaml
services:
  - id: '0x5001'
    label:
      text: 'Service 1'
  - id: '0x5002'     # Unique ID
    label:
      text: 'Service 2'
```

---

### 26. MPEG CRC Warnings in Players (Cosmetic)

**Warning:**
```
(CRC) (CRC) (CRC) (CRC) ...
```

**Cause:** Input MPEG Layer II files don't have CRC protection enabled. DAB standard requires CRC, but audio plays correctly despite warnings.

**Is This a Problem?**
- ✅ Audio plays normally
- ✅ ETI frames are valid
- ⚠️ Cosmetic warnings only
- ⚠️ Non-compliant for broadcast (fine for testing)

**Why It Happens:**
The DAB standard (ETSI EN 300 401) requires MPEG frames to include CRC-16 protection. Most encoders (including ffmpeg) generate MP2 files without CRC by default.

**Solutions:**

**Option 1: Accept the warnings (Recommended for testing)**
- Audio works perfectly
- No action needed
- Suitable for development and testing

**Option 2: Re-encode with CRC protection**

Using toolame:
```bash
# Install toolame
brew install toolame  # macOS
apt-get install toolame  # Linux

# Encode with CRC enabled
toolame -e -b 96 -s 48 input.wav output.mp2
```

Using ODR-AudioEnc:
```bash
odr-audioenc -i input.wav -b 96 -c 2 -r 48000 \
  -o output.mp2 -f mp2 --mpeg-crc
```

**Option 3: Use DAB+ instead**
```yaml
services:
  - sid: '0x5001'
    label:
      text: 'My Station'
    components:
      - type: 'dabplus'  # DAB+ has built-in error protection
        bitrate: 48
```

**Technical Details:**
- MPEG CRC protects bit allocation and scale factor metadata
- Required for RF broadcast error detection
- Cannot be added to existing non-CRC files without re-encoding
- See [MPEG_CRC_LIMITATION.md](../../MPEG_CRC_LIMITATION.md) for full explanation

**When to Fix:**
- ✅ Production/broadcast systems: Re-encode with CRC
- ✅ Critical applications: Use DAB+ instead
- ⚠️ Testing/development: Warnings can be ignored

---

## Getting More Help

If your error isn't listed here:

1. **Check specific troubleshooting guides:**
   - [Input Issues](input-issues.md)
   - [Output Issues](output-issues.md)
   - [Network Issues](network-issues.md)

2. **Enable debug logging:**
   ```bash
   dabmux -c config.yaml -o output.eti -vvv
   ```

3. **Check the FAQ:**
   - [FAQ](../faq.md)

4. **Search GitHub Issues:**
   - [github.com/python-dabmux/python-dabmux/issues](https://github.com/python-dabmux/python-dabmux/issues)

5. **Report a bug:**
   - Include your configuration file
   - Include the complete error message
   - Include debug output (`-vvv`)
   - Include your Python version and OS

## See Also

- [Debugging Guide](debugging.md): Advanced debugging techniques
- [Configuration Reference](../user-guide/configuration/index.md): Valid configuration options
- [CLI Reference](../user-guide/cli-reference.md): Command-line options
