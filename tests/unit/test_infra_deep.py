"""Unit tests for deep infra."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest

from vaultbot.infra.archive import ArchiveSecurityError, extract_zip
from vaultbot.infra.diagnostics import DiagnosticCollector


class TestArchiveExtraction:
    def test_extract_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Create a test zip
            zip_path = Path(tmp) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("file1.txt", "hello")
                zf.writestr("dir/file2.txt", "world")

            target = Path(tmp) / "output"
            result = extract_zip(str(zip_path), str(target))
            assert result.extracted_files == 2
            assert (target / "file1.txt").read_text() == "hello"

    def test_extract_zip_too_large(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "big.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("big.txt", "x" * 1000)

            target = Path(tmp) / "output"
            with pytest.raises(ArchiveSecurityError, match="too large"):
                extract_zip(str(zip_path), str(target), max_size=100)


class TestDiagnosticCollector:
    def test_capture(self) -> None:
        collector = DiagnosticCollector()
        snap = collector.capture(active_sessions=5)
        assert snap.active_sessions == 5
        assert snap.python_version != ""
        assert collector.snapshot_count == 1

    def test_uptime(self) -> None:
        collector = DiagnosticCollector()
        assert collector.uptime_seconds >= 0

    def test_error_tracking(self) -> None:
        collector = DiagnosticCollector()
        collector.record_error()
        collector.record_error()
        snap = collector.capture()
        assert snap.errors_last_hour == 2

    def test_recent_snapshots(self) -> None:
        collector = DiagnosticCollector()
        for _ in range(5):
            collector.capture()
        recent = collector.get_recent(limit=3)
        assert len(recent) == 3
