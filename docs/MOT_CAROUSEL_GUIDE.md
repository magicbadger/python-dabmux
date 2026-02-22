# MOT Carousel Guide

**Multimedia Object Transfer (MOT) Protocol for DAB**

This guide explains how to use MOT carousels to deliver images, text, and other multimedia content to DAB receivers.

---

## Table of Contents

1. [What is MOT?](#what-is-mot)
2. [Quick Start](#quick-start)
3. [Slideshow Mode](#slideshow-mode)
4. [Directory Browsing Mode](#directory-browsing-mode)
5. [EPG (Electronic Programme Guide)](#epg-electronic-programme-guide)
6. [Configuration Reference](#configuration-reference)
7. [File Formats](#file-formats)
8. [Troubleshooting](#troubleshooting)

---

## What is MOT?

MOT (Multimedia Object Transfer) is a protocol for delivering multimedia content over DAB:

- **Slideshow:** Display images synchronized with audio (album art, artist photos)
- **Directory Browsing:** Present hierarchical menus to users
- **EPG:** Electronic Programme Guide with schedule information
- **Text:** Deliver formatted text, news bulletins, lyrics

**Standards:** ETSI TS 101 756

---

## Quick Start

### 1. Create a MOT Directory

```bash
mkdir -p /path/to/mot/slideshow
```

### 2. Add Images

```bash
# Copy JPEG or PNG images
cp album_art.jpg /path/to/mot/slideshow/
cp artist_photo.png /path/to/mot/slideshow/
```

### 3. Configure MOT in YAML

```yaml
# Add to your DAB configuration file

subchannels:
  # Regular audio subchannel
  - uid: 'audio_main'
    id: 0
    type: 'dabplus'
    bitrate: 48
    protection: 'EEP_3A'
    input_uri: 'file://audio/music.dabp'

  # MOT data subchannel
  - uid: 'mot_slideshow'
    id: 1
    type: 'packet'
    bitrate: 16          # 16 kbps for slideshow
    protection: 'EEP_2A'

services:
  - uid: 'radio_service'
    id: 0x5001
    label:
      text: 'My Radio'

components:
  # Audio component
  - uid: 'audio_component'
    service_id: '0x5001'
    subchannel_id: 0
    label:
      text: 'Main Programme'

  # MOT component
  - uid: 'mot_component'
    service_id: '0x5001'
    subchannel_id: 1
    is_packet_mode: true
    packet:
      address: 0
      ua_types:
        - type: 2  # MOT Slideshow
    carousel_enabled: true
    carousel_directory: '/path/to/mot/slideshow'
```

### 4. Start the Multiplexer

```bash
python -m dabmux.cli -c config.yaml -o output.eti -f raw
```

### 5. Verify

```bash
# Check ETI output
~/git/etisnoop/etisnoop -i output.eti | grep -i "mot\|packet"

# You should see:
# - Packet mode subchannel
# - MOT objects being transmitted
```

---

## Slideshow Mode

Display images synchronized with your audio content.

### Use Cases

- Album artwork
- Artist photos
- Station logos
- Sponsor images
- Event posters

### Configuration

```yaml
components:
  - uid: 'slideshow_component'
    service_id: '0x5001'
    subchannel_id: 1  # Packet mode subchannel
    is_packet_mode: true
    packet:
      address: 0
      ua_types:
        - type: 2  # MOT Slideshow
          data: [12]  # Application type (12 = unrestricted slideshow)
    carousel_enabled: true
    carousel_directory: '/path/to/slideshow/images'
```

### Supported Image Formats

**JPEG:**
- Recommended: 320x240 pixels
- Maximum: 640x480 pixels
- Quality: 70-80%
- File size: < 50 KB per image

**PNG:**
- Recommended: 320x240 pixels
- Maximum: 640x480 pixels
- File size: < 50 KB per image

### Directory Structure

```
/path/to/slideshow/images/
├── 001_station_logo.jpg    # Rotates in order
├── 002_album_art.jpg
├── 003_artist.jpg
└── 004_sponsor.png
```

**Naming Convention:**
- Files transmitted in alphabetical order
- Use numeric prefixes for control (001_, 002_, etc.)
- Lowercase extensions (.jpg, .png)

### Timing

**Carousel Parameters:**
- **Interval:** Images rotate every 30 seconds (configurable)
- **Transmission:** Images repeat continuously in a loop
- **Update:** Add/remove files while running (auto-detected)

### Image Metadata

Add metadata to images for better receiver display:

```python
# Optional: Use EXIF/IPTC metadata
# Title: Image title shown on receiver
# Description: Optional description
# Copyright: Copyright notice
```

### Dynamic Updates

The carousel automatically detects file changes:

```bash
# Add new image (will be picked up automatically)
cp new_image.jpg /path/to/slideshow/images/

# Remove image
rm /path/to/slideshow/images/old_image.jpg

# Carousel updates within 1-2 rotation cycles
```

---

## Directory Browsing Mode

Create hierarchical menus for user navigation.

### Use Cases

- Station information menus
- Programme schedules
- Contact information
- Advertising categories
- Service guides

### Configuration

```yaml
components:
  - uid: 'directory_component'
    service_id: '0x5001'
    subchannel_id: 1
    is_packet_mode: true
    packet:
      address: 0
      ua_types:
        - type: 4  # MOT Directory Browsing
    carousel_enabled: true
    carousel_directory: '/path/to/directory/structure'
```

### Directory Structure

```
/path/to/directory/structure/
├── index.html              # Root menu
├── about/
│   ├── station_info.html
│   ├── contact.html
│   └── team.html
├── schedule/
│   ├── today.html
│   └── week.html
└── images/
    └── logo.jpg
```

### HTML Format

Simple HTML for DAB receivers:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Station Menu</title>
</head>
<body>
    <h1>My Radio Station</h1>
    <ul>
        <li><a href="about/station_info.html">About Us</a></li>
        <li><a href="schedule/today.html">Today's Schedule</a></li>
        <li><a href="contact.html">Contact</a></li>
    </ul>
</body>
</html>
```

**Supported HTML:**
- Basic tags: `<h1>`, `<p>`, `<ul>`, `<li>`, `<a>`
- Links: Relative URLs only
- Images: `<img src="images/logo.jpg">`
- Formatting: `<b>`, `<i>`, `<br>`

**Not Supported:**
- JavaScript
- CSS (limited styling only)
- External resources
- Forms

---

## EPG (Electronic Programme Guide)

Deliver programme schedules to receivers.

### Use Cases

- Broadcast schedules
- Programme descriptions
- Cast and crew information
- Genre classification

### Configuration

```yaml
components:
  - uid: 'epg_component'
    service_id: '0x5001'
    subchannel_id: 1
    is_packet_mode: true
    packet:
      address: 0
      ua_types:
        - type: 6  # EPG
    carousel_enabled: true
    carousel_directory: '/path/to/epg/data'
```

### EPG Data Format

Create XML files with programme information:

```xml
<!-- /path/to/epg/data/schedule.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<epg>
  <programme start="20260222080000" stop="20260222100000">
    <title>Morning Show</title>
    <description>Wake up with music and news</description>
    <category>Music</category>
    <presenter>John Doe</presenter>
  </programme>

  <programme start="20260222100000" stop="20260222120000">
    <title>Midday News</title>
    <description>Latest news and weather</description>
    <category>News</category>
  </programme>
</epg>
```

**Time Format:** YYYYMMDDHHmmss (UTC or local)

### EPG Updates

Update schedule files dynamically:

```bash
# Generate daily schedule
python generate_epg.py > /path/to/epg/data/schedule.xml

# Multiplexer automatically detects changes
```

---

## Configuration Reference

### User Application Types

Specify what type of MOT content:

```yaml
packet:
  ua_types:
    - type: 2   # MOT Slideshow
      data: [12]  # Unrestricted slideshow

    - type: 4   # MOT Directory Browsing
      data: []    # No additional data

    - type: 6   # EPG
      data: []    # No additional data
```

**Common Types:**
- `2` - MOT Slideshow
- `4` - MOT Directory Browsing (BWS)
- `6` - EPG (Electronic Programme Guide)
- `7` - Journaline (news)
- Custom types (0x1000+)

### Bitrate Recommendations

**Slideshow:**
- Low quality: 8 kbps (small images, slow updates)
- Medium quality: 16 kbps (recommended)
- High quality: 24 kbps (larger images, faster updates)

**Directory Browsing:**
- Small menus: 8 kbps
- Medium menus: 12 kbps
- Large menus: 16 kbps

**EPG:**
- Daily schedule: 8 kbps
- Weekly schedule: 12-16 kbps

### Protection Levels

**For Data Services:**
- `EEP_1A` - Low protection (good RF conditions)
- `EEP_2A` - Medium protection (recommended)
- `EEP_3A` - High protection (poor RF conditions)

### Packet Addresses

- Use `address: 0` for primary data service
- Use different addresses for multiple data services
- Range: 0-1023

---

## File Formats

### JPEG Images

**Recommended Settings:**
```bash
# Convert image to DAB-optimized JPEG
convert input.jpg \
  -resize 320x240 \
  -quality 75 \
  -sampling-factor 4:2:0 \
  output.jpg
```

**Requirements:**
- Baseline JPEG (not progressive)
- YCbCr color space
- 4:2:0 chroma subsampling
- File size < 50 KB

### PNG Images

**Recommended Settings:**
```bash
# Convert image to optimized PNG
convert input.png \
  -resize 320x240 \
  -colors 256 \
  output.png

# Further optimize
pngcrush output.png optimized.png
```

**Requirements:**
- 8-bit color depth (256 colors) or 24-bit RGB
- No alpha channel transparency (or use binary transparency)
- File size < 50 KB

### HTML/XML Files

**Encoding:** UTF-8
**Line endings:** LF (Unix-style)
**File size:** < 10 KB per file

---

## Troubleshooting

### Images Not Appearing

**Check:**
1. Carousel enabled: `carousel_enabled: true`
2. Directory path correct: `carousel_directory: '/full/path'`
3. Image format: JPEG or PNG
4. Image size: < 50 KB
5. File permissions: Readable by multiplexer process
6. Packet mode configured: `is_packet_mode: true`
7. User application type: `type: 2` for slideshow

**Debug:**
```bash
# Check if files are detected
ls -lh /path/to/slideshow/images/

# Check multiplexer logs
python -m dabmux.cli -c config.yaml -o test.eti -f raw -n 100 --verbose
```

### Images Too Large

**Symptoms:** Slow transmission, receiver timeouts

**Solutions:**
```bash
# Resize images
for img in *.jpg; do
  convert "$img" -resize 320x240 -quality 75 "resized_$img"
done

# Check file sizes
du -h *.jpg
```

**Target:** < 50 KB per image

### Carousel Not Updating

**Check:**
1. File modification time: `ls -lt /path/to/images/`
2. Multiplexer restart: Changes may require restart
3. Directory watch: Some systems may need manual trigger

**Force Update:**
```bash
# Touch files to update timestamp
touch /path/to/slideshow/images/*

# Or restart multiplexer
pkill -HUP dabmux  # If running as daemon
```

### Wrong Display Order

**Rename files with numeric prefixes:**
```bash
# Rename for specific order
mv album_art.jpg 001_album_art.jpg
mv artist.jpg 002_artist.jpg
mv logo.png 003_logo.png
```

Files transmit in alphabetical order.

### Receiver Not Showing MOT

**Check Receiver:**
1. MOT support: Does receiver support slideshow?
2. Data service selected: Switch to data component
3. User application: Receiver must support MOT type
4. Signal quality: Poor signal may prevent data reception

**Check Configuration:**
```yaml
# Ensure packet component linked to service
components:
  - uid: 'mot_component'
    service_id: '0x5001'     # Must match service
    subchannel_id: 1         # Must match MOT subchannel
    is_packet_mode: true     # Required
    packet:
      address: 0             # Primary data service
      ua_types:
        - type: 2            # MOT Slideshow
```

---

## Advanced Topics

### Multiple MOT Services

Deliver different content types simultaneously:

```yaml
subchannels:
  - uid: 'audio'
    id: 0
    type: 'dabplus'
    bitrate: 48

  - uid: 'mot_slideshow'
    id: 1
    type: 'packet'
    bitrate: 16

  - uid: 'mot_epg'
    id: 2
    type: 'packet'
    bitrate: 8

components:
  - uid: 'audio_comp'
    service_id: '0x5001'
    subchannel_id: 0

  - uid: 'slideshow_comp'
    service_id: '0x5001'
    subchannel_id: 1
    is_packet_mode: true
    packet:
      address: 0
      ua_types:
        - type: 2  # Slideshow
    carousel_enabled: true
    carousel_directory: '/path/to/slideshow'

  - uid: 'epg_comp'
    service_id: '0x5001'
    subchannel_id: 2
    is_packet_mode: true
    packet:
      address: 1  # Different address
      ua_types:
        - type: 6  # EPG
    carousel_enabled: true
    carousel_directory: '/path/to/epg'
```

### Dynamic Content Updates

Script to update slideshow based on current song:

```bash
#!/bin/bash
# update_slideshow.sh - Update slideshow with current track art

SLIDESHOW_DIR="/path/to/mot/slideshow"
CURRENT_TRACK="$1"

# Fetch album art for current track
fetch_album_art "$CURRENT_TRACK" > /tmp/current_art.jpg

# Resize and optimize
convert /tmp/current_art.jpg \
  -resize 320x240 \
  -quality 75 \
  "$SLIDESHOW_DIR/001_current_track.jpg"

# Add track info overlay (optional)
convert "$SLIDESHOW_DIR/001_current_track.jpg" \
  -pointsize 20 \
  -draw "text 10,230 '$CURRENT_TRACK'" \
  "$SLIDESHOW_DIR/001_current_track.jpg"
```

---

## Best Practices

### Image Quality vs. Size

**Balance:**
- Use JPEG for photos (better compression)
- Use PNG for logos/graphics (sharp edges)
- Target 30-40 KB per image
- Test on actual DAB receivers

### Update Frequency

**Recommendations:**
- Slideshow: Update every 3-5 minutes
- Directory: Update daily or when content changes
- EPG: Update daily or twice daily

### Content Organization

```
mot_content/
├── slideshow/
│   ├── current/      # Active rotation
│   ├── archive/      # Previous images
│   └── incoming/     # Staging area
├── directory/
│   └── menu/
└── epg/
    └── schedules/
```

### Monitoring

Check carousel statistics via remote control:

```bash
# Using telnet
telnet localhost 9001
> get_carousel_stats mot_component

# Using ZMQ API
curl http://localhost:9000 -d '
{
  "command": "get_carousel_stats",
  "args": {"component_uid": "mot_component"}
}'
```

---

## Resources

**Standards:**
- ETSI TS 101 756 - MOT Protocol
- ETSI EN 300 401 - DAB System

**Tools:**
- ImageMagick - Image processing
- pngcrush - PNG optimization
- ffmpeg - Image conversion

**Examples:**
- See `examples/mot_carousel_example.yaml` for complete configuration
- Sample images in `examples/mot/slideshow/` (if available)

---

## Support

For issues or questions:
1. Check multiplexer logs for errors
2. Verify configuration with `--dry-run` mode
3. Test with etisnoop to verify packet mode
4. Check receiver compatibility
5. See project README for additional help

---

**Last Updated:** 2026-02-22
**Status:** Production Ready
