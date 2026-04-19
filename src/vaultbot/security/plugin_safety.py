"""Static analysis of plugin code before loading.

Scans plugin source for dangerous patterns (network I/O, filesystem
access, subprocess calls, dynamic imports) and assigns a safety score.
Plugins below the minimum score are rejected.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SafetyLevel(str, Enum):
    SAFE = "safe"
    CAUTIOUS = "cautious"
    RISKY = "risky"
    DANGEROUS = "dangerous"


@dataclass(frozen=True, slots=True)
class SafetyIssue:
    description: str
    line_number: int = 0
    penalty: int = 10


@dataclass(frozen=True, slots=True)
class SafetyReport:
    plugin_name: str
    score: int
    level: SafetyLevel
    issues: tuple[SafetyIssue, ...] = ()

    @property
    def is_acceptable(self) -> bool:
        return self.level in (SafetyLevel.SAFE, SafetyLevel.CAUTIOUS)


_DANGEROUS_IMPORTS: frozenset[str] = frozenset({
    "subprocess",
    "ctypes",
    "socket",
    "http.client",
    "urllib.request",
    "shutil",
    "multiprocessing",
    "pickle",
    "shelve",
    "marshal",
})

_DANGEROUS_CALLS: list[tuple[str, int, str]] = [
    (r"\bos\.system\b", 30, "os.system call"),
    (r"\bos\.popen\b", 25, "os.popen call"),
    (r"\bsubprocess\.\w+\b", 20, "subprocess usage"),
    (r"\bopen\s*\(.*['\"]w['\"]", 10, "file write operation"),
    (r"\bsocket\.socket\b", 20, "raw socket creation"),
    (r"\bctypes\.\w+", 25, "ctypes FFI usage"),
    (r"\bpickle\.loads?\b", 20, "pickle deserialization"),
]


@dataclass(slots=True)
class PluginSafetyAnalyzer:
    """Performs static analysis of plugin source code."""

    _min_score: int = 50
    _scan_count: int = 0

    def analyze(
        self, source: str, plugin_name: str = "",
    ) -> SafetyReport:
        """Analyze plugin source code and return a safety report."""
        self._scan_count += 1
        issues: list[SafetyIssue] = []
        issues.extend(self._check_imports(source))
        issues.extend(self._check_patterns(source))
        issues.extend(self._check_ast(source))
        total_penalty = sum(i.penalty for i in issues)
        score = max(0, 100 - total_penalty)
        level = _score_to_level(score)
        report = SafetyReport(
            plugin_name=plugin_name,
            score=score,
            level=level,
            issues=tuple(issues),
        )
        if not report.is_acceptable:
            logger.warning(
                "plugin_safety_rejected",
                plugin=plugin_name,
                score=score,
                level=level.value,
                issue_count=len(issues),
            )
        return report

    def is_safe_to_load(
        self, source: str, plugin_name: str = "",
    ) -> bool:
        """Convenience: True if the plugin passes safety analysis."""
        return self.analyze(source, plugin_name).is_acceptable

    @property
    def scan_count(self) -> int:
        return self._scan_count

    @property
    def min_score(self) -> int:
        return self._min_score

    @staticmethod
    def _check_imports(source: str) -> list[SafetyIssue]:
        issues: list[SafetyIssue] = []
        for i, line in enumerate(source.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                for dangerous in _DANGEROUS_IMPORTS:
                    if dangerous in stripped:
                        issues.append(SafetyIssue(
                            description=(
                                f"Dangerous import: {dangerous}"
                            ),
                            line_number=i,
                            penalty=15,
                        ))
        return issues

    @staticmethod
    def _check_patterns(source: str) -> list[SafetyIssue]:
        issues: list[SafetyIssue] = []
        lines = source.split("\n")
        for i, line in enumerate(lines, 1):
            for pattern, penalty, desc in _DANGEROUS_CALLS:
                if re.search(pattern, line):
                    issues.append(SafetyIssue(
                        description=desc,
                        line_number=i,
                        penalty=penalty,
                    ))
        return issues

    @staticmethod
    def _check_ast(source: str) -> list[SafetyIssue]:
        """Use AST to detect dynamic attribute access on os/sys."""
        issues: list[SafetyIssue] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            issues.append(SafetyIssue(
                description="Failed to parse: syntax error",
                penalty=5,
            ))
            return issues
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr in (
                        "system", "popen", "execvp", "fork",
                    )
                ):
                    issues.append(SafetyIssue(
                        description=(
                            f"os.{node.attr} via AST"
                        ),
                        line_number=getattr(node, "lineno", 0),
                        penalty=25,
                    ))
        return issues


def _score_to_level(score: int) -> SafetyLevel:
    if score >= 80:
        return SafetyLevel.SAFE
    if score >= 50:
        return SafetyLevel.CAUTIOUS
    if score >= 20:
        return SafetyLevel.RISKY
    return SafetyLevel.DANGEROUS
