"""Configurable binary allow-list with hash verification.

Only binaries whose SHA-256 hash matches the stored entry are
permitted to run. This prevents tampering or unknown binaries.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AllowlistEntry:
    name: str
    path: str
    sha256: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class BinaryCheckResult:
    allowed: bool
    binary_name: str
    reason: str = ""
    hash_match: bool = False


@dataclass(slots=True)
class BinaryAllowlist:
    """Maintains and checks a set of allowed binaries."""

    _entries: dict[str, AllowlistEntry] = field(default_factory=dict)
    _strict: bool = True
    _check_count: int = 0

    def register(self, entry: AllowlistEntry) -> None:
        """Add or update an allow-list entry."""
        self._entries[entry.name] = entry
        logger.info(
            "binary_registered", name=entry.name, path=entry.path,
        )

    def remove(self, name: str) -> bool:
        """Remove a binary from the allow-list."""
        if name in self._entries:
            del self._entries[name]
            return True
        return False

    def check(
        self, name: str, path: str | None = None,
    ) -> BinaryCheckResult:
        """Check if a binary is allowed and verify its hash."""
        self._check_count += 1
        entry = self._entries.get(name)
        if entry is None:
            if self._strict:
                logger.warning("binary_not_allowed", name=name)
                return BinaryCheckResult(
                    allowed=False,
                    binary_name=name,
                    reason="Binary not in allowlist",
                )
            return BinaryCheckResult(
                allowed=True,
                binary_name=name,
                reason="Strict mode disabled",
            )
        if path is None:
            return BinaryCheckResult(
                allowed=True,
                binary_name=name,
                reason="Name found in allowlist (no hash check)",
            )
        file_path = Path(path)
        if not file_path.exists():
            return BinaryCheckResult(
                allowed=False,
                binary_name=name,
                reason=f"Binary not found at {path}",
            )
        actual_hash = _sha256_file(file_path)
        if actual_hash != entry.sha256:
            logger.warning(
                "binary_hash_mismatch",
                name=name,
                expected=entry.sha256[:16],
                actual=actual_hash[:16],
            )
            return BinaryCheckResult(
                allowed=False,
                binary_name=name,
                reason="SHA-256 hash mismatch",
            )
        return BinaryCheckResult(
            allowed=True, binary_name=name, hash_match=True,
        )

    def is_allowed(self, name: str) -> bool:
        """Quick check: is the binary name in the allow-list?"""
        return name in self._entries

    @property
    def check_count(self) -> int:
        return self._check_count

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def list_entries(self) -> list[AllowlistEntry]:
        """Return all registered entries."""
        return list(self._entries.values())


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def compute_sha256(path: str | Path) -> str:
    """Public utility to compute a SHA-256 for registering binaries."""
    return _sha256_file(Path(path))
