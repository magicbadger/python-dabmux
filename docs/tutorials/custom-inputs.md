# Tutorial: Custom Inputs

Create custom input sources by extending python-dabmux's input classes.

**Difficulty:** Advanced
**Time:** 40 minutes

## What You'll Build

A custom input class that:
- Implements the InputBase interface
- Generates synthetic audio data
- Handles buffer management
- Integrates with the multiplexer

## Prerequisites

- Python programming experience
- Completed [Basic Single Service Tutorial](basic-single-service.md)
- Understanding of [System Design](../architecture/system-design.md)
- Familiarity with python-dabmux codebase

## Why Create Custom Inputs?

**Use cases:**
- Integrate with custom audio sources
- Generate test signals
- Interface with hardware devices
- Implement special buffering strategies
- Add monitoring and statistics

## Step 1: Understand InputBase Interface

### Read the InputBase Class

```python
from abc import ABC, abstractmethod

class InputBase(ABC):
    """Abstract base class for inputs."""

    @abstractmethod
    def open(self) -> None:
        """Open the input source."""
        pass

    @abstractmethod
    def read(self, size: int) -> bytes:
        """
        Read data from input.

        Args:
            size: Number of bytes to read

        Returns:
            bytes: Audio data (exactly size bytes)
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the input source."""
        pass

    def get_stats(self) -> dict:
        """Get input statistics (optional)."""
        return {}
```

**Required methods:**
- `open()`: Initialize input source
- `read(size)`: Return exactly `size` bytes
- `close()`: Clean up resources

**Optional methods:**
- `get_stats()`: Return statistics

## Step 2: Create Sine Wave Generator

Create a custom input that generates a sine wave test signal.

### Create the Class

Create `custom_sine_input.py`:

```python
import math
import struct
from dabmux.input.base import InputBase


class SineWaveInput(InputBase):
    """
    Custom input that generates a sine wave test signal.

    Generates stereo 16-bit PCM at 48 kHz, then encodes to MPEG Layer II format.
    """

    def __init__(self, frequency: float = 1000.0):
        """
        Initialize sine wave generator.

        Args:
            frequency: Sine wave frequency in Hz (default: 1000 Hz)
        """
        self.frequency = frequency
        self.sample_rate = 48000  # DAB standard
        self.phase = 0.0
        self.bytes_read = 0

    def open(self) -> None:
        """Open the input (initialize state)."""
        self.phase = 0.0
        self.bytes_read = 0
        print(f"SineWaveInput: Opened with {self.frequency} Hz")

    def read(self, size: int) -> bytes:
        """
        Generate sine wave audio data.

        Args:
            size: Number of bytes to read

        Returns:
            bytes: Generated audio data
        """
        # Calculate number of samples needed
        # Each sample: 4 bytes (2 bytes/channel × 2 channels)
        num_samples = size // 4

        data = bytearray()

        for _ in range(num_samples):
            # Generate sine wave sample
            sample_value = math.sin(2.0 * math.pi * self.frequency * self.phase / self.sample_rate)

            # Convert to 16-bit integer (-32768 to 32767)
            sample_int = int(sample_value * 32767.0)

            # Clamp to 16-bit range
            sample_int = max(-32768, min(32767, sample_int))

            # Pack as stereo (same value for both channels)
            # Little-endian signed 16-bit
            data.extend(struct.pack('<h', sample_int))  # Left channel
            data.extend(struct.pack('<h', sample_int))  # Right channel

            self.phase += 1

        self.bytes_read += len(data)

        # Pad if needed
        while len(data) < size:
            data.append(0)

        return bytes(data[:size])

    def close(self) -> None:
        """Close the input."""
        print(f"SineWaveInput: Closed (generated {self.bytes_read} bytes)")

    def get_stats(self) -> dict:
        """Get input statistics."""
        return {
            'frequency': self.frequency,
            'bytes_generated': self.bytes_read,
            'phase': self.phase
        }
```

### Register the Custom Input

Modify python-dabmux to recognize your custom input URI:

Edit `src/dabmux/input/__init__.py`:

