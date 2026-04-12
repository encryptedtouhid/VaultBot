"""Markdown intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IRNodeType(str, Enum):
    TEXT = "text"
    BOLD = "bold"
    ITALIC = "italic"
    CODE = "code"
    CODE_BLOCK = "code_block"
    LINK = "link"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE = "table"
    PARAGRAPH = "paragraph"


@dataclass(slots=True)
class IRNode:
    node_type: IRNodeType
    content: str = ""
    children: list[IRNode] = field(default_factory=list)
    url: str = ""
    language: str = ""
    level: int = 0


def parse_to_ir(markdown: str) -> list[IRNode]:
    """Parse markdown text into intermediate representation nodes."""
    nodes: list[IRNode] = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            nodes.append(
                IRNode(
                    node_type=IRNodeType.CODE_BLOCK,
                    content="\n".join(code_lines),
                    language=lang,
                )
            )
            i += 1
            continue

        # Headings
        if line.startswith("### "):
            nodes.append(IRNode(node_type=IRNodeType.HEADING, content=line[4:], level=3))
        elif line.startswith("## "):
            nodes.append(IRNode(node_type=IRNodeType.HEADING, content=line[3:], level=2))
        elif line.startswith("# "):
            nodes.append(IRNode(node_type=IRNodeType.HEADING, content=line[2:], level=1))
        elif line.startswith("- ") or line.startswith("* "):
            nodes.append(IRNode(node_type=IRNodeType.LIST_ITEM, content=line[2:]))
        elif line.strip():
            nodes.append(IRNode(node_type=IRNodeType.PARAGRAPH, content=line))

        i += 1

    return nodes


def ir_to_plain(nodes: list[IRNode]) -> str:
    """Convert IR nodes back to plain text."""
    parts = []
    for node in nodes:
        if node.node_type == IRNodeType.HEADING:
            parts.append(f"{'#' * node.level} {node.content}")
        elif node.node_type == IRNodeType.CODE_BLOCK:
            parts.append(f"```{node.language}\n{node.content}\n```")
        elif node.node_type == IRNodeType.LIST_ITEM:
            parts.append(f"- {node.content}")
        else:
            parts.append(node.content)
    return "\n".join(parts)
