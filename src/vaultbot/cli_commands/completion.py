"""Shell completion generation for bash, zsh, and fish."""

from __future__ import annotations


def generate_bash_completion(commands: list[str]) -> str:
    """Generate bash completion script."""
    cmds = " ".join(commands)
    return f"""_vaultbot_complete() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    COMPREPLY=($(compgen -W "{cmds}" -- "$cur"))
}}
complete -F _vaultbot_complete vaultbot
"""


def generate_zsh_completion(commands: list[str]) -> str:
    """Generate zsh completion script."""
    lines = ["#compdef vaultbot", "_vaultbot() {", "    local -a commands", "    commands=("]
    for cmd in commands:
        lines.append(f"        '{cmd}:VaultBot {cmd} command'")
    lines.extend(["    )", "    _describe 'command' commands", "}", "_vaultbot"])
    return "\n".join(lines) + "\n"


def generate_fish_completion(commands: list[str]) -> str:
    """Generate fish completion script."""
    lines = []
    for cmd in commands:
        lines.append(f"complete -c vaultbot -n '__fish_use_subcommand' -a '{cmd}'")
    return "\n".join(lines) + "\n"
