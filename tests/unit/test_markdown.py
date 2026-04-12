"""Unit tests for markdown rendering."""

from __future__ import annotations

from vaultbot.core.markdown.chunking import chunk_markdown
from vaultbot.core.markdown.ir import IRNodeType, ir_to_plain, parse_to_ir


class TestMarkdownIR:
    def test_parse_heading(self) -> None:
        nodes = parse_to_ir("# Title")
        assert len(nodes) == 1
        assert nodes[0].node_type == IRNodeType.HEADING
        assert nodes[0].level == 1

    def test_parse_code_block(self) -> None:
        nodes = parse_to_ir("```python\nprint('hi')\n```")
        assert len(nodes) == 1
        assert nodes[0].node_type == IRNodeType.CODE_BLOCK
        assert nodes[0].language == "python"

    def test_parse_list_item(self) -> None:
        nodes = parse_to_ir("- Item 1\n- Item 2")
        assert len(nodes) == 2
        assert all(n.node_type == IRNodeType.LIST_ITEM for n in nodes)

    def test_parse_paragraph(self) -> None:
        nodes = parse_to_ir("Hello world")
        assert len(nodes) == 1
        assert nodes[0].node_type == IRNodeType.PARAGRAPH

    def test_parse_mixed(self) -> None:
        md = "# Title\n\nParagraph text\n\n- Item 1"
        nodes = parse_to_ir(md)
        types = [n.node_type for n in nodes]
        assert IRNodeType.HEADING in types
        assert IRNodeType.PARAGRAPH in types
        assert IRNodeType.LIST_ITEM in types

    def test_ir_to_plain(self) -> None:
        nodes = parse_to_ir("# Title\n\nHello")
        plain = ir_to_plain(nodes)
        assert "# Title" in plain
        assert "Hello" in plain


class TestChunking:
    def test_short_text(self) -> None:
        chunks = chunk_markdown("short", max_length=100)
        assert len(chunks) == 1

    def test_long_text(self) -> None:
        text = "\n".join(f"Line {i}" for i in range(100))
        chunks = chunk_markdown(text, max_length=200)
        assert len(chunks) > 1
        assert all(len(c) <= 200 for c in chunks)

    def test_preserves_code_blocks(self) -> None:
        text = "Before\n```\n" + "x\n" * 50 + "```\nAfter"
        chunks = chunk_markdown(text, max_length=100)
        # Code block content should stay together
        code_chunk = [c for c in chunks if "```" in c]
        assert len(code_chunk) >= 1
