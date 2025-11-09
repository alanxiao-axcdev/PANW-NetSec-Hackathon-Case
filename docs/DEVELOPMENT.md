# Companion - Development Guide

**Contributing to and developing Companion**

---

## Overview

Companion is built with **modular design principles** where each module is independently testable and regeneratable from specifications. This guide helps you set up your development environment and understand the project structure.

**Technology Stack**:
- Python 3.11+ with type hints throughout
- Click (CLI framework)
- Transformers + PyTorch (AI models)
- Pydantic (data validation)
- pytest (testing)
- ruff (linting/formatting)

---

## Quick Start

### Prerequisites

**Required**:
- Python 3.11 or higher
- 8GB+ RAM (for running model locally)
- 5GB+ free disk space

**Recommended**:
- pyenv (Python version management)
- make (build automation)
- git (version control)

---

### Setup Development Environment

**1. Clone repository**:
```bash
git clone https://github.com/username/companion.git
cd companion
```

**2. Install dependencies**:
```bash
make install
```

This will:
- Create virtual environment (`.venv/`)
- Install all dependencies via `uv`
- Install development tools (pytest, ruff, pyright)
- Set up pre-commit hooks

**3. Activate virtual environment**:
```bash
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

**4. Verify installation**:
```bash
make check
```

This runs:
- Linting (ruff)
- Type checking (pyright)
- Import sorting
- Code formatting validation

**5. Run tests**:
```bash
make test
```

You should see all tests passing.

---

## Project Structure

```
PANW1/
├── companion/                    # Main package
│   ├── __init__.py              # Package initialization
│   ├── cli.py                   # CLI entry point (400 lines)
│   ├── models.py                # Data models (150 lines)
│   ├── config.py                # Configuration (80 lines)
│   ├── storage.py               # File operations (120 lines)
│   ├── journal.py               # Entry CRUD (180 lines)
│   ├── ai_engine.py             # AI coordination (200 lines)
│   ├── analyzer.py              # Sentiment/themes (220 lines)
│   ├── prompter.py              # Prompt generation (190 lines)
│   ├── summarizer.py            # Summaries (240 lines)
│   ├── input_handler.py         # Input monitoring (160 lines)
│   │
│   ├── security/                # Security modules (670 lines)
│   │   ├── encryption.py        # AES-256-GCM encryption
│   │   ├── sandboxing.py        # Process isolation
│   │   ├── audit.py             # Security logging
│   │   └── pii_detector.py      # PII detection baseline
│   │
│   ├── monitoring/              # Monitoring (570 lines)
│   │   ├── metrics.py           # Performance metrics
│   │   ├── health.py            # Health checks
│   │   ├── telemetry.py         # Usage analytics
│   │   └── dashboard.py         # Terminal dashboard
│   │
│   ├── inference/               # Optimization (720 lines)
│   │   ├── optimizer.py         # Model quantization
│   │   ├── batcher.py           # Batch inference
│   │   ├── cache.py             # Semantic caching
│   │   └── benchmark.py         # Performance benchmarking
│   │
│   ├── security_research/       # Research (1200 lines)
│   │   ├── prompt_injection_detector.py
│   │   ├── pii_sanitizer.py
│   │   ├── data_poisoning_detector.py
│   │   └── adversarial_tester.py
│   │
│   ├── ai_backend/              # AI providers (640 lines)
│   │   ├── base.py              # Abstract interface
│   │   ├── qwen_provider.py     # Qwen implementation
│   │   ├── ollama_provider.py   # Ollama integration
│   │   ├── openai_provider.py   # OpenAI API
│   │   └── mock_provider.py     # Testing mock
│   │
│   └── utils/                   # Utilities (250 lines)
│       ├── retry.py             # Retry logic
│       ├── circuit_breaker.py   # Circuit breaker
│       └── error_classifier.py  # Error classification
│
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests (60%)
│   ├── integration/             # Integration tests (30%)
│   ├── security/                # Security tests
│   ├── performance/             # Performance regression
│   └── fixtures/                # Test data
│
├── benchmarks/                  # Performance benchmarks
│   ├── inference_benchmark.py
│   ├── security_benchmark.py
│   └── end_to_end_benchmark.py
│
├── docs/                        # Documentation
│   ├── DESIGN.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPMENT.md          # This file
│   ├── SECURITY.md
│   ├── THREAT_MODEL.md
│   ├── PERFORMANCE.md
│   ├── RESEARCH_FINDINGS.md
│   └── PRESENTATION.md
│
├── pyproject.toml              # Package configuration
├── Makefile                    # Common commands
├── README.md                   # Project overview
└── LICENSE                     # MIT License
```

---

## Development Workflow

### Making Changes

**1. Create feature branch**:
```bash
git checkout -b feature/your-feature-name
```

**2. Make changes**:
```bash
# Edit code
vim companion/module.py

