"""Canvas-hosted diff viewer with export support."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class DiffFormat(str, Enum):
    UNIFIED = "unified"
    SIDE_BY_SIDE = "side_by_side"
    HTML = "html"


@dataclass(frozen=True, slots=True)
class DiffResult:
    format: DiffFormat
    content: str
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0


class DiffViewer:
    """Generate and display diffs in various formats."""

    def unified_diff(self, old: str, new: str, filename: str = "file") -> DiffResult:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = list(
            difflib.unified_diff(
                old_lines, new_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}"
            )
        )
        additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        return DiffResult(
            format=DiffFormat.UNIFIED,
            content="".join(diff),
            additions=additions,
            deletions=deletions,
            files_changed=1,
        )

    def html_diff(self, old: str, new: str, filename: str = "file") -> DiffResult:
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        differ = difflib.HtmlDiff()
        html = differ.make_file(old_lines, new_lines, fromdesc="Old", todesc="New")
        return DiffResult(format=DiffFormat.HTML, content=html, files_changed=1)

    def side_by_side(self, old: str, new: str) -> DiffResult:
        old_lines = old.splitlines()
        new_lines = new.splitlines()
        max_len = max(len(old_lines), len(new_lines))
        lines = []
        for i in range(max_len):
            left = old_lines[i] if i < len(old_lines) else ""
            right = new_lines[i] if i < len(new_lines) else ""
            marker = " " if left == right else "|"
            lines.append(f"{left:<40} {marker} {right}")
        return DiffResult(
            format=DiffFormat.SIDE_BY_SIDE,
            content="\n".join(lines),
            files_changed=1,
        )


class ExportManager:
    """Export diffs to various formats."""

    def to_markdown(self, diff_result: DiffResult) -> str:
        return f"```diff\n{diff_result.content}\n```\n"

    def to_plain_text(self, diff_result: DiffResult) -> str:
        return diff_result.content

    def summary(self, diff_result: DiffResult) -> str:
        return (
            f"{diff_result.files_changed} file(s) changed, "
            f"+{diff_result.additions} -{diff_result.deletions}"
        )
