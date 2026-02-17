# Extending python-dabmux

Guide to extending python-dabmux with custom inputs, outputs, and FIG generators.

## Overview

python-dabmux is designed to be extensible. You can add:
- Custom input sources
- Custom output destinations
- Custom FIG generators
- Custom audio parsers

## Custom Input Sources

Create custom inputs by subclassing `InputBase`.

### Basic Template

```python
from dabmux.input.base import InputBase
from typing import Optional

class CustomInput(InputBase):
    """Custom input source implementation."""

    def __init__(self, config: dict):
        """Initialize with configuration."""
        self.config = config
        self.buffer = bytearray()
        self.connected = False

    def open(self) -> None:
        """Open/initialize the input source."""
        # Setup connection, open files, etc.
        self.connected = True
        print("Custom input opened")

    def close(self) -> None:
        """Close/cleanup the input source."""
        # Cleanup resources
        self.connected = False
        print("Custom input closed")

    def read_frame(self, frame_size: int) -> Optional[bytes]:
        """
        Read one audio/data frame.

        Args:
            frame_size: Number of bytes to read

        Returns:
            Frame data, or None if no data available
        """
        if not self.connected:
            return None

        # Ensure buffer has enough data
        while len(self.buffer) < frame_size:
            chunk = self._receive_data()
            if not chunk:
                return None
            self.buffer.extend(chunk)

        # Extract frame from buffer
        frame = bytes(self.buffer[:frame_size])
        self.buffer = self.buffer[frame_size:]
        return frame

    def seek(self, position: int) -> None:
        """
        Seek to position (optional, can raise NotImplementedError).
        """
        raise NotImplementedError("Seeking not supported")

    def _receive_data(self) -> Optional[bytes]:
        """Receive data chunk (implement your protocol here)."""
        # Implement your data reception logic
        pass
```

### Example: HTTP Streaming Input

```python
import requests
from dabmux.input.base import InputBase
from typing import Optional

class HttpStreamInput(InputBase):
    """Stream audio from HTTP URL."""

    def __init__(self, url: str, chunk_size: int = 8192):
        self.url = url
        self.chunk_size = chunk_size
        self.response = None
        self.iterator = None

    def open(self) -> None:
        """Start HTTP streaming."""
        self.response = requests.get(self.url, stream=True)
        self.response.raise_for_status()
        self.iterator = self.response.iter_content(chunk_size=self.chunk_size)

    def close(self) -> None:
        """Close HTTP connection."""
        if self.response:
            self.response.close()

    def read_frame(self, frame_size: int) -> Optional[bytes]:
        """Read frame from stream."""
        try:
            chunk = next(self.iterator)
            return chunk[:frame_size] if len(chunk) >= frame_size else chunk
        except StopIteration:
            return None

    def seek(self, position: int) -> None:
        """Not supported for HTTP streams."""
        raise NotImplementedError("Cannot seek in HTTP stream")
```

**Usage:**
```python
from dabmux.mux import DabMultiplexer

# Create custom input
http_input = HttpStreamInput('https://stream.example.com/audio.mp2')
http_input.open()

# Register with multiplexer
mux.add_input('subchannel1', http_input)
```

### Example: Pipe Input

```python
import subprocess
from dabmux.input.base import InputBase
from typing import Optional

class PipeInput(InputBase):
    """Read audio from pipe (e.g., ffmpeg output)."""

    def __init__(self, command: list[str]):
        """
        Initialize pipe input.

        Args:
            command: Command to execute (e.g., ['ffmpeg', '-i', ...])
        """
        self.command = command
        self.process = None

    def open(self) -> None:
        """Start subprocess."""
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

    def close(self) -> None:
        """Terminate subprocess."""
        if self.process:
            self.process.terminate()
            self.process.wait()

    def read_frame(self, frame_size: int) -> Optional[bytes]:
        """Read frame from pipe."""
        if not self.process or not self.process.stdout:
            return None

        data = self.process.stdout.read(frame_size)
        return data if len(data) == frame_size else None

    def seek(self, position: int) -> None:
        """Not supported for pipes."""
        raise NotImplementedError("Cannot seek in pipe")
```

**Usage:**
```python
# Encode live audio with ffmpeg and pipe to multiplexer
pipe_input = PipeInput([
    'ffmpeg',
    '-f', 'alsa',           # Input from ALSA (Linux audio)
    '-i', 'default',
    '-c:a', 'mp2',          # Encode to MPEG Layer II
    '-b:a', '128k',
    '-ar', '48000',
    '-f', 'mp2',
    'pipe:1'                # Output to stdout
])
pipe_input.open()
mux.add_input('live_audio', pipe_input)
```

