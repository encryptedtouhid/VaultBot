"""Terminal color themes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    user_color: str = "\033[36m"
    assistant_color: str = "\033[32m"
    system_color: str = "\033[33m"
    error_color: str = "\033[31m"
    reset: str = "\033[0m"
    bold: str = "\033[1m"


THEMES: dict[str, Theme] = {
    "default": Theme(name="default"),
    "dark": Theme(
        name="dark",
        user_color="\033[94m",
        assistant_color="\033[92m",
    ),
    "light": Theme(
        name="light",
        user_color="\033[34m",
        assistant_color="\033[32m",
    ),
    "minimal": Theme(
        name="minimal",
        user_color="",
        assistant_color="",
        system_color="",
        error_color="",
        reset="",
        bold="",
    ),
}


def get_theme(name: str) -> Theme:
    return THEMES.get(name, THEMES["default"])