# Run checks continuously
make check

# Run specific tests
pytest tests/unit/test_module.py -v
```

**3. Run full test suite**:
```bash
make test
```

**4. Commit changes**:
```bash
git add .
git commit -m "feat: add new feature"
```

**5. Push and create PR**:
```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

---

### Running Tests

**All tests**:
```bash
make test
```

**By category**:
```bash
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-security      # Security tests only
make test-performance   # Performance regression tests
```

**Specific test**:
```bash
# Single test file
pytest tests/unit/test_journal.py -v

# Single test function
pytest tests/unit/test_journal.py::test_save_entry -v

# With coverage
pytest tests/unit/test_journal.py --cov=companion.journal --cov-report=html
```

**Watch mode** (re-run on file changes):
```bash
pytest-watch
```

---

### Code Quality

**Run all checks**:
```bash
make check
```

This runs:
- `ruff check` - Linting
- `ruff format --check` - Format checking
- `pyright` - Type checking

**Auto-fix issues**:
```bash
make format  # Auto-format code
make fix     # Auto-fix linting issues
```

**Individual checks**:
```bash
ruff check .               # Lint
ruff format .              # Format
pyright                    # Type check
```

---

### Running Locally

**Development mode**:
```bash
# From package directory
python -m companion.cli

# Or via entry point
companion

# With debug logging
companion --debug
```

**Testing specific features**:
```bash
# Test journaling flow
companion

# Test summary generation
companion summary

# Test metrics dashboard
companion metrics

# Test health checks
companion health
```

---

## Module Development

### Creating a New Module

**1. Define interface** (in DESIGN.md):
```python
# companion/my_module.py

"""
Purpose: Brief description of what this module does
Dependencies: List of other modules this depends on
Exports: Public functions and classes
"""

def public_function(arg: str) -> Result:
    """
    Public function description.

    Args:
        arg: Description

    Returns:
        Description

    Raises:
        ValueError: When...
    """
    pass
```

**2. Implement module**:
```python
# companion/my_module.py

from companion.models import MyModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def public_function(arg: str) -> Result:
    """Implementation"""
    logger.info(f"Processing {arg}")

    # Validate inputs
    if not arg:
        raise ValueError("arg cannot be empty")

    # Do work
    result = _private_helper(arg)

    return result

def _private_helper(arg: str) -> str:
    """Private helper (underscore prefix)"""
    return arg.upper()
```

**3. Write tests**:
```python
# tests/unit/test_my_module.py

import pytest
from companion.my_module import public_function

def test_public_function_success():
    """Test successful case"""
    result = public_function("test")
    assert result == "TEST"

def test_public_function_empty_input():
    """Test error case"""
    with pytest.raises(ValueError, match="cannot be empty"):
        public_function("")

def test_public_function_with_mock():
    """Test with mocked dependencies"""
    # Use fixtures or mocks as needed
    pass
```

**4. Run tests**:
```bash
pytest tests/unit/test_my_module.py -v
```

**5. Update documentation**:
- Add module description to DESIGN.md
- Update module count in README.md
- Add usage examples if user-facing

---

### Modifying Existing Module

**1. Read module spec** (in DESIGN.md)

**2. Maintain interface contract**:
```python
# DON'T change function signatures (breaks other modules)
# BAD:
def analyze_sentiment(text: str, model: str) -> Sentiment:  # Added parameter!

# GOOD:
def analyze_sentiment(text: str) -> Sentiment:  # Interface unchanged
    # Implementation can change freely
    model = "new-improved-model"  # Internal change OK
```

