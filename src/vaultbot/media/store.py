"""Media file storage with SSRF prevention and workspace boundaries."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "169.254.169.254",
        "metadata.google.internal",
        "[::1]",
    }
)

_BLOCKED_PREFIXES = ("10.", "172.16.", "172.17.", "172.18.", "192.168.")


def is_url_safe(url: str) -> bool:
    """Check if a URL is safe (no SSRF to internal networks)."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host in _BLOCKED_HOSTS:
            return False
        if any(host.startswith(p) for p in _BLOCKED_PREFIXES):
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        return True
    except Exception:
        return False


@dataclass(frozen=True, slots=True)
class StoredFile:
    file_id: str
    path: str
    mime_type: str = ""
    size_bytes: int = 0
    stored_at: float = field(default_factory=time.time)


class MediaStore:
    """File storage with workspace boundary enforcement."""

    def __init__(self, workspace: str | Path = "/tmp/vaultbot-media") -> None:  # noqa: S108
        self._workspace = Path(workspace)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, StoredFile] = {}

    @property
    def workspace(self) -> Path:
        return self._workspace

    @property
    def file_count(self) -> int:
        return len(self._files)

    def store(self, data: bytes, filename: str, mime_type: str = "") -> StoredFile:
        """Store data within workspace boundary."""
        file_id = hashlib.sha256(data[:1024]).hexdigest()[:12]
        safe_name = Path(filename).name  # Strip directory traversal
        file_path = self._workspace / f"{file_id}_{safe_name}"

        # Verify path stays within workspace
        resolved = file_path.resolve()
        if not str(resolved).startswith(str(self._workspace.resolve())):
            raise ValueError("Path traversal attempt blocked")

        file_path.write_bytes(data)
        stored = StoredFile(
            file_id=file_id,
            path=str(file_path),
            mime_type=mime_type,
            size_bytes=len(data),
        )
        self._files[file_id] = stored
        return stored

    def retrieve(self, file_id: str) -> bytes | None:
        stored = self._files.get(file_id)
        if not stored:
            return None
        path = Path(stored.path)
        if path.exists():
            return path.read_bytes()
        return None

    def delete(self, file_id: str) -> bool:
        stored = self._files.get(file_id)
        if not stored:
            return False
        path = Path(stored.path)
        if path.exists():
            path.unlink()
        del self._files[file_id]
        return True

    def list_files(self) -> list[StoredFile]:
        return list(self._files.values())
