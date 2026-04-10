"""ZenBot CLI — setup, configuration, and bot management commands."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from zenbot.config import CONFIG_FILE, ZenBotConfig
from zenbot.security.credentials import CredentialStore
from zenbot.utils.logging import get_logger, setup_logging

app = typer.Typer(
    name="zenbot",
    help="ZenBot — A security-first AI agent bot.",
    no_args_is_help=True,
)
credentials_app = typer.Typer(help="Manage credentials securely.")
app.add_typer(credentials_app, name="credentials")

logger = get_logger(__name__)


@app.command()
def init() -> None:
    """Initialize ZenBot with a guided setup wizard."""
    setup_logging()
    typer.echo("🔒 ZenBot Setup Wizard")
    typer.echo("=" * 40)

    # Check for plaintext credential leaks
    store = CredentialStore()
    leaks = store.check_for_plaintext_leaks()
    if leaks:
        typer.echo("\n⚠️  WARNING: Found plaintext credential files:")
        for path in leaks:
            typer.echo(f"  - {path}")
        typer.echo("These should be removed. ZenBot never stores credentials in plain text.")
        typer.echo()

    # Create default config
    if CONFIG_FILE.exists():
        overwrite = typer.confirm("Config already exists. Overwrite?", default=False)
        if not overwrite:
            typer.echo("Keeping existing config.")
            return

    config = ZenBotConfig()

    # Platform setup
    typer.echo("\n📱 Platform Setup")
    if typer.confirm("Enable Telegram?", default=True):
        config.telegram.enabled = True
        token = typer.prompt("Telegram bot token", hide_input=True)
        store.set("telegram_bot_token", token)
        typer.echo("✓ Telegram token stored securely.")

    # LLM setup
    typer.echo("\n🤖 LLM Setup")
    provider = typer.prompt(
        "LLM provider",
        default="claude",
        type=typer.Choice(["claude", "openai", "local"]),
    )
    config.llm.provider = provider

    if provider in ("claude", "openai"):
        api_key = typer.prompt(f"{provider} API key", hide_input=True)
        store.set("llm_api_key", api_key)
        typer.echo(f"✓ {provider} API key stored securely.")

    # Allowlist setup
    typer.echo("\n👤 Allowlist Setup")
    typer.echo("Add at least one admin user (you can add more later).")
    platform = typer.prompt("Your platform", default="telegram")
    user_id = typer.prompt("Your user ID on that platform")
    config.allowlist.append(
        {"platform": platform, "user_id": user_id, "role": "admin"}  # type: ignore[arg-type]
    )
    typer.echo(f"✓ Added {platform}:{user_id} as admin.")

    # Save config
    config.save()
    typer.echo(f"\n✓ Config saved to {CONFIG_FILE}")
    typer.echo("Run `zenbot run` to start the bot.")


_config_option: Path | None = typer.Option(None, "--config", "-c", help="Config file path")


@app.command()
def run(
    config_path: Path | None = _config_option,
) -> None:
    """Start the ZenBot agent."""
    config = ZenBotConfig.load(config_path)
    setup_logging(json_output=config.log_json, level=config.log_level)

    store = CredentialStore()

    # Check for plaintext leaks on every start
    leaks = store.check_for_plaintext_leaks()
    if leaks:
        typer.echo("ERROR: Found plaintext credential files. Refusing to start.")
        typer.echo("Remove these files and use `zenbot credentials set` instead:")
        for path in leaks:
            typer.echo(f"  - {path}")
        raise typer.Exit(1)

    from zenbot.core.bot import ZenBot

    bot = ZenBot(config)

    # Register enabled platforms
    if config.telegram.enabled:
        token = store.get(config.telegram.credential_key)
        if not token:
            typer.echo(
                "ERROR: Telegram token not found. "
                "Run `zenbot credentials set telegram_bot_token`."
            )
            raise typer.Exit(1)
        from zenbot.platforms.telegram import TelegramAdapter
        bot.register_platform(TelegramAdapter(token))

    # Register LLM provider
    if config.llm.provider == "claude":
        api_key = store.get(config.llm.credential_key)
        if not api_key:
            typer.echo("ERROR: Claude API key not found. Run `zenbot credentials set llm_api_key`.")
            raise typer.Exit(1)
        from zenbot.llm.claude import ClaudeProvider
        bot.set_llm(ClaudeProvider(api_key, config.llm.model))

    typer.echo("Starting ZenBot...")
    asyncio.run(bot.start())


@credentials_app.command("set")
def credentials_set(
    key: str = typer.Argument(help="Credential key (e.g., telegram_bot_token, llm_api_key)"),
) -> None:
    """Store a credential securely in the OS keychain."""
    setup_logging()
    value = typer.prompt(f"Value for '{key}'", hide_input=True)
    store = CredentialStore()
    store.set(key, value)
    typer.echo(f"✓ Credential '{key}' stored securely.")


@credentials_app.command("delete")
def credentials_delete(
    key: str = typer.Argument(help="Credential key to delete"),
) -> None:
    """Remove a credential from the store."""
    setup_logging()
    store = CredentialStore()
    store.delete(key)
    typer.echo(f"✓ Credential '{key}' deleted.")


@credentials_app.command("check")
def credentials_check(
    key: str = typer.Argument(help="Credential key to check"),
) -> None:
    """Check if a credential exists (without revealing its value)."""
    setup_logging()
    store = CredentialStore()
    if store.exists(key):
        typer.echo(f"✓ Credential '{key}' exists.")
    else:
        typer.echo(f"✗ Credential '{key}' not found.")
