# Contributing to VaultBot

Thank you for your interest in contributing to VaultBot!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/encryptedtouhid/VaultBot.git
cd VaultBot

# Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## Code Style

- **Linter**: Ruff (configured in `pyproject.toml`)
- **Formatter**: Ruff format
- **Type checker**: Mypy (strict mode)
- **Line length**: 100 characters
- **Python**: 3.11+

## Pull Request Process

1. One PR per issue/topic. Do not bundle unrelated changes.
2. All code must have unit tests. E2E tests for integration changes.
3. All tests must pass: `pytest --tb=short`
4. Linting must pass: `ruff check src/ tests/`
5. Format must pass: `ruff format --check src/ tests/`
6. Update documentation if adding new features.

## Security

- **Never** commit secrets, API keys, or credentials.
- All credentials go through the credential store.
- Report security vulnerabilities via [SECURITY.md](SECURITY.md).
- Plugin code must be Ed25519 signed.

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_auth.py -v

# Run with coverage
pytest --cov=src/vaultbot
```

## Architecture

See the project structure in `README.md`. Key patterns:

- **Protocol-based adapters**: Platforms and LLM providers use Protocol (structural subtyping)
- **Provider registry**: Media, search, and TTS use pluggable provider registries
- **Security-first**: All security mechanisms are on by default and cannot be disabled
