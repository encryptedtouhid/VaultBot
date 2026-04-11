"""Unit tests for daemon manager."""

from __future__ import annotations

import os
from pathlib import Path

from vaultbot.daemon import DaemonManager


class TestDaemonManager:
    def _make_manager(self, tmp_path: Path) -> DaemonManager:
        return DaemonManager(pid_file=tmp_path / "test.pid")

    def test_not_running_initially(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        assert mgr.is_running() is False

    def test_get_status_not_running(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        status = mgr.get_status()
        assert status.running is False
        assert status.pid is None

    def test_write_pid(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        mgr.write_pid()
        pid_file = tmp_path / "test.pid"
        assert pid_file.exists()
        assert int(pid_file.read_text().strip()) == os.getpid()

    def test_is_running_after_write(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        mgr.write_pid()
        # Current process is running, so should be True
        assert mgr.is_running() is True

    def test_get_status_running(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        mgr.write_pid()
        status = mgr.get_status()
        assert status.running is True
        assert status.pid == os.getpid()

    def test_stale_pid_cleaned(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        # Write a PID that doesn't exist
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("999999999")
        assert mgr.is_running() is False
        assert not pid_file.exists()  # Cleaned up

    def test_stop_current_process(self, tmp_path: Path) -> None:
        # We can't actually stop ourselves, but we can test the logic
        mgr = self._make_manager(tmp_path)
        # No PID file, stop returns False
        assert mgr.stop() is False

    def test_stop_stale_pid(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("999999999")
        assert mgr.stop() is False

    def test_cleanup_pid(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        mgr.write_pid()
        mgr._cleanup_pid()
        assert not (tmp_path / "test.pid").exists()

    def test_read_pid_invalid_content(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("not_a_number")
        assert mgr._read_pid() is None

    def test_read_pid_missing_file(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        assert mgr._read_pid() is None

    def test_pid_file_permissions(self, tmp_path: Path) -> None:
        mgr = self._make_manager(tmp_path)
        mgr.write_pid()
        pid_file = tmp_path / "test.pid"
        # Check permissions (0o600 = owner read/write only)
        stat = pid_file.stat()
        assert stat.st_mode & 0o777 == 0o600
