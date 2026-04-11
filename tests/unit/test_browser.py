"""Unit tests for browser automation tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vaultbot.tools.browser import BrowserAction, BrowserCommand, BrowserResult, BrowserTool


class TestBrowserTypes:
    def test_action_enum(self) -> None:
        assert BrowserAction.NAVIGATE.value == "navigate"
        assert BrowserAction.SCREENSHOT.value == "screenshot"

    def test_command_defaults(self) -> None:
        cmd = BrowserCommand(action=BrowserAction.NAVIGATE, url="https://example.com")
        assert cmd.selector == ""

    def test_result_defaults(self) -> None:
        r = BrowserResult(success=True, action=BrowserAction.NAVIGATE)
        assert r.data == ""
        assert r.error == ""


class TestBrowserTool:
    def test_initial_state(self) -> None:
        tool = BrowserTool()
        assert tool.is_connected is False
        assert tool.action_count == 0

    def test_sandbox_enabled_by_default(self) -> None:
        tool = BrowserTool()
        assert tool._sandbox is True

    @pytest.mark.asyncio
    async def test_execute_when_not_started(self) -> None:
        tool = BrowserTool()
        cmd = BrowserCommand(action=BrowserAction.NAVIGATE, url="https://example.com")
        result = await tool.execute(cmd)
        assert result.success is False
        assert "not started" in result.error

    @pytest.mark.asyncio
    async def test_navigate_ssrf_blocked(self) -> None:
        tool = BrowserTool()
        tool._connected = True
        tool._page = MagicMock()

        cmd = BrowserCommand(action=BrowserAction.NAVIGATE, url="http://169.254.169.254/meta")
        result = await tool.execute(cmd)
        assert result.success is False
        assert "SSRF" in result.error

    @pytest.mark.asyncio
    async def test_navigate_allowlist_blocked(self) -> None:
        tool = BrowserTool(url_allowlist=["example.com"])
        tool._connected = True
        tool._page = MagicMock()

        cmd = BrowserCommand(action=BrowserAction.NAVIGATE, url="https://evil.com")
        result = await tool.execute(cmd)
        assert result.success is False
        assert "allowlist" in result.error

    @pytest.mark.asyncio
    async def test_navigate_allowlist_allowed(self) -> None:
        tool = BrowserTool(url_allowlist=["example.com"])
        tool._connected = True
        mock_page = AsyncMock()
        mock_page.url = "https://example.com"
        mock_page.goto = AsyncMock()
        tool._page = mock_page

        cmd = BrowserCommand(action=BrowserAction.NAVIGATE, url="https://example.com/page")
        result = await tool.execute(cmd)
        assert result.success is True
        assert tool.action_count == 1

    @pytest.mark.asyncio
    async def test_evaluate_blocked_in_sandbox(self) -> None:
        tool = BrowserTool(sandbox=True)
        tool._connected = True
        tool._page = AsyncMock()

        cmd = BrowserCommand(action=BrowserAction.EVALUATE, script="document.title")
        result = await tool.execute(cmd)
        assert result.success is False
        assert "sandbox" in result.error

    @pytest.mark.asyncio
    async def test_evaluate_allowed_without_sandbox(self) -> None:
        tool = BrowserTool(sandbox=False)
        tool._connected = True
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value="My Title")
        mock_page.url = "https://example.com"
        tool._page = mock_page

        cmd = BrowserCommand(action=BrowserAction.EVALUATE, script="document.title")
        result = await tool.execute(cmd)
        assert result.success is True
        assert result.data == "My Title"

    @pytest.mark.asyncio
    async def test_click(self) -> None:
        tool = BrowserTool()
        tool._connected = True
        mock_page = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.url = "https://example.com"
        tool._page = mock_page

        cmd = BrowserCommand(action=BrowserAction.CLICK, selector="#button")
        result = await tool.execute(cmd)
        assert result.success is True
        mock_page.click.assert_called_once_with("#button")

    @pytest.mark.asyncio
    async def test_fill(self) -> None:
        tool = BrowserTool()
        tool._connected = True
        mock_page = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.url = "https://example.com"
        tool._page = mock_page

        cmd = BrowserCommand(action=BrowserAction.FILL, selector="#input", value="hello")
        result = await tool.execute(cmd)
        assert result.success is True
        mock_page.fill.assert_called_once_with("#input", "hello")

    @pytest.mark.asyncio
    async def test_get_text(self) -> None:
        tool = BrowserTool()
        tool._connected = True
        mock_page = AsyncMock()
        mock_page.inner_text = AsyncMock(return_value="Page text content")
        mock_page.url = "https://example.com"
        tool._page = mock_page

        cmd = BrowserCommand(action=BrowserAction.GET_TEXT, selector="body")
        result = await tool.execute(cmd)
        assert result.success is True
        assert "Page text content" in result.data

    @pytest.mark.asyncio
    async def test_stop_idempotent(self) -> None:
        tool = BrowserTool()
        await tool.stop()
        assert tool.is_connected is False

    @pytest.mark.asyncio
    async def test_action_error_handling(self) -> None:
        tool = BrowserTool()
        tool._connected = True
        mock_page = AsyncMock()
        mock_page.click = AsyncMock(side_effect=Exception("Element not found"))
        mock_page.url = "https://example.com"
        tool._page = mock_page

        cmd = BrowserCommand(action=BrowserAction.CLICK, selector="#missing")
        result = await tool.execute(cmd)
        assert result.success is False
        assert "Element not found" in result.error
