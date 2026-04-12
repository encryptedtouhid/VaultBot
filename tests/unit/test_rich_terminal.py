"""Unit tests for rich interactive terminal."""

from __future__ import annotations

from vaultbot.tui.interactive import InteractiveTerminal, TerminalConfig
from vaultbot.tui.themes import THEMES, get_theme


class TestInteractiveTerminal:
    def test_add_message(self) -> None:
        term = InteractiveTerminal()
        entry = term.add_message("user", "hello")
        assert entry.role == "user"
        assert len(term.history) == 1

    def test_markdown_rendering(self) -> None:
        term = InteractiveTerminal()
        entry = term.add_message("assistant", "# Title")
        assert "\033[1m" in entry.rendered

    def test_no_markdown(self) -> None:
        config = TerminalConfig(markdown_rendering=False)
        term = InteractiveTerminal(config)
        entry = term.add_message("user", "# Title")
        assert entry.rendered == "# Title"

    def test_input_history(self) -> None:
        term = InteractiveTerminal()
        term.add_input("hello")
        term.add_input("world")
        assert len(term.get_input_history()) == 2

    def test_clear(self) -> None:
        term = InteractiveTerminal()
        term.add_message("user", "hi")
        term.clear()
        assert len(term.history) == 0

    def test_max_history(self) -> None:
        config = TerminalConfig(max_history=2)
        term = InteractiveTerminal(config)
        term.add_message("user", "1")
        term.add_message("user", "2")
        term.add_message("user", "3")
        assert len(term.history) == 2


class TestThemes:
    def test_get_default_theme(self) -> None:
        theme = get_theme("default")
        assert theme.name == "default"

    def test_get_unknown_theme_returns_default(self) -> None:
        theme = get_theme("nonexistent")
        assert theme.name == "default"

    def test_minimal_theme_no_colors(self) -> None:
        theme = get_theme("minimal")
        assert theme.user_color == ""

    def test_themes_dict(self) -> None:
        assert len(THEMES) >= 3
