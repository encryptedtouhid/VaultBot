"""Cross-platform process execution."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    timed_out: bool = False


class ProcessExecutor:
    """Execute processes with timeout and output capture."""

    def __init__(self, default_timeout: float = 30.0) -> None:
        self._default_timeout = default_timeout
        self._execution_count = 0

    @property
    def execution_count(self) -> int:
        return self._execution_count

    def execute(
        self,
        args: list[str],
        timeout: float | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> ProcessResult:
        """Execute a process with argument list (no shell)."""
        start = time.monotonic()
        try:
            result = subprocess.run(  # noqa: S603
                args,
                capture_output=True,
                text=True,
                timeout=timeout or self._default_timeout,
                cwd=cwd,
                env=env,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._execution_count += 1
            return ProcessResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=elapsed_ms,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._execution_count += 1
            return ProcessResult(exit_code=-1, timed_out=True, duration_ms=elapsed_ms)
        except FileNotFoundError:
            return ProcessResult(exit_code=-1, stderr="Command not found")
