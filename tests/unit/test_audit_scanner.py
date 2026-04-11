"""Unit tests for security audit scanner."""

from __future__ import annotations

from pathlib import Path

from vaultbot.security.audit_scanner import (
    AuditReport,
    FindingCategory,
    FindingSeverity,
    SecurityAuditScanner,
)


class TestAuditReport:
    def test_empty_report_passes(self) -> None:
        report = AuditReport()
        assert report.passed is True
        assert report.total_count == 0

    def test_report_with_critical_fails(self) -> None:
        from vaultbot.security.audit_scanner import AuditFinding

        report = AuditReport(
            findings=[
                AuditFinding(
                    severity=FindingSeverity.CRITICAL,
                    category=FindingCategory.SECRET_LEAK,
                    title="test",
                    description="test",
                )
            ]
        )
        assert report.passed is False
        assert report.critical_count == 1


class TestSecurityAuditScanner:
    def test_scan_nonexistent_file(self) -> None:
        scanner = SecurityAuditScanner()
        findings = scanner.scan_file(Path("/nonexistent/file.py"))
        assert findings == []

    def test_scan_clean_file(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        f = tmp_path / "clean.py"
        f.write_text("def hello():\n    return 'world'\n")
        findings = scanner.scan_file(f)
        assert len(findings) == 0

    def test_detect_api_key(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        f = tmp_path / "config.py"
        f.write_text("api_key = 'sk-abcdefghijklmnopqrstuvwxyz1234567890'\n")
        findings = scanner.scan_file(f)
        assert any(fi.severity == FindingSeverity.CRITICAL for fi in findings)

    def test_detect_password(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        f = tmp_path / "settings.yaml"
        f.write_text("password: 'mysecretpassword123'\n")
        findings = scanner.scan_file(f)
        assert any(fi.category == FindingCategory.SECRET_LEAK for fi in findings)

    def test_detect_auth_disabled(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        f = tmp_path / "config.yaml"
        f.write_text("auth: false\n")
        findings = scanner.scan_file(f)
        assert any(fi.category == FindingCategory.CONFIG_RISK for fi in findings)

    def test_scan_directory(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        (tmp_path / "clean.py").write_text("x = 1\n")
        (tmp_path / "config.yaml").write_text("auth: false\n")
        report = scanner.scan_directory(tmp_path)
        assert report.scanned_files == 2
        assert report.total_count >= 1

    def test_scan_directory_skips_pycache(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text("bad code\n")
        report = scanner.scan_directory(tmp_path)
        assert report.scanned_files == 0

    def test_check_permissions_secure(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        f = tmp_path / "secret.key"
        f.write_text("key")
        f.chmod(0o600)
        assert len(scanner.check_file_permissions(f)) == 0

    def test_check_permissions_insecure(self, tmp_path: Path) -> None:
        scanner = SecurityAuditScanner()
        f = tmp_path / "secret.key"
        f.write_text("key")
        f.chmod(0o644)
        findings = scanner.check_file_permissions(f)
        assert len(findings) == 1
        assert findings[0].category == FindingCategory.PERMISSION_RISK

    def test_check_nonexistent(self) -> None:
        scanner = SecurityAuditScanner()
        assert scanner.check_file_permissions(Path("/nonexistent")) == []
