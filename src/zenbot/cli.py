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

    if typer.confirm("Enable Discord?", default=False):
        config.discord.enabled = True
        token = typer.prompt("Discord bot token", hide_input=True)
        store.set("discord_bot_token", token)
        typer.echo("✓ Discord token stored securely.")

    if typer.confirm("Enable WhatsApp?", default=False):
        config.whatsapp.enabled = True
        token = typer.prompt("WhatsApp access token", hide_input=True)
        store.set("whatsapp_access_token", token)
        phone_id = typer.prompt("WhatsApp phone number ID")
        store.set("whatsapp_phone_number_id", phone_id)
        typer.echo("✓ WhatsApp credentials stored securely.")

    if typer.confirm("Enable Signal?", default=False):
        config.signal.enabled = True
        account = typer.prompt("Signal account phone number (e.g., +1234567890)")
        store.set("signal_account", account)
        typer.echo("✓ Signal account stored securely.")

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

    if config.discord.enabled:
        token = store.get(config.discord.credential_key)
        if not token:
            typer.echo(
                "ERROR: Discord token not found. "
                "Run `zenbot credentials set discord_bot_token`."
            )
            raise typer.Exit(1)
        from zenbot.platforms.discord import DiscordAdapter
        bot.register_platform(DiscordAdapter(token))

    if config.whatsapp.enabled:
        access_token = store.get("whatsapp_access_token")
        phone_id = store.get("whatsapp_phone_number_id")
        if not access_token or not phone_id:
            typer.echo(
                "ERROR: WhatsApp credentials not found. "
                "Run `zenbot credentials set whatsapp_access_token`."
            )
            raise typer.Exit(1)
        from zenbot.platforms.whatsapp import WhatsAppAdapter
        bot.register_platform(
            WhatsAppAdapter(
                access_token=access_token,
                phone_number_id=phone_id,
            )
        )

    if config.signal.enabled:
        account = store.get("signal_account")
        if not account:
            typer.echo(
                "ERROR: Signal account not found. "
                "Run `zenbot credentials set signal_account`."
            )
            raise typer.Exit(1)
        from zenbot.platforms.signal import SignalAdapter
        bot.register_platform(SignalAdapter(account=account))

    # Register LLM provider with prompt guard
    from zenbot.llm.prompt_guard import GuardedLLMProvider

    llm_provider = None

    if config.llm.provider == "claude":
        api_key = store.get(config.llm.credential_key)
        if not api_key:
            typer.echo(
                "ERROR: Claude API key not found. "
                "Run `zenbot credentials set llm_api_key`."
            )
            raise typer.Exit(1)
        from zenbot.llm.claude import ClaudeProvider
        llm_provider = ClaudeProvider(api_key, config.llm.model)

    elif config.llm.provider == "openai":
        api_key = store.get(config.llm.credential_key)
        if not api_key:
            typer.echo(
                "ERROR: OpenAI API key not found. "
                "Run `zenbot credentials set llm_api_key`."
            )
            raise typer.Exit(1)
        from zenbot.llm.openai_gpt import OpenAIProvider
        llm_provider = OpenAIProvider(api_key, config.llm.model)

    elif config.llm.provider == "local":
        from zenbot.llm.local import LocalProvider
        llm_provider = LocalProvider(default_model=config.llm.model)

    if llm_provider is None:
        typer.echo(f"ERROR: Unknown LLM provider '{config.llm.provider}'.")
        raise typer.Exit(1)

    # Wrap with prompt injection guard
    bot.set_llm(GuardedLLMProvider(llm_provider))

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
