"""ZenBot CLI — setup, configuration, and bot management commands."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from zenbot.config import CONFIG_FILE, ZenBotConfig
from zenbot.security.credentials import CredentialStore
from zenbot.utils import cli_style as style
from zenbot.utils.logging import get_logger, setup_logging

app = typer.Typer(
    name="zenbot",
    help="ZenBot — A security-first AI agent bot.",
    no_args_is_help=True,
)
credentials_app = typer.Typer(help="Manage credentials securely.")
app.add_typer(credentials_app, name="credentials")
plugin_app = typer.Typer(help="Manage plugins.")
app.add_typer(plugin_app, name="plugin")

logger = get_logger(__name__)


@app.command()
def init() -> None:
    """Initialize ZenBot with a guided setup wizard."""
    setup_logging()
    style.banner()

    style.section("🔒", "Security Check")

    # Check for plaintext credential leaks
    store = CredentialStore()
    leaks = store.check_for_plaintext_leaks()
    if leaks:
        style.warning("Found plaintext credential files:")
        for path in leaks:
            style.hint(path)
        style.info(
            "These should be removed. ZenBot never stores credentials in plain text."
        )
    else:
        style.success("No plaintext credential files found.")

    # Create default config
    if CONFIG_FILE.exists():
        overwrite = typer.confirm(
            typer.style(
                "  Config already exists. Overwrite?",
                fg=typer.colors.YELLOW,
            ),
            default=False,
        )
        if not overwrite:
            style.info("Keeping existing config.")
            return

    config = ZenBotConfig()

    # Platform setup
    style.section("📱", "Platform Setup")
    if typer.confirm("  Enable Telegram?", default=True):
        config.telegram.enabled = True
        token = typer.prompt(
            typer.style("  Telegram bot token", fg=typer.colors.CYAN),
            hide_input=True,
        )
        store.set("telegram_bot_token", token)
        style.success("Telegram token stored securely.")

    if typer.confirm("  Enable Discord?", default=False):
        config.discord.enabled = True
        token = typer.prompt(
            typer.style("  Discord bot token", fg=typer.colors.CYAN),
            hide_input=True,
        )
        store.set("discord_bot_token", token)
        style.success("Discord token stored securely.")

    if typer.confirm("  Enable WhatsApp?", default=False):
        config.whatsapp.enabled = True
        token = typer.prompt(
            typer.style("  WhatsApp access token", fg=typer.colors.CYAN),
            hide_input=True,
        )
        store.set("whatsapp_access_token", token)
        phone_id = typer.prompt(
            typer.style("  WhatsApp phone number ID", fg=typer.colors.CYAN),
        )
        store.set("whatsapp_phone_number_id", phone_id)
        style.success("WhatsApp credentials stored securely.")

    if typer.confirm("  Enable Signal?", default=False):
        config.signal.enabled = True
        account = typer.prompt(
            typer.style(
                "  Signal account phone number (e.g., +1234567890)",
                fg=typer.colors.CYAN,
            ),
        )
        store.set("signal_account", account)
        style.success("Signal account stored securely.")

    # LLM setup
    style.section("🤖", "LLM Setup")
    provider = typer.prompt(
        typer.style("  LLM provider", fg=typer.colors.CYAN),
        default="claude",
        type=typer.Choice(["claude", "openai", "local"]),
    )
    config.llm.provider = provider

    if provider in ("claude", "openai"):
        api_key = typer.prompt(
            typer.style(f"  {provider} API key", fg=typer.colors.CYAN),
            hide_input=True,
        )
        store.set("llm_api_key", api_key)
        style.success(f"{provider.capitalize()} API key stored securely.")

    if provider == "local":
        style.info("Local mode — no API key needed.")
        style.hint("Make sure Ollama or a compatible server is running.")

    # Allowlist setup
    style.section("👤", "Allowlist Setup")
    style.info("Add at least one admin user (you can add more later).")
    platform = typer.prompt(
        typer.style("  Your platform", fg=typer.colors.CYAN),
        default="telegram",
    )
    user_id = typer.prompt(
        typer.style("  Your user ID on that platform", fg=typer.colors.CYAN),
    )
    config.allowlist.append(
        {"platform": platform, "user_id": user_id, "role": "admin"}  # type: ignore[arg-type]
    )
    style.success(f"Added {platform}:{user_id} as admin.")

    # Save config
    config.save()

    style.section("🎉", "Setup Complete")
    style.success(f"Config saved to {CONFIG_FILE}")
    style.command_hint("zenbot run")


_config_option: Path | None = typer.Option(
    None, "--config", "-c", help="Config file path"
)


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
        style.error("Found plaintext credential files. Refusing to start.")
        style.hint("Remove these files and use `zenbot credentials set` instead:")
        for path in leaks:
            style.hint(path)
        raise typer.Exit(1)

    from zenbot.core.bot import ZenBot

    bot = ZenBot(config)

    # Register enabled platforms
    if config.telegram.enabled:
        token = store.get(config.telegram.credential_key)
        if not token:
            style.error("Telegram token not found.")
            style.command_hint("zenbot credentials set telegram_bot_token")
            raise typer.Exit(1)
        from zenbot.platforms.telegram import TelegramAdapter

        bot.register_platform(TelegramAdapter(token))
        style.success("Telegram adapter registered.")

    if config.discord.enabled:
        token = store.get(config.discord.credential_key)
        if not token:
            style.error("Discord token not found.")
            style.command_hint("zenbot credentials set discord_bot_token")
            raise typer.Exit(1)
        from zenbot.platforms.discord import DiscordAdapter

        bot.register_platform(DiscordAdapter(token))
        style.success("Discord adapter registered.")

    if config.whatsapp.enabled:
        access_token = store.get("whatsapp_access_token")
        phone_id = store.get("whatsapp_phone_number_id")
        if not access_token or not phone_id:
            style.error("WhatsApp credentials not found.")
            style.command_hint("zenbot credentials set whatsapp_access_token")
            raise typer.Exit(1)
        from zenbot.platforms.whatsapp import WhatsAppAdapter

        bot.register_platform(
            WhatsAppAdapter(access_token=access_token, phone_number_id=phone_id)
        )
        style.success("WhatsApp adapter registered.")

    if config.signal.enabled:
        account = store.get("signal_account")
        if not account:
            style.error("Signal account not found.")
            style.command_hint("zenbot credentials set signal_account")
            raise typer.Exit(1)
        from zenbot.platforms.signal import SignalAdapter

        bot.register_platform(SignalAdapter(account=account))
        style.success("Signal adapter registered.")

    # Register LLM provider with prompt guard
    from zenbot.llm.prompt_guard import GuardedLLMProvider

    llm_provider = None

    if config.llm.provider == "claude":
        api_key = store.get(config.llm.credential_key)
        if not api_key:
            style.error("Claude API key not found.")
            style.command_hint("zenbot credentials set llm_api_key")
            raise typer.Exit(1)
        from zenbot.llm.claude import ClaudeProvider

        llm_provider = ClaudeProvider(api_key, config.llm.model)

    elif config.llm.provider == "openai":
        api_key = store.get(config.llm.credential_key)
        if not api_key:
            style.error("OpenAI API key not found.")
            style.command_hint("zenbot credentials set llm_api_key")
            raise typer.Exit(1)
        from zenbot.llm.openai_gpt import OpenAIProvider

        llm_provider = OpenAIProvider(api_key, config.llm.model)

    elif config.llm.provider == "local":
        from zenbot.llm.local import LocalProvider

        llm_provider = LocalProvider(default_model=config.llm.model)

    if llm_provider is None:
        style.error(f"Unknown LLM provider '{config.llm.provider}'.")
        raise typer.Exit(1)

    # Wrap with prompt injection guard
    bot.set_llm(GuardedLLMProvider(llm_provider))
    style.success(f"LLM provider '{config.llm.provider}' ready (with prompt guard).")

    style.divider()
    style.header("🚀 Starting ZenBot...")
    style.divider()
    asyncio.run(bot.start())


# --- Credentials commands ---


@credentials_app.command("set")
def credentials_set(
    key: str = typer.Argument(
        help="Credential key (e.g., telegram_bot_token, llm_api_key)"
    ),
) -> None:
    """Store a credential securely in the OS keychain."""
    setup_logging()
    value = typer.prompt(
        typer.style(f"  Value for '{key}'", fg=typer.colors.CYAN),
        hide_input=True,
    )
    store = CredentialStore()
    store.set(key, value)
    style.success(f"Credential '{key}' stored securely.")


@credentials_app.command("delete")
def credentials_delete(
    key: str = typer.Argument(help="Credential key to delete"),
) -> None:
    """Remove a credential from the store."""
    setup_logging()
    store = CredentialStore()
    store.delete(key)
    style.success(f"Credential '{key}' deleted.")


@credentials_app.command("check")
def credentials_check(
    key: str = typer.Argument(help="Credential key to check"),
) -> None:
    """Check if a credential exists (without revealing its value)."""
    setup_logging()
    store = CredentialStore()
    if store.exists(key):
        style.success(f"Credential '{key}' exists.")
    else:
        style.error(f"Credential '{key}' not found.")


# --- Plugin commands ---


@plugin_app.command("install")
def plugin_install(
    plugin_dir: Path = typer.Argument(help="Path to the plugin directory"),
) -> None:
    """Install a signed plugin from a directory."""
    setup_logging()
    from zenbot.plugins.loader import PluginLoader, PluginLoadError
    from zenbot.plugins.registry import PluginRegistry
    from zenbot.plugins.signer import PluginVerifier
    from zenbot.security.audit import AuditLogger

    registry = PluginRegistry()
    verifier = PluginVerifier()
    audit = AuditLogger()
    loader = PluginLoader(registry, verifier, audit)

    try:
        entry = loader.load_plugin(plugin_dir)
        style.success(
            f"Plugin '{entry.manifest.name}' "
            f"v{entry.manifest.version} installed."
        )
    except PluginLoadError as e:
        style.error(str(e))
        raise typer.Exit(1) from e


@plugin_app.command("list")
def plugin_list() -> None:
    """List all installed plugins."""
    setup_logging()
    from zenbot.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    plugins = registry.list_plugins()

    if not plugins:
        style.info("No plugins installed.")
        style.command_hint("zenbot plugin install <plugin-dir>")
        return

    style.header("Installed Plugins")
    style.divider()
    for entry in plugins:
        status = "enabled" if entry.enabled else "disabled"
        style.plugin_entry(
            entry.manifest.name,
            entry.manifest.version,
            status,
            entry.manifest.description,
        )
    style.divider()


@plugin_app.command("enable")
def plugin_enable(
    name: str = typer.Argument(help="Plugin name to enable"),
) -> None:
    """Enable a disabled plugin."""
    setup_logging()
    from zenbot.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    if registry.enable(name):
        style.success(f"Plugin '{name}' enabled.")
    else:
        style.error(f"Plugin '{name}' not found.")
        raise typer.Exit(1)


@plugin_app.command("disable")
def plugin_disable(
    name: str = typer.Argument(help="Plugin name to disable"),
) -> None:
    """Disable a plugin without uninstalling it."""
    setup_logging()
    from zenbot.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    if registry.disable(name):
        style.success(f"Plugin '{name}' disabled.")
    else:
        style.error(f"Plugin '{name}' not found.")
        raise typer.Exit(1)


@plugin_app.command("uninstall")
def plugin_uninstall(
    name: str = typer.Argument(help="Plugin name to uninstall"),
) -> None:
    """Remove a plugin from the registry."""
    setup_logging()
    from zenbot.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    entry = registry.unregister(name)
    if entry:
        style.success(f"Plugin '{name}' uninstalled.")
    else:
        style.error(f"Plugin '{name}' not found.")
        raise typer.Exit(1)


@plugin_app.command("sign")
def plugin_sign(
    plugin_dir: Path = typer.Argument(help="Path to the plugin directory"),
    key_file: Path = typer.Argument(
        help="Path to Ed25519 private key (PEM)"
    ),
) -> None:
    """Sign a plugin with an Ed25519 private key."""
    setup_logging()
    import json

    from zenbot.plugins.signer import PluginSigner

    if not key_file.exists():
        style.error(f"Key file not found: {key_file}")
        raise typer.Exit(1)

    manifest_path = plugin_dir / "zenbot_plugin.json"
    if not manifest_path.exists():
        style.error("No zenbot_plugin.json found in plugin directory.")
        raise typer.Exit(1)

    manifest_data = json.loads(manifest_path.read_text())
    signer = PluginSigner.from_key_bytes(key_file.read_bytes())
    sig = signer.sign_plugin(
        manifest_data["name"],
        manifest_data["version"],
        plugin_dir,
    )
    style.success(
        f"Plugin '{sig.plugin_name}' v{sig.plugin_version} signed."
    )
    style.key_value("Public key", sig.signer_public_key.hex()[:32] + "...")


@plugin_app.command("keygen")
def plugin_keygen(
    output_dir: Path = typer.Argument(
        help="Directory to write the keypair files"
    ),
) -> None:
    """Generate an Ed25519 keypair for plugin signing."""
    setup_logging()
    from zenbot.plugins.signer import PluginSigner

    output_dir.mkdir(parents=True, exist_ok=True)

    signer = PluginSigner.generate()
    private_path = output_dir / "zenbot_signing_key.pem"
    public_path = output_dir / "zenbot_signing_key.pub"

    private_path.write_bytes(signer.private_key_pem)
    private_path.chmod(0o600)
    public_path.write_text(signer.public_key_bytes.hex())
    public_path.chmod(0o644)

    style.success("Keypair generated:")
    style.key_value("Private key", str(private_path))
    style.key_value("Public key", str(public_path))
    style.hint(
        f"To trust this key: copy {public_path.name} to ~/.zenbot/trust_store/"
    )
