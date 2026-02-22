# Remote Control Guide

Complete guide to controlling your DAB multiplexer at runtime using ZeroMQ and Telnet interfaces.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [ZeroMQ Interface](#zeromq-interface)
4. [Telnet Interface](#telnet-interface)
5. [Commands Reference](#commands-reference)
6. [Authentication](#authentication)
7. [Common Use Cases](#common-use-cases)
8. [Security](#security)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The remote control system provides two interfaces for runtime control:

### ZeroMQ Interface
- **Protocol:** JSON over ZeroMQ REQ/REP sockets
- **Use Case:** Automation, scripting, integration with other systems
- **Format:** Machine-readable JSON messages
- **Port:** Default 9000 (configurable)

### Telnet Interface
- **Protocol:** Interactive text-based commands
- **Use Case:** Manual control, debugging, monitoring
- **Format:** Human-readable text commands
- **Port:** Default 9001 (configurable)

### When to Use Which

**Use ZeroMQ when:**
- Automating label updates based on metadata
- Integrating with broadcast automation systems
- Triggering announcements from alert systems
- Monitoring multiplexer health programmatically

**Use Telnet when:**
- Manually testing or debugging
- Quick status checks
- Learning the command set
- Interactive administration

---

## Quick Start

### Enable Remote Control

Add to your configuration file:

```yaml
ensemble:
  # ... existing configuration ...

  remote_control:
    # ZeroMQ JSON API
    zmq_enabled: true
    zmq_bind: 'tcp://*:9000'  # Listen on all interfaces, port 9000

    # Telnet interface
    telnet_enabled: true
    telnet_port: 9001

    # Authentication (optional but recommended)
    auth_enabled: true
    auth_password: 'your_secure_password_here'

    # Audit logging (optional)
    audit_log: '/var/log/dabmux/audit.log'
```

### Start the Multiplexer

```bash
python -m dabmux.cli -c config.yaml -o output.eti
```

You should see:
```
INFO: ZeroMQ remote control enabled on tcp://*:9000
INFO: Telnet remote control enabled on port 9001
```

### Connect via Telnet

```bash
telnet localhost 9001
```

```
Connected to localhost.
Escape character is '^]'.
DAB Multiplexer Remote Control
Enter password: your_secure_password_here
OK Authenticated

> help
Available commands: get_statistics, set_label, ...
```

### Connect via ZeroMQ (Python)

```python
import zmq
import json

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:9000")

request = {
    "command": "get_statistics",
    "args": {},
    "auth": "your_secure_password_here"
}

socket.send_json(request)
response = socket.recv_json()
print(response)
```

---

## ZeroMQ Interface

### Message Format

**Request:**
```json
{
  "command": "command_name",
  "args": {
    "param1": "value1",
    "param2": "value2"
  },
  "auth": "password"
}
```

**Response (Success):**
```json
{
  "status": "ok",
  "data": {
    "result": "value"
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Error description"
}
```

### Python Client Example

```python
import zmq
import json

class DABMuxClient:
    def __init__(self, host='localhost', port=9000, password=None):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{host}:{port}")
        self.password = password

    def send_command(self, command, **args):
        request = {
            "command": command,
            "args": args
        }
        if self.password:
            request["auth"] = self.password

        self.socket.send_json(request)
        response = self.socket.recv_json()

        if response.get("status") == "error":
            raise Exception(response.get("message", "Unknown error"))

        return response.get("data", {})

    def get_statistics(self):
        return self.send_command("get_statistics")

    def set_label(self, uid, text):
        return self.send_command("set_label", uid=uid, text=text)

    def trigger_announcement(self, service_uid, ann_type, subchannel_uid=None):
        return self.send_command("trigger_announcement",
                                service_uid=service_uid,
                                announcement_type=ann_type,
                                subchannel_uid=subchannel_uid)

# Usage
client = DABMuxClient(password='your_password')
stats = client.get_statistics()
print(f"Frames generated: {stats['frames_generated']}")

client.set_label('my_component', 'Now Playing: Artist - Song')
```

### curl Example (Quick Testing)

While ZeroMQ isn't HTTP, you can use a simple Python wrapper for testing:

```bash
# Using Python one-liner
python3 -c "
import zmq, json, sys
ctx = zmq.Context()
sock = ctx.socket(zmq.REQ)
sock.connect('tcp://localhost:9000')
sock.send_json({'command': 'get_statistics', 'args': {}, 'auth': 'password'})
print(sock.recv_json())
"
```

---

## Telnet Interface

### Connecting

```bash
telnet localhost 9001
```

### Command Format

Commands are simple text strings:
```
command_name [arg1] [arg2] ...
```

**Example:**
```
> get_statistics
OK frames_generated=1234 inputs=2 services=3

> set_label my_component "Now Playing: New Song"
OK

> help
Available commands:
  get_statistics - Get runtime statistics
  set_label <uid> <text> - Set component dynamic label
  ...
```

### Interactive Session Example

```
$ telnet localhost 9001
Connected to localhost.
DAB Multiplexer Remote Control
Enter password: ********
OK Authenticated

> get_statistics
OK frames_generated=5432 inputs=3 services=2 fic_fill_rate=75

> list_services
OK service[0]=0x5001:My Radio service[1]=0x5002:News Channel

> set_label audio_component "Now Playing: Artist - Song Title"
OK

> get_input_status audio_main
OK state=active bytes_read=1234567 frames_read=4321

> trigger_announcement radio_service alarm
OK announcement_triggered=true

> quit
Goodbye
Connection closed by foreign host.
```

---

## Commands Reference

### 1. get_statistics

Get runtime statistics about the multiplexer.

**ZeroMQ:**
```json
{
  "command": "get_statistics",
  "args": {}
}
```

**Telnet:**
```
> get_statistics
```

**Response:**
```json
{
  "frames_generated": 12345,
  "inputs": 3,
  "services": 2,
  "subchannels": 4,
  "fic_fill_rate": 75,
  "uptime_seconds": 3600
}
```

### 2. set_label

Update a dynamic label (FIG 2/1) for a component.

**ZeroMQ:**
```json
{
  "command": "set_label",
  "args": {
    "uid": "audio_component",
    "text": "Now Playing: Artist - Song"
  }
}
```

**Telnet:**
```
> set_label audio_component "Now Playing: Artist - Song"
```

**Notes:**
- Component must have `dynamic_label` configured
- Text limit: 128 characters (UTF-8)
- Updates transmitted within 1-2 seconds

### 3. trigger_announcement

Trigger an emergency announcement (FIG 0/19).

**ZeroMQ:**
```json
{
  "command": "trigger_announcement",
  "args": {
    "service_uid": "radio_service",
    "announcement_type": "alarm",
    "subchannel_uid": "emergency_audio"
  }
}
```

**Telnet:**
```
> trigger_announcement radio_service alarm emergency_audio
```

**Announcement Types:**
- `alarm` - Emergency alarm
- `road_traffic` - Traffic flash
- `transport_flash` - Public transport
- `warning_service` - Warning message
- `news_flash` - News flash
- `area_weather` - Weather alert
- `event_announcement` - Special event
- `sport_report` - Sport flash
- `financial_report` - Financial news

### 4. stop_announcement

Stop an active announcement.

**ZeroMQ:**
```json
{
  "command": "stop_announcement",
  "args": {
    "service_uid": "radio_service"
  }
}
```

**Telnet:**
```
> stop_announcement radio_service
```

### 5. list_services

List all services in the ensemble.

**ZeroMQ:**
```json
{
  "command": "list_services",
  "args": {}
}
```

**Response:**
```json
{
  "services": [
    {"uid": "service1", "id": "0x5001", "label": "My Radio"},
    {"uid": "service2", "id": "0x5002", "label": "News"}
  ]
}
```

### 6. list_components

List all service components.

**ZeroMQ:**
```json
{
  "command": "list_components",
  "args": {}
}
```

**Response:**
```json
{
  "components": [
    {"uid": "audio_comp", "service_id": "0x5001", "subchannel_id": 0},
    {"uid": "data_comp", "service_id": "0x5001", "subchannel_id": 1}
  ]
}
```

### 7. get_input_status

Get status of an input source.

**ZeroMQ:**
```json
{
  "command": "get_input_status",
  "args": {
    "uid": "audio_main"
  }
}
```

**Response:**
```json
{
  "state": "active",
  "bytes_read": 1234567,
  "frames_read": 4321,
  "errors": 0
}
```

### 8. set_logging_level

Change logging verbosity at runtime.

**ZeroMQ:**
```json
{
  "command": "set_logging_level",
  "args": {
    "level": "debug"
  }
}
```

**Telnet:**
```
> set_logging_level debug
```

**Levels:** `debug`, `info`, `warning`, `error`

### 9-20. Additional Commands

See full command list:
```
> help
```

Or check source: `src/dabmux/remote/zmq_server.py`

---

## Authentication

### Password Setup

**Configuration:**
```yaml
ensemble:
  remote_control:
    auth_enabled: true
    auth_password: 'strong_password_here'
```

**Security Recommendations:**
- Use strong passwords (16+ characters)
- Change default passwords
- Use different passwords per deployment
- Store passwords in environment variables, not config files

**Environment Variable:**
```yaml
ensemble:
  remote_control:
    auth_password: '${DABMUX_RC_PASSWORD}'
```

```bash
export DABMUX_RC_PASSWORD='strong_password'
python -m dabmux.cli -c config.yaml -o output.eti
```

### ZeroMQ Authentication

Include `auth` field in every request:
```json
{
  "command": "get_statistics",
  "args": {},
  "auth": "your_password"
}
```

### Telnet Authentication

Enter password when prompted:
```
Enter password: ********
OK Authenticated
```

### Failed Authentication

**ZeroMQ Response:**
```json
{
  "status": "error",
  "message": "Authentication required"
}
```

**Telnet Response:**
```
ERROR Authentication failed
Connection closed.
```

### Audit Logging

Track all remote control access:
```yaml
ensemble:
  remote_control:
    audit_log: '/var/log/dabmux/audit.log'
```

**Log Format:**
```
2026-02-22 10:30:45 [ZMQ] AUTHENTICATED user@192.168.1.100
2026-02-22 10:30:46 [ZMQ] COMMAND get_statistics user@192.168.1.100
2026-02-22 10:30:50 [ZMQ] COMMAND set_label uid=audio_comp user@192.168.1.100
2026-02-22 10:31:00 [TELNET] AUTHENTICATED user@192.168.1.50
2026-02-22 10:31:05 [TELNET] COMMAND trigger_announcement user@192.168.1.50
```

---

## Common Use Cases

### Automated "Now Playing" Updates

```python
#!/usr/bin/env python3
"""Update DAB+ dynamic label from metadata."""
import zmq
import json
import time

client = DABMuxClient(password='password')

while True:
    # Get current track from your automation system
    track = get_current_track()  # Your function

    # Update label
    label_text = f"Now Playing: {track['artist']} - {track['title']}"
    client.set_label('audio_component', label_text)

    # Update every 5 seconds
    time.sleep(5)
```

### Emergency Alert Automation

```python
#!/usr/bin/env python3
"""Trigger DAB announcement from CAP alert."""
import zmq
import json
import requests

client = DABMuxClient(password='password')

# Monitor CAP (Common Alerting Protocol) feed
cap_url = 'https://alerts.example.com/cap/feed.xml'

while True:
    alerts = check_cap_feed(cap_url)  # Your parser

    for alert in alerts:
        if alert['severity'] == 'Extreme':
            # Trigger emergency announcement
            client.trigger_announcement(
                service_uid='radio_service',
                ann_type='alarm',
                subchannel_uid='emergency_audio'
            )

            # Update DLS with alert text
            client.set_label('audio_component', alert['description'])

    time.sleep(60)
```

### Health Monitoring

```python
#!/usr/bin/env python3
"""Monitor multiplexer health."""
import zmq
import json
import time

client = DABMuxClient(password='password')

while True:
    stats = client.get_statistics()

    # Check FIC fill rate
    if stats['fic_fill_rate'] > 90:
        print("WARNING: FIC nearly full!")

    # Check input status
    for input_uid in ['audio1', 'audio2']:
        status = client.send_command('get_input_status', uid=input_uid)
        if status['state'] != 'active':
            print(f"ERROR: Input {input_uid} not active!")

    time.sleep(10)
```

---

## Security

### Network Security

**Bind to Localhost Only:**
```yaml
ensemble:
  remote_control:
    zmq_bind: 'tcp://127.0.0.1:9000'  # Localhost only
    telnet_port: 9001
    telnet_bind: '127.0.0.1'          # Localhost only
```

**Use SSH Tunnel for Remote Access:**
```bash
# On remote machine, create SSH tunnel
ssh -L 9000:localhost:9000 -L 9001:localhost:9001 user@multiplexer-host

# Connect to localhost (tunneled)
telnet localhost 9001
```

### Firewall Configuration

**Allow only specific IPs:**
```bash
# iptables example
iptables -A INPUT -p tcp --dport 9000 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 9000 -j DROP
iptables -A INPUT -p tcp --dport 9001 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 9001 -j DROP
```

### Best Practices

1. **Enable Authentication** - Always use passwords
2. **Bind to Localhost** - Use SSH tunnels for remote access
3. **Enable Audit Logging** - Track all access
4. **Strong Passwords** - 16+ characters, random
5. **Regular Password Rotation** - Change every 90 days
6. **Monitor Logs** - Check for unauthorized access
7. **Limit Commands** - Implement command ACLs if needed

---

## Troubleshooting

### Connection Refused

**Problem:** `telnet: Unable to connect to remote host: Connection refused`

**Solutions:**
1. Check multiplexer is running
2. Verify telnet enabled in config
3. Check port number (default 9001)
4. Check firewall rules

```bash
# Check if port is listening
netstat -tuln | grep 9001
```

### Authentication Failed

**Problem:** `ERROR Authentication failed`

**Solutions:**
1. Check password in config matches
2. Verify auth_enabled is true
3. Check for typos or extra spaces
4. Try without auth first (disable auth_enabled)

### ZMQ Timeout

**Problem:** `zmq.error.Again: Resource temporarily unavailable`

**Solutions:**
1. Set socket timeout:
   ```python
   socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
   ```
2. Check multiplexer is running
3. Verify ZMQ port (default 9000)
4. Check network connectivity

### Command Not Found

**Problem:** `ERROR Unknown command: xyz`

**Solutions:**
1. Check spelling
2. Use `help` to list available commands
3. Check command syntax

### Label Not Updating

**Problem:** Dynamic label doesn't change on receiver

**Solutions:**
1. Verify component has `dynamic_label` configured
2. Check label text length (< 128 chars)
3. Wait 1-2 seconds for transmission
4. Check receiver supports FIG 2/1
5. Verify signal quality

### Permission Denied

**Problem:** `ERROR Permission denied`

**Solutions:**
1. Check user has permission to run command
2. Verify authentication successful
3. Check audit log for details

---

## Resources

**Standards:**
- ETSI EN 300 401 - DAB System

**Source Code:**
- `src/dabmux/remote/zmq_server.py` - ZMQ implementation
- `src/dabmux/remote/telnet_server.py` - Telnet implementation

**Examples:**
- `examples/zmq_client.py` - Python ZMQ client
- `examples/remote_control.yaml` - Configuration example

**Tools:**
- `telnet` - Interactive client
- `zmq` Python library - Automation

---

**Last Updated:** 2026-02-22

**Status:** Production Ready

For additional help, see [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) or [Quick Start Guide](QUICK_START.md).
