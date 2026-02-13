# Troubleshooting

Having problems with python-dabmux? This section will help you diagnose and fix common issues.

## Quick Troubleshooting

### Check These First

1. **Python version:** Requires Python 3.11+
   ```bash
   python --version
   ```

2. **Installation:** Verify python-dabmux is installed
   ```bash
   python -m dabmux.cli --help
   ```

3. **Configuration:** Validate your YAML file
   ```bash
   # Try with verbose logging
   dabmux -c config.yaml -o test.eti -n 1 -vvv
   ```

4. **Input files:** Check files exist and are correct format
   ```bash
   ls -l audio.mp2
   file audio.mp2
   ```

## Troubleshooting Guides

### [Common Errors](common-errors.md)

25+ most common errors with solutions:

- Configuration file errors (missing sections, invalid YAML, hex values)
- Input errors (file not found, invalid format, network issues)
- Output errors (permissions, network unreachable, EDI problems)
- Runtime errors (memory, interrupts, capacity exceeded)

[Read Common Errors →](common-errors.md)

### [Input Issues](input-issues.md)

Problems with audio inputs:

- File input errors (formats, paths, permissions)
- Network input issues (UDP/TCP, multicast, buffering)
- Audio format problems (MPEG vs AAC, bitrates, sample rates)

[Read Input Issues →](input-issues.md)

### [Output Issues](output-issues.md)

Problems with ETI/EDI output:

- File output errors (permissions, disk space, formats)
- EDI network issues (connectivity, protocols, addressing)
- PFT problems (fragmentation, FEC, MTU)

[Read Output Issues →](output-issues.md)

### [Network Issues](network-issues.md)

Network-specific problems:

- Multicast configuration
- Firewall and routing
- UDP vs TCP considerations
- Performance tuning

[Read Network Issues →](network-issues.md)

### [Debugging](debugging.md)

Advanced debugging techniques:

- Enabling debug logging
- Analyzing ETI frames
- Using network monitoring tools
- Profiling performance

[Read Debugging Guide →](debugging.md)

## Common Problem Categories

### Configuration Problems

**Symptoms:**
- Error on startup
- "Invalid configuration" messages
- YAML parse errors

**First steps:**
1. Check YAML syntax (indentation, colons, quotes)
2. Verify all IDs are quoted (`'0xCE15'`)
3. Ensure service_id and subchannel_id match

**See:** [Common Errors - Configuration](common-errors.md#configuration-errors)

### Input Problems

**Symptoms:**
- "File not found" errors
- "Invalid frame header" messages
- Buffer underruns

**First steps:**
1. Verify file paths (use `file://` prefix)
2. Check audio format (MPEG Layer II for DAB)
3. Test with a known-good audio file

**See:** [Input Issues](input-issues.md)

### Output Problems

**Symptoms:**
- Can't write output file
- Network unreachable
- Missing or corrupted frames

**First steps:**
1. Check file permissions
2. Verify network connectivity
3. Test with file output first, then network

**See:** [Output Issues](output-issues.md)

### Network Problems

**Symptoms:**
- "Connection refused"
- Multicast not working
- Packet loss

**First steps:**
1. Check firewall settings
2. Verify multicast routing
3. Test with unicast first

**See:** [Network Issues](network-issues.md)

## Debug Workflow

Follow this workflow to diagnose problems:

### 1. Start Simple

Test with minimal configuration:

```bash
# Single service, file input, file output
dabmux -c basic_config.yaml -o test.eti -n 10
```

### 2. Enable Verbose Logging

Get detailed information:

```bash
# Maximum verbosity
dabmux -c config.yaml -o output.eti -n 10 -vvv
```

### 3. Verify Configuration

Check that configuration is valid:

```bash
# Test with 1 frame
dabmux -c config.yaml -o test.eti -n 1 -vvv
```

### 4. Test Components Individually

- Test each input file separately
- Test file output before network output
- Test UDP before adding PFT

### 5. Check External Tools

Use system tools to verify:

```bash
# Check files
file audio.mp2
ffprobe audio.mp2

# Check network
netstat -rn | grep 239  # Multicast routes
tcpdump -i eth0 udp port 12000  # Network traffic

# Check ETI output
hexdump -C output.eti | head
```

## Getting Help

### Self-Help Resources

1. **[FAQ](../faq.md)**: Frequently asked questions
2. **[Configuration Reference](../user-guide/configuration/index.md)**: Valid options
3. **[Examples](../user-guide/configuration/examples.md)**: Working configurations

### Community Help

1. **GitHub Issues**: [Report bugs](https://github.com/python-dabmux/python-dabmux/issues)
2. **Discussions**: Ask questions
3. **Documentation**: You're reading it!

### Reporting Bugs

When reporting bugs, include:

1. **Python version**: `python --version`
2. **python-dabmux version**: `dabmux --version`
3. **Operating system**: Linux, macOS, Windows + version
4. **Configuration file** (remove sensitive data)
5. **Complete error message**
6. **Debug output**: Run with `-vvv` and include output
7. **Steps to reproduce**

**Example bug report:**

```
## Environment
- Python 3.11.5
- python-dabmux 0.6.0
- Ubuntu 22.04 LTS

## Problem
Getting "Invalid MPEG frame header" when using UDP input

## Configuration
[paste relevant config sections]

## Steps to Reproduce
1. Start UDP streaming with: nc -u 239.1.2.3 5001 < audio.mp2
2. Run: dabmux -c config.yaml -o output.eti -vvv
3. Error occurs immediately

## Debug Output
[paste output with -vvv]

## Expected Behavior
Should multiplex UDP input without errors

## Actual Behavior
Crashes with "Invalid MPEG frame header"
```

## Quick Reference

### Error Message Keywords

| Keyword | Section |
|---------|---------|
| "Configuration" | [Common Errors](common-errors.md#configuration-errors) |
| "File not found" | [Input Issues](input-issues.md) |
| "Invalid frame" | [Input Issues](input-issues.md) |
| "Permission denied" | [Output Issues](output-issues.md) |
| "Network unreachable" | [Network Issues](network-issues.md) |
| "Connection refused" | [Network Issues](network-issues.md) |

### Common Solutions

| Problem | Quick Fix |
|---------|-----------|
| Config not found | Use absolute path: `-c /full/path/config.yaml` |
| Input not found | Check `file://` prefix and path |
| Invalid hex value | Add quotes and `0x`: `id: '0xCE15'` |
| YAML error | Check indentation (spaces, not tabs) |
| Network error | Test with file output first |
| Permission error | Check file/directory permissions |

## See Also

- [User Guide](../user-guide/index.md): Complete usage documentation
- [CLI Reference](../user-guide/cli-reference.md): Command-line options
- [Architecture](../architecture/index.md): How python-dabmux works
- [FAQ](../faq.md): Frequently asked questions
