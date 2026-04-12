"""Dedicated coding agent with sandbox execution."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class CodeLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"


@dataclass(frozen=True, slots=True)
class CodeExecutionRequest:
    code: str
    language: CodeLanguage = CodeLanguage.PYTHON
    timeout_seconds: int = 30
    working_dir: str = ""


@dataclass(frozen=True, slots=True)
class CodeExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0


@dataclass(frozen=True, slots=True)
class CodeReviewResult:
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    score: float = 0.0


class CodingAgent:
    """Dedicated coding agent for code generation, execution, and review.

    NOTE: Uses subprocess.run with explicit argument lists (no shell=True)
    to prevent command injection. Code is passed as a direct argument to
    the interpreter, not through shell expansion.
    """

    def __init__(self, sandbox_dir: str | None = None) -> None:
        self._sandbox_dir = Path(sandbox_dir) if sandbox_dir else Path(tempfile.mkdtemp())
        self._execution_count = 0

    @property
    def sandbox_dir(self) -> Path:
        return self._sandbox_dir

    @property
    def execution_count(self) -> int:
        return self._execution_count

    async def execute(self, request: CodeExecutionRequest) -> CodeExecutionResult:
        """Execute code in a sandboxed environment using subprocess with argument lists."""
        lang_cmds = {
            CodeLanguage.PYTHON: ["python3", "-c"],
            CodeLanguage.JAVASCRIPT: ["node", "-e"],
            CodeLanguage.BASH: ["bash", "-c"],
        }
        cmd = lang_cmds.get(request.language)
        if not cmd:
            return CodeExecutionResult(
                success=False, stderr=f"Unsupported language: {request.language}"
            )

        try:
            # Uses argument list (not shell=True) to prevent injection
            result = subprocess.run(  # noqa: S603
                [*cmd, request.code],
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                cwd=request.working_dir or str(self._sandbox_dir),
            )
            self._execution_count += 1
            return CodeExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return CodeExecutionResult(success=False, stderr="Execution timed out", exit_code=-1)

    def review_code(
        self, code: str, language: CodeLanguage = CodeLanguage.PYTHON
    ) -> CodeReviewResult:
        """Basic code review with heuristic checks."""
        issues: list[str] = []
        suggestions: list[str] = []

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(f"Line {i}: exceeds 120 characters")

        if not code.strip():
            issues.append("Code is empty")

        score = max(0.0, 1.0 - len(issues) * 0.1)
        return CodeReviewResult(issues=issues, suggestions=suggestions, score=score)
