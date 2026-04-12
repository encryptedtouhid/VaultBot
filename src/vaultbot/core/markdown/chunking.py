"""Render-aware chunking for platform message limits."""

from __future__ import annotations


def chunk_markdown(text: str, max_length: int = 2000) -> list[str]:
    """Split markdown while preserving formatting.

    Avoids splitting inside code blocks or mid-paragraph.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""
    in_code_block = False

    for line in text.split("\n"):
        if line.startswith("```"):
            in_code_block = not in_code_block

        # Don't split inside code blocks
        if in_code_block:
            current = f"{current}\n{line}" if current else line
            continue

        if len(current) + len(line) + 1 > max_length and current:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current)

    return chunks