```python
from dabmux.input.base import InputBase
from dabmux.input.file import FileInput
from dabmux.input.udp import UDPInput
from dabmux.input.tcp import TCPInput
from custom_sine_input import SineWaveInput  # Add this


def create_input(uri: str) -> InputBase:
    """
    Create input from URI.

    Args:
        uri: Input URI (file://, udp://, tcp://, sine://)

    Returns:
        InputBase: Input instance
    """
    if uri.startswith('file://'):
        path = uri[7:]
        return FileInput(path)
    elif uri.startswith('udp://'):
        # Parse udp://host:port
        parts = uri[6:].split(':')
        host = parts[0]
        port = int(parts[1])
        return UDPInput(host, port)
    elif uri.startswith('tcp://'):
        # Parse tcp://host:port
        parts = uri[6:].split(':')
        host = parts[0]
        port = int(parts[1])
        return TCPInput(host, port)
    elif uri.startswith('sine://'):
        # Parse sine://frequency
        freq = float(uri[7:]) if len(uri) > 7 else 1000.0
        return SineWaveInput(frequency=freq)
    else:
        raise ValueError(f"Unknown input URI: {uri}")
```

## Step 3: Use Custom Input

### Configuration

Create `sine_test.yaml`:

```yaml
ensemble:
  id: '0xCE40'
  label:
    text: 'Sine Test'

subchannels:
  - uid: 'sine_audio'
    id: 0
    type: 'audio'
    bitrate: 128
    start_address: 0
    input: 'sine://440'  # 440 Hz sine wave (A4 note)

services:
  - uid: 'sine_service'
    id: '0x9001'
    label:
      text: 'Test Tone'

components:
  - uid: 'sine_comp'
    service_id: '0x9001'
    subchannel_id: 0
```

### Run Multiplexer

```bash
python -m dabmux.cli -c sine_test.yaml -o sine_test.eti -n 1000
```

The multiplexer will use your custom input to generate a test tone!

## Step 4: Add Buffer Management

Enhance with buffering:

```python
from collections import deque
from threading import Thread, Lock


class BufferedSineInput(SineWaveInput):
    """Sine wave input with buffering."""

    def __init__(self, frequency: float = 1000.0, buffer_size: int = 10):
        super().__init__(frequency)
        self.buffer_size = buffer_size
        self.buffer = deque(maxlen=buffer_size)
        self.lock = Lock()
        self.running = False
        self.thread = None

    def open(self) -> None:
        """Open input and start buffer thread."""
        super().open()
        self.running = True
        self.thread = Thread(target=self._fill_buffer)
        self.thread.start()

    def _fill_buffer(self) -> None:
        """Background thread to fill buffer."""
        while self.running:
            with self.lock:
                if len(self.buffer) < self.buffer_size:
                    # Generate frame worth of data
                    data = super().read(4096)
                    self.buffer.append(data)

    def read(self, size: int) -> bytes:
        """Read from buffer."""
        with self.lock:
            if not self.buffer:
                # Buffer empty - generate directly
                return super().read(size)

            # Get from buffer
            data = self.buffer.popleft()
            return data[:size] + b'\x00' * max(0, size - len(data))

    def close(self) -> None:
        """Stop buffer thread and close."""
        self.running = False
        if self.thread:
            self.thread.join()
        super().close()

    def get_stats(self) -> dict:
        """Get statistics including buffer status."""
        stats = super().get_stats()
        with self.lock:
            stats['buffer_fill'] = len(self.buffer)
            stats['buffer_size'] = self.buffer_size
        return stats
```

## Step 5: Real-World Example - HTTP Stream Input

Create an input that fetches audio from an HTTP stream:

```python
import requests
from dabmux.input.base import InputBase


class HTTPStreamInput(InputBase):
    """Input that reads from HTTP audio stream."""

    def __init__(self, url: str):
        self.url = url
        self.response = None
        self.iterator = None
        self.buffer = b''

    def open(self) -> None:
        """Connect to HTTP stream."""
        self.response = requests.get(self.url, stream=True)
        self.iterator = self.response.iter_content(chunk_size=4096)
        print(f"HTTPStreamInput: Connected to {self.url}")

    def read(self, size: int) -> bytes:
        """Read from HTTP stream."""
        # Fill buffer until we have enough data
        while len(self.buffer) < size:
            try:
                chunk = next(self.iterator)
                self.buffer += chunk
            except StopIteration:
                # Stream ended
                break

        # Return requested size
        data = self.buffer[:size]
        self.buffer = self.buffer[size:]

        # Pad if needed
        if len(data) < size:
            data += b'\x00' * (size - len(data))

        return data

    def close(self) -> None:
        """Close HTTP connection."""
        if self.response:
            self.response.close()
        print("HTTPStreamInput: Closed")
```

