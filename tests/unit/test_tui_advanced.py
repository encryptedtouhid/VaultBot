"""Unit tests for rich TUI."""

from __future__ import annotations

import pytest

from vaultbot.tui.gateway_chat import GatewayChat
from vaultbot.tui.markdown_renderer import render_aware_chunk, render_markdown, strip_ansi


class TestGatewayChat:
    @pytest.mark.asyncio
    async def test_connect_disconnect(self) -> None:
        chat = GatewayChat()
        await chat.connect()
        assert chat.is_connected is True
        await chat.disconnect()
        assert chat.is_connected is False

    def test_add_messages(self) -> None:
        chat = GatewayChat()
        chat.add_user_message("hello")
        chat.add_assistant_message("hi there", model="gpt-4o")
        assert chat.message_count == 2

    def test_get_history(self) -> None:
        chat = GatewayChat()
        for i in range(5):
            chat.add_user_message(f"msg {i}")
        history = chat.get_history(limit=3)
        assert len(history) == 3

    def test_clear_history(self) -> None:
        chat = GatewayChat()
        chat.add_user_message("test")
        chat.clear_history()
        assert chat.message_count == 0

    def test_streaming(self) -> None:
        chat = GatewayChat()
        assert chat.is_streaming is False
        chat.start_streaming()
        assert chat.is_streaming is True
        chat.stop_streaming()
        assert chat.is_streaming is False


class TestMarkdownRenderer:
    def test_render_header(self) -> None:
        result = render_markdown("# Title")
        assert "\033[1;35m" in result
        assert "Title" in result

    def test_render_bold(self) -> None:
        result = render_markdown("**bold text**")
        assert "\033[1m" in result

    def test_render_code_block(self) -> None:
        result = render_markdown("```\ncode here\n```")
        assert "\033[36m" in result

    def test_render_inline_code(self) -> None:
        result = render_markdown("Use `pip install`")
        assert "\033[36m" in result

    def test_strip_ansi(self) -> None:
        rendered = render_markdown("# Title")
        plain = strip_ansi(rendered)
        assert "\033[" not in plain
        assert "Title" in plain

    def test_render_aware_chunk_short(self) -> None:
        chunks = render_aware_chunk("short text", max_length=100)
        assert len(chunks) == 1

    def test_render_aware_chunk_long(self) -> None:
        text = "\n".join(f"Line {i}" for i in range(100))
        chunks = render_aware_chunk(text, max_length=200)
        assert len(chunks) > 1
