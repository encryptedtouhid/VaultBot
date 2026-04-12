"""Unit tests for production logging."""

from __future__ import annotations

import tempfile
from pathlib import Path

from vaultbot.utils.log_redaction import redact_dict, redact_secrets
from vaultbot.utils.log_rotation import LogRotator, RotationConfig


class TestLogRotator:
    def test_should_rotate_nonexistent(self) -> None:
        rotator = LogRotator()
        assert rotator.should_rotate("/nonexistent/file.log") is False

    def test_should_rotate_small_file(self) -> None:
        rotator = LogRotator(RotationConfig(max_bytes=1000))
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            f.write(b"small")
            f.flush()
            assert rotator.should_rotate(f.name) is False
            Path(f.name).unlink()

    def test_should_rotate_large_file(self) -> None:
        rotator = LogRotator(RotationConfig(max_bytes=10))
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            f.write(b"x" * 100)
            f.flush()
            assert rotator.should_rotate(f.name) is True
            Path(f.name).unlink()

    def test_rotate(self) -> None:
        rotator = LogRotator()
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            f.write(b"log data")
            f.flush()
            name = f.name
        assert rotator.rotate(name) is True
        assert rotator.rotation_count == 1
        assert Path(f"{name}.1").exists()
        Path(f"{name}.1").unlink()

    def test_rotate_nonexistent(self) -> None:
        rotator = LogRotator()
        assert rotator.rotate("/nonexistent/file.log") is False


class TestRedaction:
    def test_redact_api_key(self) -> None:
        text = "Using key sk-abcdefghijklmnopqrstuvwxyz"
        result = redact_secrets(text)
        assert "sk-abcdef" not in result
        assert "sk-****" in result

    def test_redact_bearer_token(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9"
        result = redact_secrets(text)
        assert "eyJ" not in result
        assert "****" in result

    def test_redact_password(self) -> None:
        text = "password = secret123"
        result = redact_secrets(text)
        assert "secret123" not in result

    def test_no_false_positive(self) -> None:
        text = "This is a normal log message"
        assert redact_secrets(text) == text

    def test_redact_dict(self) -> None:
        data = {"username": "admin", "password": "secret", "api_key": "sk-xxx"}
        result = redact_dict(data)
        assert result["username"] == "admin"
        assert result["password"] == "****"
        assert result["api_key"] == "****"

    def test_redact_nested_dict(self) -> None:
        data = {"config": {"db_password": "secret", "host": "localhost"}}
        result = redact_dict(data)
        assert result["config"]["db_password"] == "****"
        assert result["config"]["host"] == "localhost"
