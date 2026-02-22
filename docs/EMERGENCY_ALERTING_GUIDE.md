# Emergency Alerting System Guide

Complete guide to implementing emergency alerts and announcements in DAB using FIG 0/18 and FIG 0/19.

---

## Table of Contents

1. [Overview](#overview)
2. [How DAB Alerts Work](#how-dab-alerts-work)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Announcement Types](#announcement-types)
6. [Triggering Alerts](#triggering-alerts)
7. [Receiver Behavior](#receiver-behavior)
8. [Best Practices](#best-practices)
9. [Integration](#integration)
10. [Testing](#testing)

---

## Overview

### What is DAB Emergency Alerting?

DAB supports automatic emergency announcements that cause receivers to:
- **Auto-switch** to emergency broadcast
- **Increase volume** to alert users
- **Display warning** on screen
- **Return to normal** when alert ends

### Standards

- **FIG 0/18** - Announcement Support (declares which announcements are available)
- **FIG 0/19** - Announcement Switching (triggers active announcements)
- **ETSI EN 300 401 Section 8.1.6.2 and 8.1.6.3**

### Use Cases

**Public Safety:**
- Natural disasters (earthquakes, floods, tornadoes)
- Severe weather warnings
- Emergency evacuations
- Civil defense alerts

**Traffic & Transport:**
- Major traffic incidents
- Road closures
- Public transport disruptions

**Broadcasting:**
- News flashes
- Sport results
- Special announcements

---

## How DAB Alerts Work

### FIG 0/18: Announcement Support

**Purpose:** Declares which announcement types a service supports

**Example:**
```
Service "My Radio" supports:
  - Alarm (emergency)
  - Road traffic flash
  - Weather warning
  - News flash
```

Receivers know which services can provide which alerts.

### FIG 0/19: Announcement Switching

**Purpose:** Signals active announcements in progress

**Example:**
```
ALARM ANNOUNCEMENT ACTIVE
  Service: Emergency Broadcast
  Subchannel: Emergency Audio
```

Receivers automatically switch to the announcement source.

### Receiver Auto-Switching

**When announcement triggered:**

1. **Detection:** Receiver sees FIG 0/19
2. **Decision:** Check if user wants this announcement type
3. **Switch:** Tune to announcement subchannel
4. **Alert:** Increase volume, show warning
5. **Monitor:** Wait for announcement to end
6. **Return:** Resume normal playback

**User Control:**
- Users can enable/disable announcement types
- Can choose to ignore certain alerts
- Volume boost level configurable

---

## Quick Start

### 1. Configure Announcement Support

```yaml
ensemble:
  # ... existing configuration ...

services:
  - uid: 'my_radio'
    id: 0x5001
    label:
      text: 'My Radio'

    # Declare announcement support
    announcements:
      enabled: true
      cluster_id: 0  # Announcement cluster
      types:
        - 'alarm'           # Emergency alarm
        - 'road_traffic'    # Traffic flash
        - 'warning_service' # Warning messages
        - 'news_flash'      # News flash

    # Optional: Dedicated emergency audio subchannel
    announcement_subchannels:
      - type: 'alarm'
        subchannel_uid: 'emergency_audio'
```

### 2. Create Emergency Audio Source (Optional)

```yaml
subchannels:
  # Normal programming
  - uid: 'normal_audio'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file://audio/normal.dabp'

  # Emergency audio (separate subchannel)
  - uid: 'emergency_audio'
    id: 1
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file://audio/emergency.dabp'
```

### 3. Start Multiplexer

```bash
python -m dabmux.cli -c config.yaml -o output.eti
```

### 4. Trigger Alert

**Via Remote Control:**
```bash
telnet localhost 9001
> trigger_announcement my_radio alarm emergency_audio
OK announcement_triggered=true
```

**Via Python:**
```python
from dabmux_client import DABMuxClient

client = DABMuxClient(password='password')
client.trigger_announcement(
    service_uid='my_radio',
    announcement_type='alarm',
    subchannel_uid='emergency_audio'  # Optional
)
```

---

## Configuration

### Service-Level Announcement Declaration

```yaml
services:
  - uid: 'my_service'
    id: 0x5001
    label:
      text: 'My Radio'

    # Enable announcements
    announcements:
      enabled: true
      cluster_id: 0  # Announcement cluster (0-7)

      # Supported announcement types
      types:
        - 'alarm'              # Emergency alarm
        - 'road_traffic'       # Traffic flash
        - 'transport_flash'    # Public transport
        - 'warning_service'    # Warning message
        - 'news_flash'         # News flash
        - 'area_weather'       # Area weather
        - 'event_announcement' # Event
        - 'sport_report'       # Sport flash
        - 'financial_report'   # Financial news

      # Optional: Map announcement types to specific subchannels
      announcement_subchannels:
        - type: 'alarm'
          subchannel_uid: 'emergency_audio'
        - type: 'road_traffic'
          subchannel_uid: 'traffic_audio'
        - type: 'news_flash'
          subchannel_uid: 'news_audio'

      # Flags (optional, advanced)
      announcement_flags:
        alarm: 0x01  # High priority
```

### Ensemble-Level Configuration (Optional)

```yaml
ensemble:
  # Default announcement cluster
  default_announcement_cluster: 0

  # Announcement monitoring (optional)
  announcement_log: '/var/log/dabmux/announcements.log'
```

### Minimal Configuration

**Simple alarm support:**
```yaml
services:
  - uid: 'my_radio'
    id: 0x5001
    announcements:
      enabled: true
      types:
        - 'alarm'
```

---

## Announcement Types

### Standard Announcement Types

**ETSI EN 300 401 defines 11 announcement types:**

| Type | Value | Description | Priority | Use Case |
|------|-------|-------------|----------|----------|
| **alarm** | 0 | Emergency alarm | HIGHEST | Natural disasters, civil defense |
| **road_traffic** | 1 | Road traffic flash | HIGH | Major incidents, closures |
| **transport_flash** | 2 | Public transport | HIGH | Service disruptions |
| **warning_service** | 3 | Warning/service message | HIGH | Weather warnings |
| **news_flash** | 4 | News flash | MEDIUM | Breaking news |
| **area_weather** | 5 | Area weather flash | MEDIUM | Weather alerts |
| **event_announcement** | 6 | Event announcement | LOW | Special events |
| **special_event** | 7 | Special event | LOW | Rare events |
| **programme_info** | 8 | Programme information | LOW | Schedule changes |
| **sport_report** | 9 | Sport report | LOW | Sport results |
| **financial_report** | 10 | Financial report | LOW | Stock updates |

### Priority Levels

**Receiver behavior by priority:**

**HIGHEST (alarm):**
- Always auto-switch
- Maximum volume boost
- Prominent display
- Cannot be disabled

**HIGH (traffic, transport, warning):**
- Auto-switch if enabled
- Moderate volume boost
- Clear indication
- Can be disabled

**MEDIUM (news, weather):**
- Auto-switch if enabled
- Small volume boost
- Notification
- Can be disabled

**LOW (events, info, sport, financial):**
- Notification only
- No auto-switch
- User can manually switch
- Can be disabled

### Choosing Announcement Types

**Emergency Broadcasting:**
```yaml
types:
  - 'alarm'           # Critical emergencies
  - 'warning_service' # Weather warnings
  - 'area_weather'    # Weather alerts
```

**Traffic Service:**
```yaml
types:
  - 'road_traffic'    # Traffic incidents
  - 'transport_flash' # Public transport
```

**News Station:**
```yaml
types:
  - 'news_flash'      # Breaking news
  - 'sport_report'    # Sport updates
  - 'financial_report'# Financial news
```

---

## Triggering Alerts

### Via Remote Control (Telnet)

```bash
telnet localhost 9001
> trigger_announcement <service_uid> <announcement_type> [subchannel_uid]
```

**Examples:**
```
> trigger_announcement my_radio alarm
OK announcement_triggered=true

> trigger_announcement my_radio alarm emergency_audio
OK announcement_triggered=true announcement_subchannel=emergency_audio

> trigger_announcement traffic_service road_traffic traffic_subchannel
OK announcement_triggered=true
```

### Via Remote Control (ZeroMQ/Python)

```python
import zmq
import json

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:9000")

request = {
    "command": "trigger_announcement",
    "args": {
        "service_uid": "my_radio",
        "announcement_type": "alarm",
        "subchannel_uid": "emergency_audio"  # Optional
    },
    "auth": "password"
}

socket.send_json(request)
response = socket.recv_json()
print(response)
```

### Stopping Announcements

**Via Telnet:**
```
> stop_announcement my_radio
OK announcement_stopped=true
```

**Via Python:**
```python
request = {
    "command": "stop_announcement",
    "args": {
        "service_uid": "my_radio"
    },
    "auth": "password"
}
```

### Announcement Duration

**Automatic timeout:**
- Default: 60 seconds
- Configurable per announcement type
- Can be stopped manually before timeout

**Configuration:**
```yaml
services:
  - uid: 'my_radio'
    announcements:
      enabled: true
      types:
        - 'alarm'
      timeout_seconds: 120  # 2 minutes max
```

---

## Receiver Behavior

### Auto-Switching Logic

**When receiver sees FIG 0/19:**

1. **Check announcement type:** Is it enabled by user?
2. **Check priority:** High priority = immediate switch
3. **Check current state:** Already in announcement?
4. **Switch:** Tune to announcement subchannel
5. **Alert:** Volume boost, display warning
6. **Monitor:** Wait for FIG 0/19 to stop
7. **Return:** Resume previous service

### Volume Boost

**Typical behavior:**
- Alarm: +12 dB boost
- Traffic/Warning: +6 dB boost
- News/Weather: +3 dB boost
- Info/Sport: +0 dB (notification only)

### User Settings

**Receivers typically allow:**
- Enable/disable each announcement type
- Adjust volume boost level
- Choose between auto-switch or notification
- Blacklist certain services

### Display

**On receiver screen:**
```
⚠️ EMERGENCY ALERT ⚠️
Severe Weather Warning
Tune to local emergency broadcast
```

---

## Best Practices

### Testing Procedures

**Before going live:**
1. Configure announcement support
2. Test trigger mechanism (remote control)
3. Verify FIG 0/18 transmitted (etisnoop)
4. Verify FIG 0/19 when triggered (etisnoop)
5. Test with real receivers
6. Verify auto-switching works
7. Test stop mechanism
8. Check timeout behavior

**Weekly testing:**
```bash
# Automated test script
#!/bin/bash
echo "Testing emergency alert system..."
telnet localhost 9001 <<EOF
trigger_announcement test_service alarm test_audio
sleep 10
stop_announcement test_service
quit
EOF
echo "Test complete. Check receiver behavior."
```

### False Alarm Prevention

**Safeguards:**
1. **Authentication required** for remote control
2. **Audit logging** of all announcement triggers
3. **Rate limiting** (max 1 alarm per minute)
4. **Manual approval** for critical alerts
5. **Testing schedule** (avoid prime time)

**Configuration:**
```yaml
ensemble:
  remote_control:
    auth_enabled: true
    audit_log: '/var/log/dabmux/audit.log'

  announcement_limits:
    max_alarm_per_hour: 5
    max_traffic_per_hour: 20
```

### Legal Requirements

**Check local regulations:**
- Some countries require EAS capability
- Specific announcement types may be mandated
- Testing schedules may be required
- Cooperation with emergency authorities

**Example (USA):**
- FCC requires EAS participation
- Weekly tests required
- Monthly state tests
- CAP (Common Alerting Protocol) integration

**Example (EU):**
- Alert systems may be mandated by member states
- DAB announcements supplement cell broadcast
- Public warning system integration

### Emergency Procedures

**Create emergency playbook:**

1. **Alert received:**
   - Verify authenticity
   - Assess severity
   - Choose announcement type

2. **Trigger announcement:**
   - Use dedicated emergency audio
   - Include clear instructions
   - Repeat key information

3. **Monitor:**
   - Check transmission
   - Verify receiver behavior
   - Log all actions

4. **Stop announcement:**
   - When all-clear given
   - Verify return to normal
   - Log completion

5. **Post-event:**
   - Review logs
   - Analyze performance
   - Update procedures

---

## Integration

### CAP (Common Alerting Protocol)

**Parse CAP feeds and trigger DAB announcements:**

```python
#!/usr/bin/env python3
"""Integrate CAP alerts with DAB announcements."""
import requests
import xml.etree.ElementTree as ET
from dabmux_client import DABMuxClient

client = DABMuxClient(password='password')

# CAP feed URL
CAP_URL = 'https://alerts.weather.gov/cap/us.php?x=0'

def check_cap_alerts():
    response = requests.get(CAP_URL)
    root = ET.fromstring(response.content)

    for alert in root.findall('.//{urn:oasis:names:tc:emergency:cap:1.2}alert'):
        severity = alert.find('.//{urn:oasis:names:tc:emergency:cap:1.2}severity').text
        event = alert.find('.//{urn:oasis:names:tc:emergency:cap:1.2}event').text

        # Map CAP severity to DAB announcement type
        if severity in ['Extreme', 'Severe']:
            ann_type = 'alarm'
        elif 'Weather' in event:
            ann_type = 'area_weather'
        elif 'Traffic' in event:
            ann_type = 'road_traffic'
        else:
            ann_type = 'warning_service'

        # Trigger announcement
        print(f"Triggering {ann_type}: {event}")
        client.trigger_announcement(
            service_uid='emergency_service',
            announcement_type=ann_type,
            subchannel_uid='emergency_audio'
        )

if __name__ == '__main__':
    check_cap_alerts()
```

### Automation Systems

**Integrate with broadcast automation:**

```python
#!/usr/bin/env python3
"""Trigger announcements from automation cues."""
import socket
from dabmux_client import DABMuxClient

client = DABMuxClient(password='password')

# Listen for automation cues (example: TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('0.0.0.0', 5000))
sock.listen(1)

while True:
    conn, addr = sock.accept()
    data = conn.recv(1024).decode()

    # Parse automation cue
    # Format: "ANNOUNCE <type> <duration>"
    if data.startswith('ANNOUNCE'):
        _, ann_type, duration = data.split()

        # Trigger announcement
        client.trigger_announcement(
            service_uid='radio_service',
            announcement_type=ann_type
        )

        # Schedule stop
        import time
        time.sleep(int(duration))
        client.stop_announcement('radio_service')

    conn.close()
```

---

## Testing

### Verify FIG 0/18 Transmission

```bash
# Generate ETI
python -m dabmux.cli -c config.yaml -o test.eti -f raw -n 100

# Check for FIG 0/18
etisnoop -i test.eti | grep "FIG 0/18"

# Expected output:
# FIG 0/18: Announcement support
#   SId: 0x5001 (My Radio)
#   ASu flags: 0x0401 (Alarm, News flash)
#   Cluster Id: 0
```

### Verify FIG 0/19 When Triggered

```bash
# Start multiplexer
python -m dabmux.cli -c config.yaml -o test.eti -f raw &

# Trigger announcement
telnet localhost 9001 <<EOF
trigger_announcement my_radio alarm
quit
EOF

# Check ETI output
etisnoop -i test.eti | grep "FIG 0/19"

# Expected output:
# FIG 0/19: Announcement switching
#   Cluster Id: 0
#   ASw flags: 0x0001 (Alarm active)
#   SubChId: 1 (Emergency audio)
```

### Test with Real Receiver

**Procedure:**
1. Tune receiver to DAB ensemble
2. Enable announcement auto-switching in receiver settings
3. Trigger announcement via remote control
4. Verify receiver switches to announcement
5. Verify volume boost applied
6. Verify display shows alert
7. Stop announcement
8. Verify receiver returns to normal service

**Expected behavior:**
- Immediate switch (< 1 second)
- Clear audio from announcement subchannel
- Prominent display
- Return to normal when stopped

---

## Troubleshooting

### Announcement Not Triggering

**Check configuration:**
1. `announcements: enabled: true` in service config
2. Announcement type listed in `types`
3. FIG 0/18 transmitted (verify with etisnoop)

**Check remote control:**
1. Authentication successful
2. Command syntax correct
3. Service UID matches configuration

**Check logs:**
```bash
python -m dabmux.cli -c config.yaml -o test.eti --verbose
```

### Receiver Not Switching

**Check receiver settings:**
1. Announcement auto-switch enabled
2. Specific announcement type enabled
3. Service not blacklisted

**Check signal quality:**
1. Adequate signal strength
2. No audio dropouts
3. FIC decoded successfully

**Check FIG 0/19:**
```bash
etisnoop -i test.eti | grep "FIG 0/19"
```

### Announcement Doesn't Stop

**Check timeout:**
- Default: 60 seconds
- Increase if needed: `timeout_seconds: 120`

**Manual stop:**
```bash
telnet localhost 9001
> stop_announcement my_radio
```

**Check logs for errors:**
```bash
tail -f /var/log/dabmux/dabmux.log
```

---

## Resources

**Standards:**
- ETSI EN 300 401 Section 8.1.6 - Announcements
- CAP (Common Alerting Protocol) - OASIS standard

**Examples:**
- `examples/priority1_emergency_alerting.yaml` - Complete example
- `examples/cap_integration.py` - CAP alert integration

**Tools:**
- etisnoop - Verify FIG 0/18 and 0/19
- DAB receiver - Test announcement behavior

---

**Last Updated:** 2026-02-22

**Status:** Production Ready

For additional help, see [Remote Control Guide](REMOTE_CONTROL_GUIDE.md) or [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md).
