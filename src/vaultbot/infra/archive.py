"""Secure archive extraction with safety checks."""

from __future__ import annotations

import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_MAX_EXTRACT_SIZE = 500 * 1024 * 1024  # 500MB
_MAX_FILES = 10000


class ArchiveSecurityError(Exception):
    """Raised when archive contains unsafe content."""


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    extracted_files: int
    total_size: int
    target_dir: str


def _check_path_safe(name: str, target: Path) -> bool:
    """Check that an archive member doesn't escape the target directory."""
    resolved = (target / name).resolve()
    return str(resolved).startswith(str(target.resolve()))


def extract_zip(
    archive_path: str, target_dir: str, max_size: int = _MAX_EXTRACT_SIZE
) -> ExtractionResult:
    """Extract a ZIP archive with security checks."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as zf:
        total_size = sum(i.file_size for i in zf.infolist())
        if total_size > max_size:
            raise ArchiveSecurityError(f"Archive too large: {total_size} bytes")
        if len(zf.infolist()) > _MAX_FILES:
            raise ArchiveSecurityError(f"Too many files: {len(zf.infolist())}")

        for info in zf.infolist():
            if not _check_path_safe(info.filename, target):
                raise ArchiveSecurityError(f"Path traversal: {info.filename}")
            if info.filename.startswith("/") or ".." in info.filename:
                raise ArchiveSecurityError(f"Unsafe path: {info.filename}")

        zf.extractall(target)  # noqa: S202
        return ExtractionResult(
            extracted_files=len(zf.infolist()),
            total_size=total_size,
            target_dir=str(target),
        )


def extract_tar(
    archive_path: str, target_dir: str, max_size: int = _MAX_EXTRACT_SIZE
) -> ExtractionResult:
    """Extract a TAR archive with security checks."""
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:*") as tf:
        members = tf.getmembers()
        if len(members) > _MAX_FILES:
            raise ArchiveSecurityError(f"Too many files: {len(members)}")

        total_size = sum(m.size for m in members if m.isfile())
        if total_size > max_size:
            raise ArchiveSecurityError(f"Archive too large: {total_size} bytes")

        for member in members:
            if not _check_path_safe(member.name, target):
                raise ArchiveSecurityError(f"Path traversal: {member.name}")
            if member.issym() or member.islnk():
                raise ArchiveSecurityError(f"Symlink not allowed: {member.name}")

        tf.extractall(target, filter="data")
        return ExtractionResult(
            extracted_files=len(members),
            total_size=total_size,
            target_dir=str(target),
        )
