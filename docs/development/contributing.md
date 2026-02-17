# Contributing to python-dabmux

Thank you for your interest in contributing to python-dabmux!

## Ways to Contribute

- 🐛 Report bugs
- ✨ Suggest features
- 📝 Improve documentation
- 🧪 Add tests
- 💻 Submit code changes
- 🎓 Share examples and tutorials

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/python-dabmux.git
cd python-dabmux
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev,docs]"
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dabmux --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_eti.py

# Run specific test
pytest tests/unit/test_eti.py::test_eti_frame_creation -v
```

### Type Checking

```bash
# Check types
mypy src/dabmux

# Check specific module
mypy src/dabmux/core/eti.py
```

### Documentation

```bash
# Build and serve documentation locally
mkdocs serve

# View at http://127.0.0.1:8000

# Build documentation
mkdocs build
```

## Code Style

### Python Style

- **PEP 8** compliance
- **Type annotations** on all functions
- **Docstrings** for public APIs (Google style)
- **Max line length**: 100 characters

### Example

```python
from typing import Optional

def generate_frame(
    frame_number: int,
    enable_tist: bool = False
) -> Optional[EtiFrame]:
    """
    Generate an ETI frame.

    Args:
        frame_number: Frame sequence number (0-255)
        enable_tist: Include timestamp field

    Returns:
        ETI frame, or None if generation fails

    Raises:
        ValueError: If frame_number is invalid
    """
    if frame_number < 0 or frame_number > 255:
        raise ValueError("Frame number must be 0-255")

    # Implementation
    ...
```

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Short description (one line).

    Longer description if needed. Can span multiple
    lines and paragraphs.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When parameter is invalid
        RuntimeError: When operation fails

    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        True
    """
```

## Writing Tests

### Test Structure

```python
import pytest
from dabmux.core.eti import EtiFrame, TransmissionMode

def test_frame_creation():
    """Test ETI frame creation."""
    frame = EtiFrame.create_empty(mode=TransmissionMode.MODE_I)
    assert frame is not None
    assert frame.fc.mid == 1

def test_frame_serialization():
    """Test frame serialization."""
    frame = EtiFrame.create_empty(mode=TransmissionMode.MODE_I)
    data = frame.pack()
    assert len(data) == 6144

@pytest.mark.parametrize("mode,expected_size", [
    (TransmissionMode.MODE_I, 6144),
    (TransmissionMode.MODE_II, 3072),
])
def test_frame_sizes(mode, expected_size):
    """Test frame sizes for different modes."""
    frame = EtiFrame.create_empty(mode=mode)
    assert len(frame.pack()) == expected_size
```

### Test Coverage

- Aim for **>80% coverage** for new code
- Core modules should have **>90% coverage**
- Test both success and error cases

## Submitting Changes

### 1. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add feature: description of changes"
```

**Commit message format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Add or modify tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

**Example:**
```
feat: Add support for Mode IV transmission

Implement Mode IV frame generation with correct
timing and FIC size. Includes tests and documentation.

Closes #42
```

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Create Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select your branch
4. Fill in PR template:
   - Description of changes
   - Related issues
   - Testing done
   - Checklist

### Pull Request Checklist

- [ ] Tests pass (`pytest`)
- [ ] Type checking passes (`mypy src/dabmux`)
- [ ] Documentation updated (if needed)
- [ ] New tests added (if applicable)
- [ ] Commit messages are clear
- [ ] No merge conflicts

## Reporting Issues

### Bug Reports

Include:
1. **Description**: What happened vs what you expected
2. **Steps to reproduce**: Minimal example
3. **Environment**: Python version, OS, python-dabmux version
4. **Logs**: Error messages and tracebacks

**Template:**
```markdown
**Description**
Brief description of the bug

**To Reproduce**
1. Step 1
2. Step 2
3. See error

**Expected Behavior**
What should happen

**Environment**
- Python version: 3.11.5
- OS: Ubuntu 22.04
- python-dabmux version: 0.6.0

**Additional Context**
Error logs, configuration files, etc.
```

### Feature Requests

Include:
1. **Use case**: Why is this needed?
2. **Proposed solution**: How should it work?
3. **Alternatives**: Other approaches considered

## Review Process

1. **Automated checks**: CI runs tests and type checking
2. **Code review**: Maintainers review code
3. **Feedback**: Address review comments
4. **Approval**: Maintainer approves PR
5. **Merge**: PR merged to main branch

## Development Tips

### Testing Locally

```bash
# Test specific component
pytest tests/unit/core/ -v

# Test with verbose output
pytest -vv

# Stop on first failure
pytest -x

# Run only failed tests
pytest --lf
```

### Debugging

```python
# Add logging
import structlog
logger = structlog.get_logger(__name__)

logger.debug("Variable value", value=x)
logger.info("Processing frame", frame_num=frame.fc.fct)
logger.warning("Unusual condition", condition=state)
logger.error("Operation failed", error=e)
```

### Performance Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
mux.generate_frame()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Questions?

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Specific bugs or features
- **Documentation**: Check [User Guide](../user-guide/index.md) and [API Reference](../api-reference/index.md)

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build great software together.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to python-dabmux! 🎉