## Custom Output Destinations

Create custom outputs by subclassing `DabOutput`.

### Basic Template

```python
from dabmux.output.base import DabOutput

class CustomOutput(DabOutput):
    """Custom output destination."""

    def __init__(self, target: str):
        """Initialize with target destination."""
        self.target = target
        self.handle = None

    def open(self, *args, **kwargs) -> None:
        """Open output destination."""
        # Initialize output (open connection, file, etc.)
        print(f"Opening output to {self.target}")

    def close(self) -> None:
        """Close output destination."""
        # Cleanup
        if self.handle:
            self.handle.close()
        print("Output closed")

    def write(self, data: bytes) -> None:
        """
        Write data to output.

        Args:
            data: Binary data to write (typically ETI frame)
        """
        # Write data to destination
        pass

    def get_info(self) -> str:
        """Get output description string."""
        return f"Custom Output: {self.target}"
```

### Example: Database Output

```python
import sqlite3
from datetime import datetime
from dabmux.output.base import DabOutput

class DatabaseOutput(DabOutput):
    """Store ETI frames in SQLite database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def open(self, *args, **kwargs) -> None:
        """Open database connection."""
        self.conn = sqlite3.connect(self.db_path)
        # Create table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS eti_frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                frame_data BLOB
            )
        ''')
        self.conn.commit()

    def close(self) -> None:
        """Close database."""
        if self.conn:
            self.conn.close()

    def write(self, data: bytes) -> None:
        """Store frame in database."""
        timestamp = datetime.now().isoformat()
        self.conn.execute(
            'INSERT INTO eti_frames (timestamp, frame_data) VALUES (?, ?)',
            (timestamp, data)
        )
        self.conn.commit()

    def get_info(self) -> str:
        return f"Database: {self.db_path}"
```

### Example: Multi-Destination Output

```python
from dabmux.output.base import DabOutput
from typing import List

class MultiOutput(DabOutput):
    """Write to multiple outputs simultaneously."""

    def __init__(self, outputs: List[DabOutput]):
        self.outputs = outputs

    def open(self, *args, **kwargs) -> None:
        """Open all outputs."""
        for output in self.outputs:
            output.open(*args, **kwargs)

    def close(self) -> None:
        """Close all outputs."""
        for output in self.outputs:
            output.close()

    def write(self, data: bytes) -> None:
        """Write to all outputs."""
        for output in self.outputs:
            output.write(data)

    def get_info(self) -> str:
        infos = [output.get_info() for output in self.outputs]
        return f"Multi: {', '.join(infos)}"
```

**Usage:**
```python
from dabmux.output.file import FileOutput
from dabmux.output.edi import EdiOutput

# Create multiple outputs
file_out = FileOutput()
file_out.open('archive.eti')

edi_out = EdiOutput('239.1.2.3', 12000)
edi_out.open()

# Combine into multi-output
multi = MultiOutput([file_out, edi_out])

# Use with multiplexer
while running:
    frame = mux.generate_frame()
    multi.write(frame.pack())
```

## Custom FIG Generators

Extend FIC encoder with custom FIG types.

### Example: Custom FIG Type

```python
from dabmux.fig.base import FigGenerator
from typing import List

class CustomFigGenerator(FigGenerator):
    """Generate custom FIG type."""

    def __init__(self, ensemble):
        self.ensemble = ensemble

    def generate(self) -> List[bytes]:
        """
        Generate FIG data items.

        Returns:
            List of FIG data blocks (each max 30 bytes)
        """
        figs = []

        # Build your FIG data
        fig_data = bytearray()

        # FIG header (1 byte)
        fig_type = 0  # FIG type (0-7)
        extension = 0  # Extension (0-31)
        fig_header = (fig_type << 5) | extension
        fig_data.append(fig_header)

        # Add your data
        # ... (implement your FIG content)

        # Split into 30-byte blocks if needed
        max_size = 30
        for i in range(0, len(fig_data), max_size):
            figs.append(bytes(fig_data[i:i+max_size]))

        return figs

    def get_repetition_rate(self) -> float:
        """
        Get repetition rate in seconds.

        Returns:
            How often this FIG should be transmitted (seconds)
        """
        return 1.0  # Transmit every 1 second
```

