# Input Module

Input sources for audio and data streams.

## Module: `dabmux.input`

Provides input source implementations for reading audio/data from files and network.

## Base Class: `InputBase`

Abstract base class for all input sources.

### Module: `dabmux.input.base`

```python
from abc import ABC, abstractmethod
from typing import Optional

class InputBase(ABC):
    """Abstract base class for input sources."""

    @abstractmethod
    def open(self) -> None:
        """Open the input source."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the input source."""
        pass

    @abstractmethod
    def read_frame(self, frame_size: int) -> Optional[bytes]:
        """
        Read one audio/data frame.

        Args:
            frame_size: Number of bytes to read

        Returns:
            Frame data, or None if no data available
        """
        pass

    @abstractmethod
    def seek(self, position: int) -> None:
        """Seek to position in stream (if supported)."""
        pass
```

## File Input

### Module: `dabmux.input.file`

### Class: `FileInput`

Read audio/data from files with automatic looping.

```python
from dabmux.input.file import FileInput

# Create file input
input_source = FileInput('audio.mp2', loop=True)
input_source.open()

# Read frames
frame_data = input_source.read_frame(960)  # 960 bytes per frame

input_source.close()
```

#### Constructor

##### `__init__(file_path: str | Path, loop: bool = False)`

Create a file input source.

**Parameters:**
- `file_path: str | Path` - Path to input file
- `loop: bool` - Loop file when EOF reached (default: False)

**Example:**
```python
# Single-pass reading
input_source = FileInput('audio.mp2', loop=False)

# Continuous looping
input_source = FileInput('audio.mp2', loop=True)
```

#### Methods

##### `open() -> None`

Open the file for reading.

**Raises:**
- `FileNotFoundError` - If file doesn't exist
- `PermissionError` - If file can't be read

**Example:**
```python
input_source = FileInput('audio.mp2')
input_source.open()
```

##### `close() -> None`

Close the file.

**Example:**
```python
input_source.close()
```

##### `read_frame(frame_size: int) -> Optional[bytes]`

Read audio/data frame from file.

**Parameters:**
- `frame_size: int` - Number of bytes to read

**Returns:** Frame data, or `None` if EOF and not looping

**Behavior:**
- Reads exactly `frame_size` bytes
- If EOF reached and `loop=True`, seeks to beginning
- If EOF reached and `loop=False`, returns `None`

**Example:**
```python
# Read frames until EOF
while True:
    frame_data = input_source.read_frame(960)
    if frame_data is None:
        break
    # Process frame
```

##### `seek(position: int) -> None`

Seek to byte position in file.

**Parameters:**
- `position: int` - Byte offset (0 = start of file)

**Example:**
```python
# Seek to beginning
input_source.seek(0)

# Seek to 1 second (48000 Hz, 128 kbps MPEG Layer II)
input_source.seek(16000)  # ~1 second
```

#### File Format Support

Supported formats:

| Format | Extension | Description |
|--------|-----------|-------------|
| MPEG Layer II | `.mp2`, `.mp2a` | DAB audio |
| HE-AAC v2 | `.aac`, `.dabp` | DAB+ audio |
| Raw audio | `.raw` | Unframed audio data |

**Note:** File must contain properly framed audio data matching the subchannel configuration.

---

## Network Input

### Module: `dabmux.input.network`

### Class: `UdpInput`

Receive audio/data via UDP.

```python
from dabmux.input.network import UdpInput

# Listen on multicast group
input_source = UdpInput('239.1.2.3', 5001)
input_source.open()

# Read frames
frame_data = input_source.read_frame(960)

input_source.close()
```

#### Constructor

##### `__init__(host: str, port: int, buffer_size: int = 8192)`

Create a UDP input source.

**Parameters:**
- `host: str` - IP address to listen on (unicast or multicast)
- `port: int` - UDP port number
- `buffer_size: int` - Socket receive buffer size (default: 8192)

