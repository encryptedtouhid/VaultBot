"""Tests for file-based logging setup."""

import json
import tempfile
from pathlib import Path

from vaultbot.utils.logging import get_logger, setup_logging


def test_file_logging_creates_log_files() -> None:
    """Log files are created in the specified directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        setup_logging(level="DEBUG", log_dir=log_dir, enable_file_logging=True)

        logger = get_logger("test.file_logging")
        logger.info("test_message", key="value")

        # Verify log files exist
        assert (log_dir / "vaultbot.log").exists()
        assert (log_dir / "vaultbot.error.log").exists()
        assert (log_dir / "audit.log").exists()


def test_app_log_contains_json_entries() -> None:
    """Application log entries are valid JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        setup_logging(level="DEBUG", log_dir=log_dir, enable_file_logging=True)

        logger = get_logger("test.json_format")
        logger.info("json_test", foo="bar", num=42)

        log_file = log_dir / "vaultbot.log"
        content = log_file.read_text().strip()
        assert content  # Not empty

        # Each line should be valid JSON
        for line in content.split("\n"):
            if line.strip():
                data = json.loads(line)
                assert "event" in data
                assert "level" in data
                assert "timestamp" in data


def test_error_log_only_contains_warnings_and_above() -> None:
    """Error log only captures WARNING level and above."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        setup_logging(level="DEBUG", log_dir=log_dir, enable_file_logging=True)

        logger = get_logger("test.error_filter")
        logger.debug("debug_msg")
        logger.info("info_msg")
        logger.warning("warning_msg")
        logger.error("error_msg")

        error_content = (log_dir / "vaultbot.error.log").read_text()
        assert "warning_msg" in error_content
        assert "error_msg" in error_content
        assert "info_msg" not in error_content
        assert "debug_msg" not in error_content


def test_log_includes_caller_info() -> None:
    """Log entries include filename, function, and line number."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        setup_logging(level="DEBUG", log_dir=log_dir, enable_file_logging=True)

        logger = get_logger("test.caller_info")
        logger.info("caller_test")

        content = (log_dir / "vaultbot.log").read_text()
        data = json.loads(content.strip().split("\n")[-1])
        assert "filename" in data
        assert "func_name" in data
        assert "lineno" in data


def test_log_file_permissions() -> None:
    """Log files have restricted permissions (owner-only read/write)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        setup_logging(level="INFO", log_dir=log_dir, enable_file_logging=True)

        logger = get_logger("test.permissions")
        logger.info("perm_test")

        import os
        import stat

        for name in ["vaultbot.log", "vaultbot.error.log", "audit.log"]:
            path = log_dir / name
            mode = os.stat(path).st_mode
            # Owner read+write only (0o600)
            assert mode & stat.S_IRWXG == 0, f"{name} is group-accessible"
            assert mode & stat.S_IRWXO == 0, f"{name} is world-accessible"


def test_disable_file_logging() -> None:
    """When file logging is disabled, no log directory is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "should_not_exist"
        setup_logging(level="INFO", log_dir=log_dir, enable_file_logging=False)

        logger = get_logger("test.no_files")
        logger.info("should_not_write_to_file")

        assert not log_dir.exists()


def test_audit_log_separate_from_app_log() -> None:
    """Audit events go to the dedicated audit.log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        setup_logging(level="INFO", log_dir=log_dir, enable_file_logging=True)

        import structlog

        audit_logger = structlog.get_logger("vaultbot.audit")
        audit_logger.info("auth.denied", user_id="attacker", platform="telegram")

        audit_content = (log_dir / "audit.log").read_text()
        assert "auth.denied" in audit_content
        assert "attacker" in audit_content
