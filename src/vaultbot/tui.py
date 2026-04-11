"""Terminal UI components for interactive VaultBot sessions.

Provides rich terminal output using ANSI escape codes for colorized
chat interface, status panels, and interactive prompts.  No heavy
TUI library required — works with any terminal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class Color(str, Enum):
    """ANSI color codes."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"


@dataclass
class PlatformStatus:
    """Status of a connected platform."""

    name: str
    connected: bool
    sessions: int = 0
    last_message: str = ""


class TerminalUI:
    """Rich terminal UI for VaultBot interactive mode."""

    def __init__(self, *, color: bool = True) -> None:
        self._color = color

    def _c(self, color: Color, text: str) -> str:
        """Apply color to text."""
        if not self._color:
            return text
        return f"{color.value}{text}{Color.RESET.value}"

    def banner(self) -> str:
        """Return the VaultBot startup banner."""
        lines = [
            self._c(Color.CYAN, "╔══════════════════════════════════╗"),
            self._c(Color.CYAN, "║")
            + self._c(Color.BOLD, "  V.A.U.L.T. BOT  ")
            + self._c(Color.CYAN, "              ║"),
            self._c(Color.CYAN, "║")
            + self._c(Color.DIM, "  Security-first AI agent")
            + self._c(Color.CYAN, "        ║"),
            self._c(Color.CYAN, "╚══════════════════════════════════╝"),
        ]
        return "\n".join(lines)

    def format_user_message(self, sender: str, text: str, platform: str = "") -> str:
        """Format an incoming user message for display."""
        platform_tag = f"[{platform}] " if platform else ""
        header = self._c(Color.GREEN, f"{platform_tag}{sender}")
        return f"{header}: {text}"

    def format_bot_response(self, text: str) -> str:
        """Format a bot response for display."""
        header = self._c(Color.BLUE, "VaultBot")
        return f"{header}: {text}"

    def format_error(self, error: str) -> str:
        """Format an error message."""
        return self._c(Color.RED, f"Error: {error}")

    def format_warning(self, warning: str) -> str:
        """Format a warning message."""
        return self._c(Color.YELLOW, f"Warning: {warning}")

    def format_info(self, info: str) -> str:
        """Format an info message."""
        return self._c(Color.GRAY, f"Info: {info}")

    def format_status_panel(self, platforms: list[PlatformStatus]) -> str:
        """Format a status panel showing connected platforms."""
        lines = [
            self._c(Color.BOLD, "Platform Status"),
            self._c(Color.DIM, "─" * 40),
        ]
        for p in platforms:
            icon = self._c(Color.GREEN, "●") if p.connected else self._c(Color.RED, "○")
            name = self._c(Color.WHITE, p.name.ljust(15))
            status = "connected" if p.connected else "disconnected"
            sessions = f"({p.sessions} sessions)" if p.sessions else ""
            lines.append(f"  {icon} {name} {status} {sessions}")
        lines.append(self._c(Color.DIM, "─" * 40))
        return "\n".join(lines)

    def format_help(self) -> str:
        """Format help text."""
        commands = [
            ("/help", "Show this help"),
            ("/status", "Show platform status"),
            ("/clear", "Clear conversation"),
            ("/model <name>", "Switch LLM model"),
            ("/quit", "Exit VaultBot"),
        ]
        lines = [self._c(Color.BOLD, "Commands:")]
        for cmd, desc in commands:
            lines.append(f"  {self._c(Color.CYAN, cmd.ljust(20))} {desc}")
        return "\n".join(lines)

    def prompt(self) -> str:
        """Return the input prompt string."""
        return self._c(Color.GREEN, "you> ")

    def thinking_indicator(self) -> str:
        """Return a thinking/processing indicator."""
        return self._c(Color.DIM, "⟳ Thinking...")

    def format_token_usage(self, input_tokens: int, output_tokens: int, model: str = "") -> str:
        """Format token usage info."""
        total = input_tokens + output_tokens
        model_str = f" ({model})" if model else ""
        return self._c(Color.GRAY, f"[{total} tokens{model_str}]")