**Example:**
```python
# Multicast
input_source = UdpInput('239.1.2.3', 5001)

# Unicast
input_source = UdpInput('0.0.0.0', 5001)  # Listen on all interfaces

# Custom buffer size
input_source = UdpInput('239.1.2.3', 5001, buffer_size=16384)
```

#### Methods

##### `open() -> None`

Open UDP socket and bind to address.

**Raises:**
- `OSError` - If socket can't bind to address
- `PermissionError` - If port requires privileges

**Example:**
```python
input_source = UdpInput('239.1.2.3', 5001)
input_source.open()
```

##### `close() -> None`

Close UDP socket.

##### `read_frame(frame_size: int) -> Optional[bytes]`

Receive audio/data frame from UDP.

**Parameters:**
- `frame_size: int` - Expected frame size in bytes

**Returns:** Frame data, or `None` if no data received

**Behavior:**
- Blocks until data received or timeout
- Returns first `frame_size` bytes from packet
- Discards remaining data if packet > frame_size
- Returns `None` on timeout or error

**Example:**
```python
# Receive frames
while True:
    frame_data = input_source.read_frame(960)
    if frame_data:
        # Process frame
        pass
```

##### `seek(position: int) -> None`

Not supported for network inputs (raises `NotImplementedError`).

---

### Class: `TcpInput`

Receive audio/data via TCP.

```python
from dabmux.input.network import TcpInput

# Connect to TCP server
input_source = TcpInput('192.168.1.100', 5002)
input_source.open()

# Read frames
frame_data = input_source.read_frame(960)

input_source.close()
```

#### Constructor

##### `__init__(host: str, port: int, timeout: float = 5.0)`

Create a TCP input source.

**Parameters:**
- `host: str` - IP address to connect to
- `port: int` - TCP port number
- `timeout: float` - Connection timeout in seconds (default: 5.0)

**Example:**
```python
# Default timeout
input_source = TcpInput('192.168.1.100', 5002)

# Custom timeout
input_source = TcpInput('192.168.1.100', 5002, timeout=10.0)
```

#### Methods

##### `open() -> None`

Connect to TCP server.

**Raises:**
- `ConnectionError` - If connection fails
- `TimeoutError` - If connection times out

**Example:**
```python
input_source = TcpInput('192.168.1.100', 5002)
try:
    input_source.open()
except ConnectionError:
    print("Failed to connect to server")
```

##### `close() -> None`

Close TCP connection.

##### `read_frame(frame_size: int) -> Optional[bytes]`

Receive audio/data frame from TCP.

**Parameters:**
- `frame_size: int` - Number of bytes to read

**Returns:** Frame data, or `None` if connection closed

**Behavior:**
- Blocks until `frame_size` bytes received
- Returns `None` if connection closed
- Handles partial receives automatically

**Example:**
```python
# Receive frames
while True:
    frame_data = input_source.read_frame(960)
    if frame_data is None:
        print("Connection closed")
        break
    # Process frame
```

##### `seek(position: int) -> None`

Not supported for network inputs (raises `NotImplementedError`).

---

## Usage Examples

### Reading from File

```python
from dabmux.input.file import FileInput

# Open file input
input_source = FileInput('audio.mp2', loop=True)
input_source.open()

try:
    # Read 100 frames
    for _ in range(100):
        frame = input_source.read_frame(960)
        if frame:
            print(f"Read {len(frame)} bytes")
        else:
            print("No data")
            break
finally:
    input_source.close()
```

### Receiving from UDP

```python
from dabmux.input.network import UdpInput
import socket

# Create UDP input
input_source = UdpInput('239.1.2.3', 5001)
input_source.open()

try:
    # Receive continuously
    while True:
        frame = input_source.read_frame(960)
        if frame:
            print(f"Received {len(frame)} bytes")
except KeyboardInterrupt:
    print("Stopped")
finally:
    input_source.close()
```

### Receiving from TCP

