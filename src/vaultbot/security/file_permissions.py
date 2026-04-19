"""Workspace-bounded file access validation.

Ensures that all file operations stay within the designated workspace
directory. Prevents path-traversal attacks and validates file
permissions before reads or writes.
"""

from __future__ import annotations

import stat
from dataclasses import dataclass, field
from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AccessResult:
    allowed: bool
    path: str
    reason: str = ""


@dataclass(slots=True)
class FilePermissionChecker:
    """Validates file access stays within workspace boundaries."""

    _workspace: Path
    _deny_patterns: list[str] = field(default_factory=list)
    _check_count: int = 0

    def __post_init__(self) -> None:
        self._workspace = self._workspace.resolve()
        if not self._deny_patterns:
            self._deny_patterns = [
                ".env", ".git/config", "id_rsa", "id_ed25519",
                ".ssh", ".gnupg", "credentials.json", "secrets.yaml",
            ]

    def check_access(self, target: str | Path) -> AccessResult:
        """Check whether target is within the workspace."""
        self._check_count += 1
        target_path = Path(target).resolve()
        try:
            target_path.relative_to(self._workspace)
        except ValueError:
            logger.warning(
                "path_traversal_blocked",
                target=str(target),
                resolved=str(target_path),
                workspace=str(self._workspace),
            )
            return AccessResult(
                allowed=False,
                path=str(target_path),
                reason="Path is outside workspace boundary",
            )
        rel = str(target_path.relative_to(self._workspace))
        for pattern in self._deny_patterns:
            if pattern in rel:
                logger.warning(
                    "denied_file_pattern",
                    target=rel,
                    pattern=pattern,
                )
                return AccessResult(
                    allowed=False,
                    path=str(target_path),
                    reason=f"Matches deny pattern: {pattern}",
                )
        return AccessResult(allowed=True, path=str(target_path))

    def is_within_workspace(self, target: str | Path) -> bool:
        """Convenience: return True if path is inside workspace."""
        return self.check_access(target).allowed

    def check_file_mode(self, target: str | Path) -> AccessResult:
        """Verify file permissions are not overly permissive."""
        target_path = Path(target)
        if not target_path.exists():
            return AccessResult(
                allowed=True,
                path=str(target_path),
                reason="File does not exist yet",
            )
        mode = target_path.stat().st_mode
        issues: list[str] = []
        if mode & stat.S_IWOTH:
            issues.append("world-writable")
        if mode & stat.S_IROTH and _is_sensitive_name(target_path.name):
            issues.append("world-readable sensitive file")
        if issues:
            return AccessResult(
                allowed=False,
                path=str(target_path),
                reason="; ".join(issues),
            )
        return AccessResult(allowed=True, path=str(target_path))

    def add_deny_pattern(self, pattern: str) -> None:
        """Add a custom deny pattern."""
        self._deny_patterns.append(pattern)

    @property
    def check_count(self) -> int:
        return self._check_count

    @property
    def workspace(self) -> Path:
        return self._workspace


def _is_sensitive_name(name: str) -> bool:
    """Heuristic: is this filename likely sensitive?"""
    sensitive_keywords = {
        "secret", "credential", "key", "token",
        "cert", "pem", "env", "private",
    }
    lower = name.lower()
    return any(kw in lower for kw in sensitive_keywords)


def validate_workspace_path(
    workspace: Path, target: str | Path,
) -> bool:
    """Quick standalone check."""
    checker = FilePermissionChecker(_workspace=workspace)
    return checker.is_within_workspace(target)
