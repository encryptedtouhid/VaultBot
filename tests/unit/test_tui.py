"""Unit tests for terminal UI."""

from __future__ import annotations

from vaultbot.tui import Color, PlatformStatus, TerminalUI


class TestTerminalUI:
    def test_banner(self) -> None:
        ui = TerminalUI()
        banner = ui.banner()
        assert "V.A.U.L.T." in banner

    def test_banner_no_color(self) -> None:
        ui = TerminalUI(color=False)
        banner = ui.banner()
        assert "\033[" not in banner

    def test_format_user_message(self) -> None:
        ui = TerminalUI(color=False)
        msg = ui.format_user_message("alice", "hello", "telegram")
        assert "alice" in msg
        assert "hello" in msg
        assert "[telegram]" in msg

    def test_format_user_message_no_platform(self) -> None:
        ui = TerminalUI(color=False)
        msg = ui.format_user_message("bob", "hi")
        assert "bob" in msg
        assert "[" not in msg

    def test_format_bot_response(self) -> None:
        ui = TerminalUI(color=False)
        msg = ui.format_bot_response("I can help with that")
        assert "VaultBot" in msg
        assert "I can help" in msg

    def test_format_error(self) -> None:
        ui = TerminalUI(color=False)
        msg = ui.format_error("connection failed")
        assert "Error" in msg
        assert "connection failed" in msg

    def test_format_warning(self) -> None:
        ui = TerminalUI(color=False)
        msg = ui.format_warning("rate limited")
        assert "Warning" in msg

    def test_format_info(self) -> None:
        ui = TerminalUI(color=False)
        msg = ui.format_info("connected")
        assert "Info" in msg

    def test_format_status_panel(self) -> None:
        ui = TerminalUI(color=False)
        platforms = [
            PlatformStatus(name="telegram", connected=True, sessions=3),
            PlatformStatus(name="discord", connected=False),
        ]
        panel = ui.format_status_panel(platforms)
        assert "telegram" in panel
        assert "discord" in panel
        assert "3 sessions" in panel

    def test_format_help(self) -> None:
        ui = TerminalUI(color=False)
        help_text = ui.format_help()
        assert "/help" in help_text
        assert "/quit" in help_text

    def test_prompt(self) -> None:
        ui = TerminalUI(color=False)
        assert "you>" in ui.prompt()

    def test_thinking_indicator(self) -> None:
        ui = TerminalUI(color=False)
        assert "Thinking" in ui.thinking_indicator()

    def test_format_token_usage(self) -> None:
        ui = TerminalUI(color=False)
        usage = ui.format_token_usage(100, 50, "claude")
        assert "150 tokens" in usage
        assert "claude" in usage

    def test_format_token_usage_no_model(self) -> None:
        ui = TerminalUI(color=False)
        usage = ui.format_token_usage(10, 5)
        assert "15 tokens" in usage

    def test_color_application(self) -> None:
        ui = TerminalUI(color=True)
        colored = ui._c(Color.RED, "test")
        assert "\033[31m" in colored
        assert "test" in colored

    def test_no_color_mode(self) -> None:
        ui = TerminalUI(color=False)
        plain = ui._c(Color.RED, "test")
        assert "\033[" not in plain
        assert plain == "test"
