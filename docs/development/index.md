# Development Guide

Contributing to python-dabmux.

## Overview

python-dabmux is an open-source project welcoming contributions of all kinds:
- Bug fixes and features
- Documentation improvements
- Test coverage
- Performance optimizations
- Example configurations

## Getting Started

### Development Setup

```bash
# Clone repository
git clone https://github.com/python-dabmux/python-dabmux.git
cd python-dabmux

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev,docs]"

# Run tests
pytest

# Check types
mypy src/dabmux

# Build documentation
mkdocs serve
```

### Repository Structure

```
python-dabmux/
├── src/
│   └── dabmux/          # Source code
├── tests/
│   └── unit/            # Unit tests
├── docs/                # Documentation (MkDocs)
├── examples/            # Example configurations
├── pyproject.toml       # Project configuration
├── mkdocs.yml           # Documentation configuration
└── README.md
```

## Contributing

See [Contributing Guide](contributing.md) for detailed instructions on:
- Code style and standards
- Submitting pull requests
- Reporting issues
- Development workflow

## Testing

See [Testing Guide](testing.md) for:
- Running tests
- Writing tests
- Coverage requirements
- Integration testing

## Development Phases

python-dabmux was developed in phases. See [Phase Summaries](phase-summaries.md) for the development history and design decisions.

## Roadmap

See [Roadmap](roadmap.md) for planned features and improvements.

## Key Technologies

- **Python 3.11+**: Modern Python features
- **structlog**: Structured logging
- **pytest**: Testing framework
- **mypy**: Static type checking
- **MkDocs**: Documentation

## Code Quality

### Requirements

- ✅ Type annotations on all functions
- ✅ Docstrings for public APIs
- ✅ Unit tests for new features
- ✅ No mypy errors
- ✅ All tests passing

### Tools

```bash
# Type checking
mypy src/dabmux

# Run tests with coverage
pytest --cov=dabmux --cov-report=term-missing

# Format check (if using black)
black --check src/

# Lint (if using ruff)
ruff check src/
```

## Communication

- **GitHub Issues**: Bug reports and feature requests
- **Pull Requests**: Code contributions
- **Discussions**: Questions and ideas

## License

python-dabmux is open source under the MIT License.

## Related Projects

- **[ODR-DabMux](https://github.com/Opendigitalradio/ODR-DabMux)** - C++ reference implementation
- **[ODR-DabMod](https://github.com/Opendigitalradio/ODR-DabMod)** - DAB modulator
- **[ODR-AudioEnc](https://github.com/Opendigitalradio/ODR-AudioEnc)** - Audio encoder

## Resources

- [ETSI Standards](../standards/index.md) - DAB specifications
- [Architecture](../architecture/index.md) - System design
- [API Reference](../api-reference/index.md) - Complete API

## Quick Links

- [Report a Bug](https://github.com/python-dabmux/python-dabmux/issues/new?labels=bug)
- [Request a Feature](https://github.com/python-dabmux/python-dabmux/issues/new?labels=enhancement)
- [View Open Issues](https://github.com/python-dabmux/python-dabmux/issues)
- [Contributor Guidelines](contributing.md)
