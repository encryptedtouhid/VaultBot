"""Daemon mode for running VaultBot as a background service.

Provides PID file management, signal handling, and service lifecycle
for running VaultBot in the background.
"""

from __future__ import annotations

import os
import signal
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from vaultbot.config import CONFIG_DIR
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_PID_FILE = CONFIG_DIR / "vaultbot.pid"


@dataclass
class DaemonStatus:
    """Status of the VaultBot daemon."""

    running: bool
    pid: int | None = None
    uptime_seconds: float = 0.0
    started_at: str = ""


class DaemonManager:
    """Manages VaultBot daemon lifecycle.

    Parameters
    ----------
    pid_file:
        Path to the PID file.
    """

    def __init__(self, pid_file: Path = _PID_FILE) -> None:
        self._pid_file = pid_file
        self._start_time: datetime | None = None

    def is_running(self) -> bool:
        """Check if a daemon process is currently running."""
        pid = self._read_pid()
        if pid is None:
            return False

        try:
            os.kill(pid, 0)  # Signal 0 = check if process exists
            return True
        except (OSError, ProcessLookupError):
            # Stale PID file
            self._cleanup_pid()
            return False

    def get_status(self) -> DaemonStatus:
        """Get the current daemon status."""
        pid = self._read_pid()
        if pid is None:
            return DaemonStatus(running=False)

        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            self._cleanup_pid()
            return DaemonStatus(running=False)

        uptime = 0.0
        started = ""
        if self._start_time:
            uptime = (datetime.now(UTC) - self._start_time).total_seconds()
            started = self._start_time.isoformat()

        return DaemonStatus(
            running=True,
            pid=pid,
            uptime_seconds=uptime,
            started_at=started,
        )

    def write_pid(self) -> None:
        """Write the current process PID to the PID file."""
        self._pid_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._pid_file.write_text(str(os.getpid()))
        self._pid_file.chmod(0o600)
        self._start_time = datetime.now(UTC)
        logger.info("daemon_pid_written", pid=os.getpid(), pid_file=str(self._pid_file))

    def stop(self) -> bool:
        """Send SIGTERM to the running daemon process."""
        pid = self._read_pid()
        if pid is None:
            return False

        try:
            os.kill(pid, signal.SIGTERM)
            logger.info("daemon_stop_signal_sent", pid=pid)
            self._cleanup_pid()
            return True
        except (OSError, ProcessLookupError):
            self._cleanup_pid()
            return False

    def setup_signal_handlers(self, shutdown_callback: object = None) -> None:
        """Register signal handlers for graceful shutdown."""

        def handle_sigterm(signum: int, frame: object) -> None:
            logger.info("daemon_sigterm_received")
            self._cleanup_pid()
            if shutdown_callback and callable(shutdown_callback):
                shutdown_callback()
            sys.exit(0)

        def handle_sighup(signum: int, frame: object) -> None:
            logger.info("daemon_sighup_received_reload")

        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGHUP, handle_sighup)

    def _read_pid(self) -> int | None:
        """Read PID from the PID file."""
        if not self._pid_file.exists():
            return None
        try:
            return int(self._pid_file.read_text().strip())
        except (ValueError, OSError):
            return None

    def _cleanup_pid(self) -> None:
        """Remove the PID file."""
        try:
            self._pid_file.unlink(missing_ok=True)
        except OSError:
            pass
