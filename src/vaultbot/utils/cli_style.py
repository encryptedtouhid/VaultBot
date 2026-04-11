"""CLI styling helpers — colored, consistent output across all commands."""

from __future__ import annotations

import typer


def _get_version() -> str:
    from vaultbot import __version__

    return __version__


def success(msg: str) -> None:
    """Green text for successful operations."""
    typer.echo(typer.style(f"  ✓ {msg}", fg=typer.colors.GREEN, bold=True))


def error(msg: str) -> None:
    """Red text for errors."""
    typer.echo(typer.style(f"  ✗ {msg}", fg=typer.colors.RED, bold=True))


def warning(msg: str) -> None:
    """Yellow text for warnings."""
    typer.echo(typer.style(f"  ⚠ {msg}", fg=typer.colors.YELLOW, bold=True))


def info(msg: str) -> None:
    """Cyan text for informational messages."""
    typer.echo(typer.style(f"  ℹ {msg}", fg=typer.colors.CYAN))


def hint(msg: str) -> None:
    """Dim text for hints and suggestions."""
    typer.echo(typer.style(f"    → {msg}", fg=typer.colors.BRIGHT_BLACK))


def header(msg: str) -> None:
    """Bold bright text for section headers."""
    typer.echo()
    typer.echo(typer.style(f"  {msg}", fg=typer.colors.BRIGHT_WHITE, bold=True))


def banner() -> None:
    """Display the V.A.U.L.T. BOT ASCII banner."""
    art = typer.style(
        r"""
 ██╗   ██       ███████╗       ██╗   ██╗     ██╗         ████████╗
 ██║   ██║      ██╔══██╗       ██║   ██║     ██║         ╚══██╔══╝
 ██║   ██║      ███████║       ██║   ██║     ██║            ██║
 ╚██╗ ██╔╝      ██╔══██║       ██║   ██║     ██║            ██║
  ╚████╔╝  ██╗  ██║  ██║  ██╗  ╚██████╔╝ ██╗ ███████╗  ██╗  ██║  ██╗
   ╚═══╝   ╚═╝  ╚═╝  ╚═╝  ╚═╝   ╚═════╝  ╚═╝ ╚══════╝  ╚═╝  ╚═╝  ╚═╝  BOT v"""
        + _get_version()
        + r"""

 Security-first, source-available autonomous AI agent
""",
        fg=typer.colors.BRIGHT_CYAN,
        bold=True,
    )
    typer.echo(art)


def section(icon: str, title: str) -> None:
    """Colored section separator with icon."""
    typer.echo()
    typer.echo(
        typer.style(f"  {icon} ", fg=typer.colors.BRIGHT_YELLOW)
        + typer.style(title, fg=typer.colors.BRIGHT_WHITE, bold=True)
    )
    typer.echo(typer.style("  " + "─" * 40, fg=typer.colors.BRIGHT_BLACK))


def key_value(key: str, value: str) -> None:
    """Display a key-value pair with colors."""
    typer.echo(
        typer.style(f"    {key}: ", fg=typer.colors.BRIGHT_BLACK)
        + typer.style(value, fg=typer.colors.WHITE)
    )


def plugin_entry(
    name: str, version: str, status: str, description: str
) -> None:
    """Display a plugin entry with colored status."""
    status_color = typer.colors.GREEN if status == "enabled" else typer.colors.RED
    typer.echo(
        typer.style(f"  • {name}", fg=typer.colors.BRIGHT_WHITE, bold=True)
        + typer.style(f" v{version} ", fg=typer.colors.BRIGHT_BLACK)
        + typer.style(f"[{status}]", fg=status_color)
        + typer.style(f" — {description}", fg=typer.colors.WHITE)
    )


def command_hint(cmd: str) -> None:
    """Show a command suggestion in styled format."""
    typer.echo(
        typer.style("    Run: ", fg=typer.colors.BRIGHT_BLACK)
        + typer.style(cmd, fg=typer.colors.BRIGHT_MAGENTA, bold=True)
    )


def divider() -> None:
    """Thin divider line."""
    typer.echo(typer.style("  " + "─" * 40, fg=typer.colors.BRIGHT_BLACK))


def box(lines: list[str], title: str = "", width: int = 50) -> None:
    """Display content inside a styled box."""
    top = f"  ╭{'─' * (width - 2)}╮"
    bot = f"  ╰{'─' * (width - 2)}╯"

    if title:
        padded_title = f" {title} "
        top = f"  ╭─{padded_title}{'─' * (width - len(padded_title) - 3)}╮"

    typer.echo(typer.style(top, fg=typer.colors.BRIGHT_BLACK))
    for line in lines:
        padding = width - 4 - len(_strip_ansi(line))
        if padding < 0:
            padding = 0
        typer.echo(
            typer.style("  │ ", fg=typer.colors.BRIGHT_BLACK)
            + line
            + " " * padding
            + typer.style(" │", fg=typer.colors.BRIGHT_BLACK)
        )
    typer.echo(typer.style(bot, fg=typer.colors.BRIGHT_BLACK))


def status_line(label: str, value: str, ok: bool = True) -> str:
    """Build a colored status line for use inside a box."""
    icon = typer.style("●", fg=typer.colors.GREEN if ok else typer.colors.RED)
    lbl = typer.style(f"{label}: ", fg=typer.colors.BRIGHT_BLACK)
    val = typer.style(value, fg=typer.colors.WHITE, bold=True)
    return f"{icon} {lbl}{val}"


def startup_summary(
    platforms: list[str],
    llm_provider: str,
    security: list[str],
    version: str = "",
) -> None:
    """Display a clean startup summary panel."""
    ver = version or _get_version()

    banner()

    lines = [
        status_line("Version", f"v{ver}"),
        status_line("Platforms", ", ".join(platforms) if platforms else "none", bool(platforms)),
        status_line("LLM", llm_provider),
        "",
    ]
    for sec in security:
        lines.append(
            typer.style("  ✓ ", fg=typer.colors.GREEN)
            + typer.style(sec, fg=typer.colors.BRIGHT_BLACK)
        )

    box(lines, title="V.A.U.L.T. BOT", width=56)
    typer.echo()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes for length calculation."""
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)
