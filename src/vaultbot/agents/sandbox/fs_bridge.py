"""File system bridge with safety boundary enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class PathTraversalError(Exception):
    """Raised when a path escapes the workspace boundary."""


@dataclass(frozen=True, slots=True)
class WorkspaceBoundary:
    root: Path
    readonly: bool = False
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50MB


class FsBridge:
    """File system abstraction with safety boundary enforcement."""

    def __init__(self, boundary: WorkspaceBoundary) -> None:
        self._boundary = boundary

    @property
    def root(self) -> Path:
        return self._boundary.root

    def resolve_safe(self, relative_path: str) -> Path:
        """Resolve a path within the workspace, blocking traversal."""
        resolved = (self._boundary.root / relative_path).resolve()
        if not str(resolved).startswith(str(self._boundary.root.resolve())):
            raise PathTraversalError(f"Path escapes workspace: {relative_path}")
        return resolved

    def read_file(self, relative_path: str) -> bytes:
        path = self.resolve_safe(relative_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return path.read_bytes()

    def write_file(self, relative_path: str, data: bytes) -> Path:
        if self._boundary.readonly:
            raise PermissionError("Workspace is read-only")
        if len(data) > self._boundary.max_file_size_bytes:
            raise ValueError(f"File exceeds max size: {len(data)} bytes")
        path = self.resolve_safe(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def delete_file(self, relative_path: str) -> bool:
        if self._boundary.readonly:
            raise PermissionError("Workspace is read-only")
        path = self.resolve_safe(relative_path)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_files(self, relative_dir: str = ".") -> list[str]:
        dir_path = self.resolve_safe(relative_dir)
        if not dir_path.is_dir():
            return []
        root = self._boundary.root.resolve()
        return [str(p.relative_to(root)) for p in dir_path.rglob("*") if p.is_file()]

    def file_exists(self, relative_path: str) -> bool:
        try:
            path = self.resolve_safe(relative_path)
            return path.exists()
        except PathTraversalError:
            return False
