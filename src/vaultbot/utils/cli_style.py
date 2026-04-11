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