**Register with FIC encoder:**
```python
from dabmux.fig.fic import FICEncoder

fic_encoder = FICEncoder(ensemble)

# Add custom FIG generator
custom_fig = CustomFigGenerator(ensemble)
fic_encoder.add_generator(custom_fig)
```

## Registering Custom Components

### URI Scheme Handler

Register custom input URI schemes:

```python
from dabmux.input import register_input_handler

def create_custom_input(uri: str):
    """Factory function for custom input."""
    # Parse URI and create input instance
    # uri format: custom://host:port/path
    return CustomInput(uri)

# Register handler
register_input_handler('custom', create_custom_input)
```

**Usage in configuration:**
```yaml
subchannels:
  - uid: 'sub1'
    input: 'custom://server:9000/stream'  # Uses custom handler
```

## Plugin Architecture

### Creating a Plugin

```python
# my_plugin.py
from dabmux.plugins import DabMuxPlugin

class MyPlugin(DabMuxPlugin):
    """Custom plugin for python-dabmux."""

    name = "my-plugin"
    version = "1.0.0"

    def on_frame_generated(self, frame):
        """Called after each frame is generated."""
        print(f"Frame {frame.fc.fct} generated")

    def on_multiplexer_start(self, mux):
        """Called when multiplexer starts."""
        print("Multiplexer started")

    def on_multiplexer_stop(self, mux):
        """Called when multiplexer stops."""
        print("Multiplexer stopped")
```

**Load plugin:**
```python
from dabmux.plugins import load_plugin

plugin = load_plugin('my_plugin.MyPlugin')
mux.register_plugin(plugin)
```

## Testing Custom Components

### Unit Tests for Custom Input

```python
import pytest
from my_custom_input import CustomInput

def test_custom_input_open():
    """Test opening custom input."""
    input_source = CustomInput({'url': 'test://example'})
    input_source.open()
    assert input_source.connected

def test_custom_input_read_frame():
    """Test reading frame."""
    input_source = CustomInput({'url': 'test://example'})
    input_source.open()

    frame = input_source.read_frame(960)
    assert frame is not None
    assert len(frame) == 960

    input_source.close()

def test_custom_input_close():
    """Test closing custom input."""
    input_source = CustomInput({'url': 'test://example'})
    input_source.open()
    input_source.close()
    assert not input_source.connected
```

## Performance Considerations

### Input Performance

- **Buffering**: Implement internal buffering to smooth data flow
- **Threading**: Consider threading for slow input sources
- **Error handling**: Handle transient errors gracefully

```python
import threading
import queue

class BufferedInput(InputBase):
    """Input with background buffering thread."""

    def __init__(self, source):
        self.source = source
        self.buffer = queue.Queue(maxsize=100)
        self.thread = None
        self.running = False

    def open(self) -> None:
        self.source.open()
        self.running = True
        self.thread = threading.Thread(target=self._fill_buffer)
        self.thread.start()

    def _fill_buffer(self):
        """Background thread to fill buffer."""
        while self.running:
            chunk = self.source.read_frame(960)
            if chunk:
                self.buffer.put(chunk)

    def read_frame(self, frame_size: int) -> Optional[bytes]:
        try:
            return self.buffer.get(timeout=1.0)
        except queue.Empty:
            return None

    def close(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join()
        self.source.close()
```

### Output Performance

- **Batch writes**: Write multiple frames at once when possible
- **Async I/O**: Use async for network outputs
- **Buffering**: Buffer writes for better performance

## Best Practices

1. **Follow base class interfaces**: Implement all required methods
2. **Handle errors gracefully**: Don't crash the multiplexer
3. **Document your code**: Include docstrings and examples
4. **Add tests**: Unit test your components
5. **Consider threading**: Use threads for slow operations
6. **Log appropriately**: Use structlog for consistent logging

```python
import structlog

logger = structlog.get_logger(__name__)

class MyCustomInput(InputBase):
    def open(self) -> None:
        logger.info("Opening custom input", source=self.source)
        # ...

    def read_frame(self, frame_size: int) -> Optional[bytes]:
        logger.debug("Reading frame", size=frame_size)
        # ...
```

## See Also

- [API Reference](../api-reference/index.md) - Base classes and interfaces
- [Input API](../api-reference/input.md) - Input source details
- [Output API](../api-reference/output.md) - Output destination details
- [Development Guide](../development/contributing.md) - Contributing guidelines
