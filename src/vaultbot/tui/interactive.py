"""Rich interactive terminal mode for agent chat."""

from __future__ import annotations

from dataclasses import dataclass

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TerminalConfig:
    theme: str = "default"
    syntax_highlighting: bool = True
    markdown_rendering: bool = True
    max_history: int = 1000
    prompt: str = "> "


@dataclass(slots=True)
class ChatEntry:
    role: str
    content: str
    rendered: str = ""


class InteractiveTerminal:
    """Rich interactive terminal for chat with syntax highlighting and markdown."""

    def __init__(self, config: TerminalConfig | None = None) -> None:
        self._config = config or TerminalConfig()
        self._history: list[ChatEntry] = []
        self._input_history: list[str] = []

    @property
    def config(self) -> TerminalConfig:
        return self._config

    @property
    def history(self) -> list[ChatEntry]:
        return list(self._history)

    def add_message(self, role: str, content: str) -> ChatEntry:
        rendered = self._render(content) if self._config.markdown_rendering else content
        entry = ChatEntry(role=role, content=content, rendered=rendered)
        self._history.append(entry)
        if len(self._history) > self._config.max_history:
            self._history.pop(0)
        return entry

    def add_input(self, text: str) -> None:
        self._input_history.append(text)

    def get_input_history(self) -> list[str]:
        return list(self._input_history)

    def clear(self) -> None:
        self._history.clear()

    @staticmethod
    def _render(text: str) -> str:
        """Basic markdown rendering for terminal."""
        lines = []
        for line in text.split("\n"):
            if line.startswith("# "):
                lines.append(f"\033[1m{line[2:]}\033[0m")
            elif line.startswith("**") and line.endswith("**"):
                lines.append(f"\033[1m{line[2:-2]}\033[0m")
            elif line.startswith("```"):
                lines.append(line)
            else:
                lines.append(line)
        return "\n".join(lines)
