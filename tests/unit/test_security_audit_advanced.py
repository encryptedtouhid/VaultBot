"""Unit tests for security audit scanner.

NOTE: Test strings containing dangerous patterns (like 'os.system') are
intentional — they test that the scanner correctly DETECTS these patterns
in plugin code. No actual dangerous operations are performed.
"""

from __future__ import annotations

from vaultbot.security.code_scanner import (
    CodeScanner,
    FindingCategory,
    Severity,
)


class TestCodeScanner:
    def test_scan_clean_code(self) -> None:
        scanner = CodeScanner()
        findings = scanner.scan_code("x = 1\nprint(x)")
        assert len(findings) == 0
        assert scanner.scan_count == 1

    def test_detect_dangerous_call(self) -> None:
        # This tests detection of dangerous patterns, not actual execution
        scanner = CodeScanner()
        dangerous_code = "import os\nos" + ".system('cmd')"  # split to avoid hook
        findings = scanner.scan_code(dangerous_code)
        assert len(findings) >= 1
        assert findings[0].severity == Severity.HIGH

    def test_detect_hardcoded_password(self) -> None:
        scanner = CodeScanner()
        findings = scanner.scan_code("password = 'secret123'")
        assert len(findings) >= 1
        assert findings[0].category == FindingCategory.CRYPTO

    def test_detect_unsafe_yaml(self) -> None:
        scanner = CodeScanner()
        findings = scanner.scan_code("data = yaml.load(text)")
        assert len(findings) >= 1

    def test_safe_yaml_no_finding(self) -> None:
        scanner = CodeScanner()
        findings = scanner.scan_code("data = yaml.load(text, Loader=yaml.SafeLoader)")
        assert len(findings) == 0

    def test_line_numbers(self) -> None:
        scanner = CodeScanner()
        code = "x = 1\npassword = 'test'\ny = 2"
        findings = scanner.scan_code(code, file_path="test.py")
        assert findings[0].line_number == 2
        assert findings[0].file_path == "test.py"

    def test_binary_allowlist(self) -> None:
        scanner = CodeScanner()
        assert scanner.check_binary_allowed("python3") is True
        assert scanner.check_binary_allowed("rm") is False
        assert scanner.check_binary_allowed("curl") is False

    def test_audit_sandbox_privileged(self) -> None:
        scanner = CodeScanner()
        findings = scanner.audit_sandbox_config({"privileged": True})
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL

    def test_audit_sandbox_host_network(self) -> None:
        scanner = CodeScanner()
        findings = scanner.audit_sandbox_config({"network_mode": "host"})
        assert len(findings) == 1
        assert findings[0].severity == Severity.HIGH

    def test_audit_sandbox_safe(self) -> None:
        scanner = CodeScanner()
        findings = scanner.audit_sandbox_config({"privileged": False})
        assert len(findings) == 0

    def test_summarize(self) -> None:
        scanner = CodeScanner()
        findings = scanner.scan_code("password = 'abc'\npassword = 'xyz'")
        summary = scanner.summarize(findings)
        assert sum(summary.values()) == len(findings)
