"""Unit tests for setup wizard and doctor."""

from __future__ import annotations

from pathlib import Path

import pytest

from vaultbot.setup import CheckStatus, DiagnosticReport, Doctor, SetupWizard


class TestDoctor:
    def test_check_python_version(self) -> None:
        doctor = Doctor()
        result = doctor.check_python_version()
        # We're running on 3.11+, should pass
        assert result.status == CheckStatus.PASS

    def test_check_config_dir(self) -> None:
        doctor = Doctor()
        result = doctor.check_config_dir()
        # May or may not exist
        assert result.status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_check_config_file(self) -> None:
        doctor = Doctor()
        result = doctor.check_config_file()
        assert result.status in (CheckStatus.PASS, CheckStatus.WARN)

    def test_check_dependencies(self) -> None:
        doctor = Doctor()
        result = doctor.check_dependencies()
        assert result.status == CheckStatus.PASS  # We have all deps

    def test_run_all(self) -> None:
        doctor = Doctor()
        report = doctor.run_all()
        assert len(report.checks) >= 4
        assert report.pass_count >= 2  # At least Python + deps


class TestDiagnosticReport:
    def test_empty_passes(self) -> None:
        report = DiagnosticReport()
        assert report.passed is True

    def test_with_failure(self) -> None:
        from vaultbot.setup import DiagnosticCheck
        report = DiagnosticReport(checks=[
            DiagnosticCheck(name="test", status=CheckStatus.FAIL, message="bad"),
        ])
        assert report.passed is False
        assert report.fail_count == 1

    def test_skip_still_passes(self) -> None:
        from vaultbot.setup import DiagnosticCheck
        report = DiagnosticReport(checks=[
            DiagnosticCheck(name="test", status=CheckStatus.SKIP, message="skipped"),
            DiagnosticCheck(name="test2", status=CheckStatus.PASS, message="ok"),
        ])
        assert report.passed is True

    def test_counts(self) -> None:
        from vaultbot.setup import DiagnosticCheck
        report = DiagnosticReport(checks=[
            DiagnosticCheck(name="a", status=CheckStatus.PASS, message="ok"),
            DiagnosticCheck(name="b", status=CheckStatus.WARN, message="warn"),
            DiagnosticCheck(name="c", status=CheckStatus.FAIL, message="fail"),
        ])
        assert report.pass_count == 1
        assert report.warn_count == 1
        assert report.fail_count == 1


class TestSetupWizard:
    def test_create_config_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import vaultbot.setup as setup_mod
        monkeypatch.setattr(setup_mod, "CONFIG_DIR", tmp_path / "vaultbot_test")

        wizard = SetupWizard()
        assert wizard.create_config_dir() is True
        assert "config_dir" in wizard.steps_completed

    def test_steps_initially_empty(self) -> None:
        wizard = SetupWizard()
        assert wizard.steps_completed == []