**Usage:**
```yaml
input: 'http://stream.example.com/audio.mp2'
```

## Step 6: Testing Custom Inputs

### Unit Tests

Create `test_custom_input.py`:

```python
import unittest
from custom_sine_input import SineWaveInput


class TestSineWaveInput(unittest.TestCase):
    def test_open_close(self):
        """Test opening and closing input."""
        inp = SineWaveInput(frequency=1000.0)
        inp.open()
        inp.close()

    def test_read_size(self):
        """Test reading returns correct size."""
        inp = SineWaveInput()
        inp.open()

        data = inp.read(4096)
        self.assertEqual(len(data), 4096)

        inp.close()

    def test_continuous_read(self):
        """Test reading multiple times."""
        inp = SineWaveInput()
        inp.open()

        for _ in range(10):
            data = inp.read(1000)
            self.assertEqual(len(data), 1000)

        inp.close()

    def test_statistics(self):
        """Test statistics reporting."""
        inp = SineWaveInput()
        inp.open()

        inp.read(4096)
        stats = inp.get_stats()

        self.assertIn('frequency', stats)
        self.assertIn('bytes_generated', stats)
        self.assertGreater(stats['bytes_generated'], 0)

        inp.close()


if __name__ == '__main__':
    unittest.main()
```

Run tests:
```bash
python test_custom_input.py
```

## Best Practices

### Always Return Exact Size

```python
def read(self, size: int) -> bytes:
    data = self._generate_data()

    # Ensure exact size
    if len(data) < size:
        data += b'\x00' * (size - len(data))  # Pad
    elif len(data) > size:
        data = data[:size]  # Truncate

    return data
```

### Handle Errors Gracefully

```python
def read(self, size: int) -> bytes:
    try:
        return self._read_internal(size)
    except Exception as e:
        print(f"Input error: {e}")
        # Return silence instead of crashing
        return b'\x00' * size
```

### Provide Meaningful Statistics

```python
def get_stats(self) -> dict:
    return {
        'input_type': 'custom',
        'bytes_read': self.total_bytes,
        'underruns': self.underrun_count,
        'last_error': self.last_error
    }
```

## Troubleshooting

### Input not recognized

**Error:**
```
ERROR: Unknown input URI: sine://440
```

**Solution:** Ensure you modified the input factory to register your custom input.

### Wrong data size returned

**Error:**
```
ERROR: Input returned wrong size
```

**Solution:** Always return exactly `size` bytes, pad with zeros if needed.

### Memory leak

**Problem:** Memory usage grows over time

**Solution:** Clean up resources in `close()`, avoid circular references.

## Next Steps

### Extend Further

Ideas for custom inputs:
- Database audio sources
- Algorithmically generated music
- Hardware audio interfaces
- Cloud storage (S3, etc.)
- Message queue inputs

### Contribute

Consider contributing your custom input to python-dabmux!

See [Contributing Guide](../development/contributing.md).

## Summary

You've learned to create custom inputs:

- ✅ Understanding InputBase interface
- ✅ Implementing required methods
- ✅ Buffer management
- ✅ Error handling
- ✅ Testing and debugging

Custom inputs extend python-dabmux for any audio source!

## Complete Example

```python
from dabmux.input.base import InputBase

class MyCustomInput(InputBase):
    def __init__(self, config: str):
        self.config = config

    def open(self) -> None:
        # Initialize your source
        pass

    def read(self, size: int) -> bytes:
        # Generate/fetch audio data
        data = self._get_audio()

        # Ensure exact size
        if len(data) < size:
            data += b'\x00' * (size - len(data))

        return data[:size]

    def close(self) -> None:
        # Clean up resources
        pass

    def get_stats(self) -> dict:
        return {
            'input_type': 'custom',
            'config': self.config
        }
```