**3. Run affected tests**:
```bash
# Test module itself
pytest tests/unit/test_module.py -v

# Test integration (modules that depend on this one)
pytest tests/integration/ -v
```

**4. Update documentation** if behavior changes visibly

---

## Testing Guidelines

### Test Organization

**Unit tests** (tests/unit/):
- One test file per module
- Test individual functions in isolation
- Mock external dependencies
- Fast (< 1s per test)

**Integration tests** (tests/integration/):
- Test multiple modules working together
- Minimal mocking (real dependencies)
- Test complete workflows
- Moderate speed (< 10s per test)

**Security tests** (tests/security/):
- Test security mechanisms
- Adversarial test cases
- Injection attempts, PII detection, etc.
- Can be slower (real AI models)

**Performance tests** (tests/performance/):
- Regression tests for performance
- Latency, memory, throughput
- Run less frequently (before releases)

---

### Testing Best Practices

**1. Use descriptive test names**:
```python
# GOOD
def test_save_entry_with_valid_data_succeeds():
    pass

def test_save_entry_with_empty_content_raises_validation_error():
    pass

# BAD
def test_save_entry_1():
    pass

def test_save_entry_error():
    pass
```

**2. Follow AAA pattern** (Arrange, Act, Assert):
```python
def test_analyze_sentiment_positive():
    # Arrange
    entry = JournalEntry(content="I'm so happy today!")

    # Act
    sentiment = analyze_sentiment(entry.content)

    # Assert
    assert sentiment.label == "positive"
    assert sentiment.confidence > 0.7
```

**3. Use fixtures for common setup**:
```python
# tests/fixtures/entries.py
@pytest.fixture
def sample_entry():
    return JournalEntry(
        content="Test entry content",
        timestamp=datetime.now()
    )

# tests/unit/test_analyzer.py
def test_analyze_sentiment(sample_entry):
    sentiment = analyze_sentiment(sample_entry.content)
    assert sentiment is not None
```

**4. Test edge cases**:
```python
def test_save_entry_edge_cases():
    # Empty content
    with pytest.raises(ValueError):
        save_entry(JournalEntry(content=""))

    # Very long content
    long_content = "a" * 100_000
    entry = save_entry(JournalEntry(content=long_content))
    assert entry.id is not None

    # Special characters
    special_content = "Hello 👋 émojis & spëcial çharacters"
    entry = save_entry(JournalEntry(content=special_content))
    assert entry.content == special_content
```

**5. Mock external dependencies**:
```python
from unittest.mock import Mock, patch

def test_generate_summary_with_mocked_ai():
    with patch('companion.ai_engine.generate_text') as mock_generate:
        # Control AI output for predictable testing
        mock_generate.return_value = "This is a test summary"

        summary = generate_summary(entries)

        assert "test summary" in summary.text
        mock_generate.assert_called_once()
```

---

## Makefile Commands

Common development tasks are automated in the Makefile:

```bash
make install          # Install dependencies
make check            # Run all code quality checks
make test             # Run all tests
make test-unit        # Run unit tests only
make test-integration # Run integration tests only
make test-security    # Run security tests only
make test-performance # Run performance tests
make coverage         # Generate coverage report
make format           # Auto-format code
make fix              # Auto-fix linting issues
make clean            # Remove generated files
make benchmark        # Run performance benchmarks
make docs             # Build documentation (if applicable)
```

---

## Code Style Guidelines

### General Principles

1. **Type hints everywhere**:
```python
# GOOD
def save_entry(entry: JournalEntry) -> str:
    return entry.id

# BAD
def save_entry(entry):
    return entry.id
```

2. **Docstrings for public functions**:
```python
def analyze_sentiment(text: str) -> Sentiment:
    """
    Analyze sentiment of journal entry text.

    Uses Qwen2.5-1.5B model to classify sentiment as positive,
    neutral, or negative with confidence score.

    Args:
        text: Journal entry content to analyze

    Returns:
        Sentiment with label and confidence (0-1)

    Raises:
        ValueError: If text is empty
        AIError: If model inference fails

    Example:
        >>> sentiment = analyze_sentiment("I'm happy today!")
        >>> sentiment.label
        'positive'
        >>> sentiment.confidence
        0.87
    """
```