```python
from dabmux.input.network import TcpInput

# Connect to TCP server
input_source = TcpInput('192.168.1.100', 5002, timeout=10.0)

try:
    input_source.open()
    print("Connected")

    # Receive frames
    while True:
        frame = input_source.read_frame(960)
        if frame is None:
            print("Connection closed")
            break
        print(f"Received {len(frame)} bytes")

except ConnectionError as e:
    print(f"Connection error: {e}")
finally:
    input_source.close()
```

### Using with Multiplexer

```python
from dabmux.mux import DabMultiplexer
from dabmux.input.file import FileInput
from dabmux.config import load_config

# Load configuration
ensemble = load_config('config.yaml')

# Create multiplexer
mux = DabMultiplexer(ensemble)

# Create and register inputs for each subchannel
for subchannel in ensemble.subchannels:
    # Extract file path from input URI
    uri = subchannel.input_uri
    if uri.startswith('file://'):
        file_path = uri[7:]  # Remove 'file://' prefix
        input_source = FileInput(file_path, loop=True)
        input_source.open()
        mux.add_input(subchannel.uid, input_source)

# Generate frames
try:
    while True:
        frame = mux.generate_frame()
        # Output frame
except KeyboardInterrupt:
    pass
finally:
    # Close all inputs
    for input_source in mux.inputs.values():
        input_source.close()
```

### Context Manager Pattern

```python
from contextlib import closing
from dabmux.input.file import FileInput

# Automatic cleanup with context manager
with closing(FileInput('audio.mp2')) as input_source:
    input_source.open()
    frame = input_source.read_frame(960)
    # Input automatically closed when exiting context
```

## Custom Input Source

### Creating a Custom Input

```python
from dabmux.input.base import InputBase
from typing import Optional

class StreamingInput(InputBase):
    """Custom streaming input source."""

    def __init__(self, url: str):
        self.url = url
        self.buffer = bytearray()

    def open(self) -> None:
        """Initialize streaming connection."""
        # Connect to streaming service
        pass

    def close(self) -> None:
        """Close streaming connection."""
        # Disconnect
        pass

    def read_frame(self, frame_size: int) -> Optional[bytes]:
        """Read frame from stream."""
        # Fill buffer if needed
        while len(self.buffer) < frame_size:
            chunk = self._receive_chunk()
            if not chunk:
                return None
            self.buffer.extend(chunk)

        # Extract frame
        frame = bytes(self.buffer[:frame_size])
        self.buffer = self.buffer[frame_size:]
        return frame

    def seek(self, position: int) -> None:
        """Not supported."""
        raise NotImplementedError("Streaming inputs don't support seeking")

    def _receive_chunk(self) -> Optional[bytes]:
        """Receive data chunk from stream."""
        # Implement streaming protocol
        pass
```

### Using Custom Input

```python
from dabmux.mux import DabMultiplexer

# Create custom input
custom_input = StreamingInput('https://stream.example.com/audio')
custom_input.open()

# Register with multiplexer
mux.add_input('subchannel1', custom_input)

# Use normally
frame = mux.generate_frame()
```

## Error Handling

```python
from dabmux.input.file import FileInput
from dabmux.input.network import UdpInput

# File input errors
try:
    input_source = FileInput('missing.mp2')
    input_source.open()
except FileNotFoundError:
    print("File not found")
except PermissionError:
    print("Permission denied")

# Network input errors
try:
    input_source = UdpInput('239.1.2.3', 5001)
    input_source.open()
except OSError as e:
    print(f"Network error: {e}")
```

## Performance Considerations

- **File I/O**: Use `loop=True` for continuous operation to avoid reopening files
- **UDP**: Use larger buffer sizes for high bitrate streams
- **TCP**: Connection setup has overhead; maintain persistent connections
- **Buffering**: Consider implementing input buffering for network sources

## See Also

- [Output Module](output.md) - Output destinations
- [User Guide: Inputs](../user-guide/inputs/index.md) - Detailed input guide
- [Mux API](mux.md) - Using inputs with multiplexer
- [Configuration](config.md) - Configuring input URIs
