"""Security audit scanner for deep code and config analysis.

Scans plugins, configuration, and runtime state for security issues.
Provides actionable findings with severity levels and auto-fix suggestions.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    SECRET_LEAK = "secret_leak"
    CONFIG_RISK = "config_risk"
    PLUGIN_RISK = "plugin_risk"
    PERMISSION_RISK = "permission_risk"
    NETWORK_RISK = "network_risk"
    CODE_SAFETY = "code_safety"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    severity: FindingSeverity
    category: FindingCategory
    title: str
    description: str
    file_path: str = ""
    line_number: int = 0
    auto_fixable: bool = False
    fix_suggestion: str = ""


@dataclass
class AuditReport:
    findings: list[AuditFinding] = field(default_factory=list)
    scanned_files: int = 0
    scanned_plugins: int = 0
    scan_duration_ms: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.HIGH)

    @property
    def total_count(self) -> int:
        return len(self.findings)

    @property
    def passed(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0


_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"][a-zA-Z0-9_\-]{20,}", "API key in plaintext"),
    (r"(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"][^\s'\"]{8,}", "Secret in plaintext"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
    (r"sk-ant-[a-zA-Z0-9\-]{20,}", "Anthropic API key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
    (r"xoxb-[0-9]{10,}-[a-zA-Z0-9]{20,}", "Slack bot token"),
]

_CONFIG_RISKS: list[tuple[str, str]] = [
    (r"(?i)auth\s*[=:]\s*(false|off|disabled|none)", "Authentication disabled"),
    (r"(?i)sandbox\s*[=:]\s*(false|off|disabled)", "Sandbox disabled"),
    (r"(?i)verify_ssl\s*[=:]\s*false", "SSL verification disabled"),
]

# Patterns that detect unsafe code constructs in scanned files
_UNSAFE_CALL = r"\b{}\s*\("
_CODE_RISK_PATTERNS: list[tuple[str, str]] = [
    (_UNSAFE_CALL.format("os.system"), "os.system() call"),
    (r"__import__\s*\(", "Dynamic __import__() call"),
]


class SecurityAuditScanner:

    def scan_file(self, file_path: Path) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        if not file_path.exists() or not file_path.is_file():
            return findings
        try:
            content = file_path.read_text(errors="replace")
        except OSError:
            return findings

        lines = content.splitlines()

        for pattern, desc in _SECRET_PATTERNS:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    findings.append(AuditFinding(
                        severity=FindingSeverity.CRITICAL,
                        category=FindingCategory.SECRET_LEAK,
                        title=f"Potential secret: {desc}",
                        description=f"Found '{desc}' in {file_path.name}:{i}",
                        file_path=str(file_path),
                        line_number=i,
                        fix_suggestion="Move secrets to env vars or credential store.",
                    ))

        suffix = file_path.suffix.lower()
        if suffix in (".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".json"):
            for pattern, desc in _CONFIG_RISKS:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        findings.append(AuditFinding(
                            severity=FindingSeverity.HIGH,
                            category=FindingCategory.CONFIG_RISK,
                            title=f"Risky config: {desc}",
                            description=f"Found '{desc}' in {file_path.name}:{i}",
                            file_path=str(file_path),
                            line_number=i,
                        ))

        if suffix == ".py":
            for pattern, desc in _CODE_RISK_PATTERNS:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        findings.append(AuditFinding(
                            severity=FindingSeverity.MEDIUM,
                            category=FindingCategory.CODE_SAFETY,
                            title=f"Code risk: {desc}",
                            description=f"Found '{desc}' in {file_path.name}:{i}",
                            file_path=str(file_path),
                            line_number=i,
                        ))

        return findings

    def scan_directory(self, directory: Path, *, extensions: set[str] | None = None) -> AuditReport:
        if extensions is None:
            extensions = {".py", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env", ".json"}
        start = time.monotonic()
        report = AuditReport()
        for file_path in sorted(directory.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in extensions:
                continue
            if "__pycache__" in str(file_path) or ".git" in str(file_path):
                continue
            findings = self.scan_file(file_path)
            report.findings.extend(findings)
            report.scanned_files += 1
        report.scan_duration_ms = int((time.monotonic() - start) * 1000)
        return report

    def check_file_permissions(self, path: Path) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        if not path.exists():
            return findings
        stat = path.stat()
        mode = stat.st_mode & 0o777
        if mode & 0o077:
            findings.append(AuditFinding(
                severity=FindingSeverity.HIGH,
                category=FindingCategory.PERMISSION_RISK,
                title="Overly permissive file permissions",
                description=f"{path.name} has {oct(mode)} — should be 0600",
                file_path=str(path),
                auto_fixable=True,
                fix_suggestion=f"chmod 600 {path}",
            ))
        return findings