3. **Explicit over implicit**:
```python
# GOOD
def get_entries(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100
) -> list[JournalEntry]:
    pass

# BAD (unclear what kwargs might be)
def get_entries(**kwargs) -> list[JournalEntry]:
    pass
```

4. **Error handling with context**:
```python
# GOOD
try:
    entry = decrypt_entry(encrypted_data, passphrase)
except DecryptionError as e:
    logger.error(f"Failed to decrypt entry {entry_id}: {e}")
    raise

# BAD (swallows error)
try:
    entry = decrypt_entry(encrypted_data, passphrase)
except:
    pass
```

5. **Logging appropriately**:
```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: Detailed diagnostic information
logger.debug(f"Processing entry with {len(text)} characters")

# INFO: General informational messages
logger.info(f"Entry {entry_id} saved successfully")

# WARNING: Something unexpected but handled
logger.warning(f"PII detected in entry {entry_id}")

# ERROR: Operation failed
logger.error(f"Failed to analyze entry {entry_id}: {e}")

# CRITICAL: System cannot continue
logger.critical("AI model failed to load, shutting down")
```

---

## Dependencies

### Adding Dependencies

**1. Add to pyproject.toml**:
```bash
# From companion directory
cd PANW1

# Add runtime dependency
uv add package-name

# Add dev dependency
uv add --dev package-name
```

This updates both `pyproject.toml` and `uv.lock`.

**2. Document why**:
```toml
# pyproject.toml
[project.dependencies]
requests = ">=2.31.0"  # Used in ollama_provider for REST API
```

**3. Update lockfile**:
```bash
make lock-upgrade
```

---

### Dependency Guidelines

**Prefer**:
- Well-maintained packages (recent commits)
- Permissive licenses (MIT, Apache 2.0)
- Minimal transitive dependencies
- Good documentation

**Avoid**:
- Unmaintained packages (>1 year no updates)
- Packages with known vulnerabilities
- Packages with GPL license (incompatible with MIT)
- Reinventing wheels (use stdlib when possible)

---

## Debugging

### Debug Mode

```bash
# Enable debug logging
companion --debug

# Save debug output
companion --debug > debug.log 2>&1
```

### Python Debugger

```python
# Add breakpoint in code
def problematic_function():
    import pdb; pdb.set_trace()  # Debugger stops here
    # ... rest of code
```

**Or use built-in breakpoint** (Python 3.7+):
```python
def problematic_function():
    breakpoint()  # Same as pdb.set_trace()
    # ... rest of code
```

### Common Debug Scenarios

**AI model not loading**:
```bash
# Check if model exists
ls ~/.companion/models/

# Try downloading again
companion --download-model

# Check disk space
df -h

# Check RAM
free -h
```

**Decryption failures**:
```python
# Enable encryption debug logging
import logging
logging.getLogger('companion.security.encryption').setLevel(logging.DEBUG)
```

**Performance issues**:
```bash
# Run with profiling
python -m cProfile -o profile.stats -m companion.cli

# Analyze profile
python -m pstats profile.stats
```

---

## Contributing Guidelines

### Before Contributing

1. **Read existing code** to understand patterns
2. **Check issues** to see if already being worked on
3. **Open discussion** for large changes
4. **Start small** with bug fixes or documentation

### Pull Request Process

