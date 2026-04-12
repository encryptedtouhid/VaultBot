"""Markdown rendering with syntax highlighting for terminal."""

from __future__ import annotations

import re


def render_markdown(text: str) -> str:
    """Render markdown to terminal-friendly output with ANSI codes."""
    lines = []
    in_code = False

    for line in text.split("\n"):
        if line.startswith("```"):
            in_code = not in_code
            lines.append(f"\033[90m{line}\033[0m")
            continue

        if in_code:
            lines.append(f"\033[36m{line}\033[0m")
            continue

        # Headers
        if line.startswith("### "):
            lines.append(f"\033[1;33m{line[4:]}\033[0m")
        elif line.startswith("## "):
            lines.append(f"\033[1;32m{line[3:]}\033[0m")
        elif line.startswith("# "):
            lines.append(f"\033[1;35m{line[2:]}\033[0m")
        else:
            # Bold
            rendered = re.sub(r"\*\*(.+?)\*\*", r"\033[1m\1\033[0m", line)
            # Italic
            rendered = re.sub(r"\*(.+?)\*", r"\033[3m\1\033[0m", rendered)
            # Inline code
            rendered = re.sub(r"`(.+?)`", r"\033[36m\1\033[0m", rendered)
            lines.append(rendered)

    return "\n".join(lines)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\033\[[0-9;]*m", "", text)


def render_aware_chunk(text: str, max_length: int = 2000) -> list[str]:
    """Split text into chunks while preserving markdown formatting."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_length:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
