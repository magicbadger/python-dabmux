# Installation

This guide covers installing python-dabmux on your system.

## Requirements

- **Python 3.11 or later**: python-dabmux uses modern Python features
- **pip**: Python package installer (usually comes with Python)
- **Virtual environment** (recommended): Keeps dependencies isolated

## Installation Methods

### Method 1: Install from PyPI (Recommended)

Once python-dabmux is published to PyPI, you can install it directly:

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install python-dabmux
pip install python-dabmux
```

### Method 2: Install from Source

For development or to use the latest code:

```bash
# Clone the repository
git clone https://github.com/python-dabmux/python-dabmux.git
cd python-dabmux

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

### Method 3: Install with Development Tools

If you plan to contribute or run tests:

```bash
# Clone and navigate to the repository
git clone https://github.com/python-dabmux/python-dabmux.git
cd python-dabmux

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

## Verify Installation

After installation, verify that python-dabmux is working:

```bash
# Check the CLI is accessible
python -m dabmux.cli --help
```

You should see the help message with available options:

```
usage: python -m dabmux.cli [-h] [-c CONFIG] [-o OUTPUT] [--edi EDI]
                            [--pft] [--continuous] [--version]

DAB/DAB+ Multiplexer

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to configuration file (YAML)
  -o OUTPUT, --output OUTPUT
                        Output file path (ETI format)
  --edi EDI             EDI output (udp://host:port or tcp://host:port)
  --pft                 Enable PFT (Protection, Fragmentation, Transport)
  --continuous          Run continuously (loop inputs)
  --version             Show version and exit
```

## Platform-Specific Notes

### Linux

python-dabmux works on all major Linux distributions:

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Fedora/RHEL
sudo dnf install python3.11 python3-pip

# Arch Linux
sudo pacman -S python python-pip
```

### macOS

Python 3.11+ is available via Homebrew:

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
```

### Windows

1. Download Python 3.11+ from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. Check "Add Python to PATH" during installation
4. Open Command Prompt or PowerShell and verify:

```powershell
python --version
```

## Dependencies

python-dabmux has minimal dependencies:

- **structlog**: Structured logging (automatically installed)

### Optional Dependencies

For documentation (developers only):

```bash
pip install -e ".[docs]"
```

This installs:
- mkdocs
- mkdocs-material
- mkdocs-mermaid2-plugin
- pymdown-extensions

## Troubleshooting Installation

### Python Version Issues

If you see "Python 3.11 or later is required":

```bash
# Check your Python version
python --version

# If you have multiple Python versions, use:
python3.11 -m venv venv
```

### Permission Errors

On Linux/macOS, if you see permission errors:

```bash
# Don't use sudo with pip in a virtual environment
# Instead, ensure you've activated the venv:
source venv/bin/activate
```

### Windows Path Issues

If `python` command is not found:

1. Reinstall Python with "Add to PATH" checked
2. Or manually add Python to your PATH
3. Or use the full path to python.exe

### pip Not Found

```bash
# Linux/macOS
python -m ensurepip --upgrade

# Or install pip separately
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

## Upgrading

To upgrade python-dabmux to the latest version:

```bash
# From PyPI
pip install --upgrade python-dabmux

# From source (in the repository directory)
git pull
pip install -e .
```

## Uninstallation

To remove python-dabmux:

```bash
pip uninstall python-dabmux
```

## Next Steps

Now that python-dabmux is installed, let's create your first multiplex:

[Your First Multiplex →](first-multiplex.md){ .md-button .md-button--primary }

## See Also

- [Basic Concepts](basic-concepts.md): Learn DAB terminology
- [CLI Reference](../user-guide/cli-reference.md): Complete CLI documentation
- [Configuration Reference](../user-guide/configuration/index.md): All configuration options
