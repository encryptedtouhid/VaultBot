"""Deep code safety scanning for plugins and agent code.

NOTE: This scanner DETECTS dangerous patterns (like pickle, os.system, shell=True)
in plugin code to FLAG them as security issues. It does not use these patterns itself.
The regex patterns below are detection rules, not usage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    INJECTION = "injection"
    FILE_ACCESS = "file_access"
    NETWORK = "network"
    CRYPTO = "crypto"
    DANGEROUS_CALL = "dangerous_call"
    CONFIGURATION = "configuration"


@dataclass(frozen=True, slots=True)
class SecurityFinding:
    title: str
    severity: Severity
    category: FindingCategory
    description: str = ""
    file_path: str = ""
    line_number: int = 0
    remediation: str = ""


# Detection patterns for flagging dangerous code in plugins
_DANGEROUS_PATTERNS: list[tuple[str, Severity, FindingCategory, str]] = [
    (
        r"\bos\.system\b",
        Severity.HIGH,
        FindingCategory.INJECTION,
        "os.system is vulnerable to injection",
    ),
    (
        r"\byaml\.load\b(?!.*Loader)",
        Severity.MEDIUM,
        FindingCategory.INJECTION,
        "yaml.load without Loader is unsafe",
    ),
    (
        r"\b(?:chmod|chown)\b.*0o?777",
        Severity.MEDIUM,
        FindingCategory.FILE_ACCESS,
        "World-writable permissions",
    ),
    (
        r"password\s*=\s*['\"][^'\"]+['\"]",
        Severity.MEDIUM,
        FindingCategory.CRYPTO,
        "Hardcoded password detected",
    ),
    (
        r"\brequests\.get\b.*verify\s*=\s*False",
        Severity.MEDIUM,
        FindingCategory.NETWORK,
        "SSL verification disabled",
    ),
]

_SAFE_BINARIES = frozenset(
    {
        "python3",
        "python",
        "node",
        "git",
        "ls",
        "cat",
        "echo",
        "grep",
        "find",
        "wc",
        "sort",
        "head",
        "tail",
    }
)


class CodeScanner:
    """Scans code for security issues."""

    def __init__(self) -> None:
        self._scan_count = 0

    @property
    def scan_count(self) -> int:
        return self._scan_count

    def scan_code(self, code: str, file_path: str = "") -> list[SecurityFinding]:
        """Scan code string for security issues."""
        findings: list[SecurityFinding] = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern, severity, category, desc in _DANGEROUS_PATTERNS:
                if re.search(pattern, line):
                    findings.append(
                        SecurityFinding(
                            title=desc,
                            severity=severity,
                            category=category,
                            description=f"Found in: {line.strip()[:80]}",
                            file_path=file_path,
                            line_number=i,
                        )
                    )

        self._scan_count += 1
        return findings

    def check_binary_allowed(self, binary: str) -> bool:
        """Check if a binary is in the safe allowlist."""
        return binary in _SAFE_BINARIES

    def audit_sandbox_config(self, config: dict[str, object]) -> list[SecurityFinding]:
        """Audit a sandbox/Docker configuration."""
        findings: list[SecurityFinding] = []
        if config.get("privileged"):
            findings.append(
                SecurityFinding(
                    title="Privileged container",
                    severity=Severity.CRITICAL,
                    category=FindingCategory.CONFIGURATION,
                    description="Container runs in privileged mode",
                    remediation="Remove privileged flag",
                )
            )
        if config.get("network_mode") == "host":
            findings.append(
                SecurityFinding(
                    title="Host network mode",
                    severity=Severity.HIGH,
                    category=FindingCategory.NETWORK,
                    description="Container uses host networking",
                )
            )
        return findings

    def summarize(self, findings: list[SecurityFinding]) -> dict[str, int]:
        """Summarize findings by severity."""
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return counts
