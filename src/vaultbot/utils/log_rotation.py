"""Log file rotation with configurable size and count."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RotationConfig:
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    log_dir: str = ""


class LogRotator:
    """Manages log file rotation."""

    def __init__(self, config: RotationConfig | None = None) -> None:
        self._config = config or RotationConfig()
        self._rotation_count = 0

    @property
    def config(self) -> RotationConfig:
        return self._config

    @property
    def rotation_count(self) -> int:
        return self._rotation_count

    def should_rotate(self, file_path: str) -> bool:
        """Check if a log file needs rotation."""
        path = Path(file_path)
        if not path.exists():
            return False
        return path.stat().st_size >= self._config.max_bytes

    def rotate(self, file_path: str) -> bool:
        """Rotate a log file, shifting backups."""
        path = Path(file_path)
        if not path.exists():
            return False

        # Shift existing backups
        for i in range(self._config.backup_count - 1, 0, -1):
            src = Path(f"{file_path}.{i}")
            dst = Path(f"{file_path}.{i + 1}")
            if src.exists():
                src.rename(dst)

        # Move current to .1
        path.rename(Path(f"{file_path}.1"))
        self._rotation_count += 1
        return True

    def cleanup_old(self, file_path: str) -> int:
        """Remove backups beyond the configured count."""
        removed = 0
        for i in range(self._config.backup_count + 1, self._config.backup_count + 10):
            path = Path(f"{file_path}.{i}")
            if path.exists():
                path.unlink()
                removed += 1
        return removed