**1. Create issue** (if doesn't exist)
- Describe problem/feature
- Propose solution
- Get feedback before coding

**2. Fork and branch**:
```bash
git checkout -b fix/issue-123-description
```

**3. Make changes**:
- Follow code style guidelines
- Add tests for new functionality
- Update documentation

**4. Run checks**:
```bash
make check
make test
```

**5. Commit with clear messages**:
```bash
git commit -m "fix: resolve decryption issue with special characters

- Add UTF-8 encoding handling in encryption module
- Add test cases for special characters
- Update documentation

Fixes #123"
```

**6. Push and create PR**:
```bash
git push origin fix/issue-123-description
```

**7. Address review feedback**
- Make requested changes
- Push updates to same branch
- PR automatically updates

---

### Commit Message Format

Follow conventional commits:

```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build/tooling changes

**Examples**:
```
feat: add prompt injection detection

Implement pattern-based detection with 93.6% accuracy.
Uses regex patterns + semantic analysis.

Closes #45

fix: handle UTF-8 in encryption

Previous implementation failed with emoji.
Add explicit UTF-8 encoding in encrypt/decrypt.

Fixes #123

docs: update installation instructions

Add pipx as recommended method.
Clarify system requirements.
```

---

## Security Considerations

### Security Review Checklist

Before committing security-related changes:

- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user data
- [ ] Encryption for sensitive data
- [ ] Audit logging for security events
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies have no known vulnerabilities
- [ ] Security tests pass

### Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

**Instead**:
1. Email: security@companion-journal.com
2. Provide: Description, steps to reproduce, impact
3. Wait for response (within 48 hours)
4. Coordinated disclosure after fix

---

## Release Process

### Versioning

We follow **Semantic Versioning** (semver):
- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes

### Creating a Release

**1. Update version**:
```toml
# pyproject.toml
[project]
version = "0.2.0"
```

**2. Update CHANGELOG.md**:
```markdown
## [0.2.0] - 2025-01-15

### Added
- Prompt injection detection with 93.6% accuracy
- PII sanitization with 91.9% F1 score
- Performance metrics dashboard

### Fixed
- Decryption issue with special characters
- Memory leak in cache system

### Changed
- Improved summary generation quality
```

**3. Run full test suite**:
```bash
make test
make benchmark
```

**4. Build package**:
```bash
python -m build
```

**5. Test installation**:
```bash
pip install dist/companion_journal-0.2.0-py3-none-any.whl
companion --version
```

**6. Tag release**:
```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

**7. Publish to PyPI**:
```bash
twine upload dist/*
```

---

## Resources

### Documentation

- **[DESIGN.md](DESIGN.md)** - Architecture and module specifications
- **[USER_GUIDE.md](USER_GUIDE.md)** - User-facing documentation
- **[SECURITY.md](SECURITY.md)** - Security architecture
- **[THREAT_MODEL.md](THREAT_MODEL.md)** - Threat analysis
- **[PERFORMANCE.md](PERFORMANCE.md)** - Performance benchmarks
- **[RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md)** - AI security research

### External Resources

**Python**:
- Python Type Hints: https://docs.python.org/3/library/typing.html
- Python Testing: https://docs.pytest.org/

**AI/ML**:
- Hugging Face Transformers: https://huggingface.co/docs/transformers
- PyTorch: https://pytorch.org/docs/

**Security**:
- OWASP LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Cryptography: https://cryptography.io/

**Tools**:
- ruff: https://docs.astral.sh/ruff/
- pytest: https://docs.pytest.org/
- Click: https://click.palletsprojects.com/

---

## Getting Help

### Stuck? Try This

**1. Check documentation** (you're reading it!)

**2. Search existing issues**:
```bash
# GitHub search
https://github.com/username/companion/issues
```

**3. Enable debug logging**:
```bash
companion --debug
```

**4. Run health check**:
```bash
companion health
```

**5. Ask for help**:
- GitHub Discussions: For questions
- GitHub Issues: For bugs
- Email: dev@companion-journal.com

### Creating Good Issues

**Include**:
- Clear title
- Steps to reproduce
- Expected vs actual behavior
- Debug logs (sanitized)
- System info (OS, Python version, RAM)
- Screenshots if applicable

**Template**:
```markdown
**Description**
Brief description of the problem

**Steps to Reproduce**
1. Run `companion`
2. Type this...
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Debug Logs**
```
[paste relevant logs]
```

**Environment**
- OS: Ubuntu 22.04
- Python: 3.11.4
- RAM: 8GB
- Companion version: 0.1.0
```

---

## Welcome!

Thank you for contributing to Companion!

**Remember**:
- Start small (bug fixes, docs)
- Ask questions early
- Follow existing patterns
- Write tests
- Be patient with reviews

We're here to help. Happy coding! 

---

**Document Version**: 1.0
**Last Updated**: 2025-01-08
**Maintainer**: Companion Development Team
