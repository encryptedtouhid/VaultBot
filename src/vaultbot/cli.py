"""VaultBot CLI — setup, configuration, and bot management commands."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
import typer

from vaultbot.config import CONFIG_FILE, VaultBotConfig
from vaultbot.security.credentials import CredentialStore
from vaultbot.utils import cli_style as style
from vaultbot.utils.logging import get_logger, setup_logging

app = typer.Typer(
    name="vaultbot",
    help="V.A.U.L.T. BOT — Verified Autonomous Utility & Logical Taskrunner",
    no_args_is_help=True,
)
credentials_app = typer.Typer(help="Manage credentials securely.")
app.add_typer(credentials_app, name="credentials")
plugin_app = typer.Typer(help="Manage plugins.")
app.add_typer(plugin_app, name="plugin")
marketplace_app = typer.Typer(help="Browse and install plugins from the marketplace.")
app.add_typer(marketplace_app, name="marketplace")
team_app = typer.Typer(help="Manage teams and multi-user access.")
app.add_typer(team_app, name="team")
sdk_app = typer.Typer(help="Plugin development tools.")
app.add_typer(sdk_app, name="sdk")

logger = get_logger(__name__)


@app.command()
def init(
    # Platform flags — pass token directly, no prompts
    telegram: str = typer.Option("", help="Telegram bot token"),
    discord: str = typer.Option("", help="Discord bot token"),
    whatsapp: str = typer.Option("", help="WhatsApp access token"),
    whatsapp_phone_id: str = typer.Option("", help="WhatsApp phone number ID"),
    signal: str = typer.Option("", help="Signal phone number"),
    slack: str = typer.Option("", help="Slack bot token (xoxb-...)"),
    slack_app: str = typer.Option("", help="Slack app token (xapp-...)"),
    teams_id: str = typer.Option("", help="Teams App ID"),
    teams_password: str = typer.Option("", help="Teams App Password"),
    imessage: bool = typer.Option(False, help="Enable iMessage (macOS only)"),
    # LLM flags
    llm: str = typer.Option("", help="LLM provider (claude, openai, openrouter, groq, etc.)"),
    llm_key: str = typer.Option("", help="LLM API key"),
    llm_model: str = typer.Option("", help="Model name override"),
    # Admin flag
    admin: str = typer.Option("", help="Admin user as platform:user_id (e.g., discord:123456)"),
    # Control flags
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
    auto: bool = typer.Option(False, "--auto", help="Auto-detect from env vars, skip prompts"),
) -> None:
    """Initialize VaultBot. Pass flags for zero-interaction setup.

    Examples:
      vaultbot init --discord TOKEN --llm openrouter --llm-key KEY --admin discord:123
      vaultbot init --auto                     (reads from VAULTBOT_* env vars)
      vaultbot init                            (interactive wizard)
    """
    import os
    import sys

    setup_logging(enable_file_logging=False)
    style.banner()

    store = CredentialStore()

    # Security check
    leaks = store.check_for_plaintext_leaks()
    if leaks:
        style.warning("Found plaintext credential files:")
        for path in leaks:
            style.hint(path)
    else:
        style.success("No plaintext credential files found.")

    # Check existing config
    if CONFIG_FILE.exists() and not force:
        if auto or _has_any_flag(telegram, discord, whatsapp, slack, llm, admin):
            pass  # flags override silently
        else:
            overwrite = typer.confirm(
                typer.style("  Config exists. Overwrite?", fg=typer.colors.YELLOW),
                default=False,
            )
            if not overwrite:
                style.info("Keeping existing config.")
                return

    config = VaultBotConfig()

    # --- Auto mode: read everything from env vars ---
    if auto:
        style.section("⚡", "Auto-detecting from environment")
        _auto_setup_platform(config, store, "telegram", "VAULTBOT_TELEGRAM_BOT_TOKEN")
        _auto_setup_platform(config, store, "discord", "VAULTBOT_DISCORD_BOT_TOKEN")
        _auto_setup_platform(config, store, "slack", "VAULTBOT_SLACK_BOT_TOKEN")

        env_llm = os.environ.get("VAULTBOT_LLM__PROVIDER", "")
        env_key = os.environ.get("VAULTBOT_LLM_API_KEY", "")
        if env_llm:
            config.llm.provider = env_llm
            if env_key:
                store.set("llm_api_key", env_key)
            style.success(f"LLM: {env_llm}")

        env_admin = os.environ.get("VAULTBOT_ADMIN", "")
        if env_admin:
            _add_admin(config, env_admin)

        config.save()
        style.section("🎉", "Setup Complete")
        style.success(f"Config saved to {CONFIG_FILE}")
        style.command_hint("vaultbot run")
        return

    # --- Flag mode: configure from CLI flags ---
    has_flags = _has_any_flag(telegram, discord, whatsapp, slack, llm, admin)

    if has_flags:
        style.section("⚡", "Configuring from flags")

        # Platforms
        if telegram:
            config.telegram.enabled = True
            store.set("telegram_bot_token", telegram)
            style.success("Telegram configured.")

        if discord:
            config.discord.enabled = True
            store.set("discord_bot_token", discord)
            style.success("Discord configured.")

        if whatsapp:
            config.whatsapp.enabled = True
            store.set("whatsapp_access_token", whatsapp)
            if whatsapp_phone_id:
                store.set("whatsapp_phone_number_id", whatsapp_phone_id)
            style.success("WhatsApp configured.")

        if signal:
            config.signal.enabled = True
            store.set("signal_account", signal)
            style.success("Signal configured.")

        if slack:
            config.slack.enabled = True
            store.set("slack_bot_token", slack)
            if slack_app:
                store.set("slack_app_token", slack_app)
            style.success("Slack configured.")

        if teams_id:
            config.teams.enabled = True
            store.set("teams_app_id", teams_id)
            if teams_password:
                store.set("teams_app_password", teams_password)
            style.success("Teams configured.")

        if imessage:
            if sys.platform == "darwin":
                config.imessage.enabled = True
                style.success("iMessage enabled.")
            else:
                style.warning("iMessage is macOS only. Skipping.")

        # LLM
        if llm:
            config.llm.provider = llm
            if llm_key:
                store.set("llm_api_key", llm_key)
            if llm_model:
                config.llm.model = llm_model
            style.success(f"LLM: {llm}")
        elif not config.telegram.enabled and not config.discord.enabled:
            # No platform set via flags, need at least LLM
            pass

        # Admin
        if admin:
            _add_admin(config, admin)

        config.save()
        style.section("🎉", "Setup Complete")
        style.success(f"Config saved to {CONFIG_FILE}")
        style.command_hint("vaultbot run")
        return

    # --- Interactive mode (fallback) ---
    style.section("📱", "Platform Setup")
    style.hint("Press Enter to skip any platform you don't need.")

    _interactive_platform(config, store, "Telegram", "telegram", "telegram_bot_token")
    _interactive_platform(config, store, "Discord", "discord", "discord_bot_token")
    _interactive_platform(config, store, "Slack", "slack", "slack_bot_token")

    if typer.confirm("  Enable more platforms? (WhatsApp/Signal/Teams/iMessage)", default=False):
        _interactive_platform(config, store, "WhatsApp", "whatsapp", "whatsapp_access_token")
        if config.whatsapp.enabled:
            phone_id = typer.prompt(
                typer.style("  WhatsApp phone number ID", fg=typer.colors.CYAN),
            )
            store.set("whatsapp_phone_number_id", phone_id)
        _interactive_platform(config, store, "Signal", "signal", "signal_account", hide=False)
        _interactive_platform(config, store, "Teams", "teams", "teams_app_id", hide=False)
        if sys.platform == "darwin" and typer.confirm("  Enable iMessage?", default=False):
            config.imessage.enabled = True
            style.success("iMessage enabled.")

    # LLM
    style.section("🤖", "LLM Setup")
    all_providers = [
        "claude",
        "openai",
        "openrouter",
        "together",
        "groq",
        "mistral",
        "perplexity",
        "deepseek",
        "fireworks",
        "ollama",
        "vllm",
        "lmstudio",
        "custom",
    ]
    provider = typer.prompt(
        typer.style("  LLM provider", fg=typer.colors.CYAN),
        default="claude",
        type=click.Choice(all_providers),
    )
    config.llm.provider = provider

    needs_key = {
        "claude",
        "openai",
        "openrouter",
        "together",
        "groq",
        "mistral",
        "perplexity",
        "deepseek",
        "fireworks",
    }
    if provider in needs_key:
        api_key = typer.prompt(
            typer.style(f"  {provider} API key", fg=typer.colors.CYAN),
            hide_input=True,
        )
        store.set("llm_api_key", api_key)
        style.success(f"{provider} API key stored.")
    elif provider == "custom":
        base_url = typer.prompt(
            typer.style("  API base URL", fg=typer.colors.CYAN),
        )
        store.set("custom_llm_base_url", base_url)
    else:
        style.info(f"{provider} — no API key needed.")

    # Admin
    style.section("👤", "Admin Setup")
    # Auto-detect platform from what was enabled
    enabled_platforms = [
        p
        for p in ["telegram", "discord", "slack", "whatsapp", "signal", "teams"]
        if getattr(config, p).enabled
    ]
    default_platform = enabled_platforms[0] if enabled_platforms else "telegram"

    user_id = typer.prompt(
        typer.style(f"  Your {default_platform} user ID", fg=typer.colors.CYAN),
    )
    _add_admin(config, f"{default_platform}:{user_id}")

    config.save()
    style.section("🎉", "Setup Complete")
    style.success(f"Config saved to {CONFIG_FILE}")
    style.command_hint("vaultbot run")


def _has_any_flag(*args: str | bool) -> bool:
    """Check if any CLI flag was provided."""
    return any(bool(a) for a in args)


def _auto_setup_platform(
    config: VaultBotConfig, store: CredentialStore, name: str, env_var: str
) -> None:
    """Auto-configure a platform from an env var if set."""
    import os

    val = os.environ.get(env_var, "")
    if val:
        platform_config = getattr(config, name)
        platform_config.enabled = True
        store.set(platform_config.credential_key, val)
        style.success(f"{name.capitalize()} auto-configured from {env_var}")


def _interactive_platform(
    config: VaultBotConfig,
    store: CredentialStore,
    display_name: str,
    config_name: str,
    credential_key: str,
    hide: bool = True,
) -> None:
    """Prompt for a platform token. Empty input = skip."""
    token = typer.prompt(
        typer.style(f"  {display_name} token", fg=typer.colors.CYAN),
        default="",
        show_default=False,
        hide_input=hide,
    )
    if token:
        platform_config = getattr(config, config_name)
        platform_config.enabled = True
        store.set(credential_key, token)
        style.success(f"{display_name} configured.")


def _add_admin(config: VaultBotConfig, admin_str: str) -> None:
    """Add an admin from 'platform:user_id' format."""
    from vaultbot.config import AllowlistEntry

    if ":" not in admin_str:
        style.error(f"Invalid format '{admin_str}'. Use platform:user_id")
        return
    platform, user_id = admin_str.split(":", 1)
    config.allowlist.append(AllowlistEntry(platform=platform, user_id=user_id, role="admin"))
    style.success(f"Admin: {platform}:{user_id}")


_config_option: Path | None = typer.Option(None, "--config", "-c", help="Config file path")


@app.command()
def run(
    config_path: Path | None = _config_option,
) -> None:
    """Start the VaultBot agent."""
    config = VaultBotConfig.load(config_path)
    setup_logging(
        json_output=config.log_json,
        level=config.log_level,
        log_dir=Path(config.log_dir) if config.log_dir else None,
        enable_file_logging=config.log_file,
    )

    store = CredentialStore()

    # Check for plaintext leaks on every start
    leaks = store.check_for_plaintext_leaks()
    if leaks:
        style.error("Found plaintext credential files. Refusing to start.")
        style.hint("Remove these files and use `vaultbot credentials set` instead:")
        for path in leaks:
            style.hint(path)
        raise typer.Exit(1)

    from vaultbot.core.bot import VaultBot

    bot = VaultBot(config)
    registered_platforms: list[str] = []

    # Register enabled platforms
    if config.telegram.enabled:
        token = store.get(config.telegram.credential_key)
        if not token:
            style.error("Telegram token not found.")
            style.command_hint("vaultbot credentials set telegram_bot_token")
            raise typer.Exit(1)
        from vaultbot.platforms.telegram import TelegramAdapter

        bot.register_platform(TelegramAdapter(token))
        registered_platforms.append("Telegram")

    if config.discord.enabled:
        token = store.get(config.discord.credential_key)
        if not token:
            style.error("Discord token not found.")
            style.command_hint("vaultbot credentials set discord_bot_token")
            raise typer.Exit(1)
        try:
            from vaultbot.platforms.discord import DiscordAdapter

            bot.register_platform(DiscordAdapter(token))
            style.success("Discord adapter registered.")
        except ImportError as e:
            style.error(f"Discord: {e}")
            raise typer.Exit(1) from e

    if config.whatsapp.enabled:
        access_token = store.get("whatsapp_access_token")
        phone_id = store.get("whatsapp_phone_number_id")
        if not access_token or not phone_id:
            style.error("WhatsApp credentials not found.")
            style.command_hint("vaultbot credentials set whatsapp_access_token")
            raise typer.Exit(1)
        from vaultbot.platforms.whatsapp import WhatsAppAdapter

        bot.register_platform(WhatsAppAdapter(access_token=access_token, phone_number_id=phone_id))
        style.success("WhatsApp adapter registered.")

    if config.signal.enabled:
        account = store.get("signal_account")
        if not account:
            style.error("Signal account not found.")
            style.command_hint("vaultbot credentials set signal_account")
            raise typer.Exit(1)
        from vaultbot.platforms.signal import SignalAdapter

        bot.register_platform(SignalAdapter(account=account))
        style.success("Signal adapter registered.")

    if config.slack.enabled:
        bot_token = store.get("slack_bot_token")
        app_token = store.get("slack_app_token")
        if not bot_token:
            style.error("Slack bot token not found.")
            style.command_hint("vaultbot credentials set slack_bot_token")
            raise typer.Exit(1)
        try:
            from vaultbot.platforms.slack import SlackAdapter

            bot.register_platform(SlackAdapter(bot_token=bot_token, app_token=app_token or ""))
            style.success("Slack adapter registered.")
        except ImportError as e:
            style.error(f"Slack: {e}")
            raise typer.Exit(1) from e

    if config.teams.enabled:
        app_id = store.get("teams_app_id")
        app_password = store.get("teams_app_password")
        if not app_id or not app_password:
            style.error("Teams credentials not found.")
            style.command_hint("vaultbot credentials set teams_app_id")
            raise typer.Exit(1)
        try:
            from vaultbot.platforms.teams import TeamsAdapter

            bot.register_platform(TeamsAdapter(app_id=app_id, app_password=app_password))
            style.success("Teams adapter registered.")
        except ImportError as e:
            style.error(f"Teams: {e}")
            raise typer.Exit(1) from e

    if config.imessage.enabled:
        try:
            from vaultbot.platforms.imessage import IMessageAdapter

            bot.register_platform(IMessageAdapter())
            style.success("iMessage adapter registered.")
        except (ImportError, RuntimeError) as e:
            style.error(f"iMessage: {e}")
            raise typer.Exit(1) from e

    # Register LLM provider with prompt guard
    from vaultbot.llm.prompt_guard import GuardedLLMProvider

    llm_provider = None

    from vaultbot.llm.compatible import PROVIDER_PRESETS, CompatibleProvider

    compatible_providers = set(PROVIDER_PRESETS.keys())
    provider_name = config.llm.provider

    if provider_name == "claude":
        api_key = store.get(config.llm.credential_key)
        if not api_key:
            style.error("Claude API key not found.")
            style.command_hint("vaultbot credentials set llm_api_key")
            raise typer.Exit(1)
        from vaultbot.llm.claude import ClaudeProvider

        llm_provider = ClaudeProvider(api_key, config.llm.model)

    elif provider_name == "openai":
        api_key = store.get(config.llm.credential_key)
        if not api_key:
            style.error("OpenAI API key not found.")
            style.command_hint("vaultbot credentials set llm_api_key")
            raise typer.Exit(1)
        from vaultbot.llm.openai_gpt import OpenAIProvider

        llm_provider = OpenAIProvider(api_key, config.llm.model)

    elif provider_name in compatible_providers:
        api_key = store.get(config.llm.credential_key) or "not-needed"
        llm_provider = CompatibleProvider.from_preset(
            provider_name,
            api_key=api_key,
            model=config.llm.model if config.llm.model != "claude-sonnet-4-20250514" else None,
        )

    elif provider_name == "custom":
        base_url = store.get("custom_llm_base_url")
        if not base_url:
            style.error("Custom LLM base URL not found.")
            style.command_hint("vaultbot credentials set custom_llm_base_url")
            raise typer.Exit(1)
        api_key = store.get(config.llm.credential_key) or "not-needed"
        llm_provider = CompatibleProvider(
            base_url=base_url,
            default_model=config.llm.model,
            api_key=api_key,
            provider_label="custom",
        )

    else:
        style.error(f"Unknown LLM provider '{provider_name}'.")
        style.hint(
            "Available: claude, openai, openrouter, together, groq, "
            "mistral, perplexity, deepseek, fireworks, ollama, vllm, "
            "lmstudio, custom"
        )
        raise typer.Exit(1)

    # Wrap with prompt injection guard
    bot.set_llm(GuardedLLMProvider(llm_provider))

    # Get dashboard token for display
    dashboard_token = bot._dashboard._config.api_token

    # Show startup summary
    style.startup_summary(
        platforms=registered_platforms,
        llm_provider=f"{config.llm.provider} (guarded)",
        security=[
            "Zero-trust auth (allowlist enforced)",
            "Prompt injection guard (13 patterns)",
            "Rate limiting (per-user + global)",
            "Audit logging (append-only)",
            "Encrypted credential storage",
        ],
    )

    style.section("🌐", "Endpoints")
    style.key_value("Health", "http://localhost:8081/health")
    style.key_value("Dashboard UI", "http://localhost:8082/dashboard")
    style.key_value("API Status", "http://localhost:8082/dashboard/api/status")
    style.key_value("SSE Events", "http://localhost:8082/dashboard/api/events")
    style.key_value("Dashboard Token", dashboard_token)
    style.hint("Open http://localhost:8082/dashboard in your browser for the full control panel")
    typer.echo()

    try:
        asyncio.run(bot.start())
    except RuntimeError as e:
        style.error(str(e))
        raise typer.Exit(1) from e
    except KeyboardInterrupt:
        typer.echo()
        style.info("V.A.U.L.T. BOT stopped.")


# --- Credentials commands ---


@credentials_app.command("set")
def credentials_set(
    key: str = typer.Argument(help="Credential key (e.g., telegram_bot_token, llm_api_key)"),
) -> None:
    """Store a credential securely in the OS keychain."""
    setup_logging(enable_file_logging=False)
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
    setup_logging(enable_file_logging=False)
    store = CredentialStore()
    store.delete(key)
    style.success(f"Credential '{key}' deleted.")


@credentials_app.command("check")
def credentials_check(
    key: str = typer.Argument(help="Credential key to check"),
) -> None:
    """Check if a credential exists (without revealing its value)."""
    setup_logging(enable_file_logging=False)
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
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.loader import PluginLoader, PluginLoadError
    from vaultbot.plugins.registry import PluginRegistry
    from vaultbot.plugins.signer import PluginVerifier
    from vaultbot.security.audit import AuditLogger

    registry = PluginRegistry()
    verifier = PluginVerifier()
    audit = AuditLogger()
    loader = PluginLoader(registry, verifier, audit)

    try:
        entry = loader.load_plugin(plugin_dir)
        style.success(f"Plugin '{entry.manifest.name}' v{entry.manifest.version} installed.")
    except PluginLoadError as e:
        style.error(str(e))
        raise typer.Exit(1) from e


@plugin_app.command("list")
def plugin_list() -> None:
    """List all installed plugins."""
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    plugins = registry.list_plugins()

    if not plugins:
        style.info("No plugins installed.")
        style.command_hint("vaultbot plugin install <plugin-dir>")
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
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.registry import PluginRegistry

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
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.registry import PluginRegistry

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
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.registry import PluginRegistry

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
    key_file: Path = typer.Argument(help="Path to Ed25519 private key (PEM)"),
) -> None:
    """Sign a plugin with an Ed25519 private key."""
    setup_logging(enable_file_logging=False)
    import json

    from vaultbot.plugins.signer import PluginSigner

    if not key_file.exists():
        style.error(f"Key file not found: {key_file}")
        raise typer.Exit(1)

    manifest_path = plugin_dir / "vaultbot_plugin.json"
    if not manifest_path.exists():
        style.error("No vaultbot_plugin.json found in plugin directory.")
        raise typer.Exit(1)

    manifest_data = json.loads(manifest_path.read_text())
    signer = PluginSigner.from_key_bytes(key_file.read_bytes())
    sig = signer.sign_plugin(
        manifest_data["name"],
        manifest_data["version"],
        plugin_dir,
    )
    style.success(f"Plugin '{sig.plugin_name}' v{sig.plugin_version} signed.")
    style.key_value("Public key", sig.signer_public_key.hex()[:32] + "...")


@plugin_app.command("keygen")
def plugin_keygen(
    output_dir: Path = typer.Argument(help="Directory to write the keypair files"),
) -> None:
    """Generate an Ed25519 keypair for plugin signing."""
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.signer import PluginSigner

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
    style.hint(f"To trust this key: copy {public_path.name} to ~/.vaultbot/trust_store/")


# --- Marketplace commands ---


@marketplace_app.command("search")
def marketplace_search(
    query: str = typer.Argument("", help="Search query"),
) -> None:
    """Search the plugin marketplace."""
    setup_logging(enable_file_logging=False)
    style.info(f"Searching marketplace for '{query}'...")
    style.hint("Marketplace server not configured yet.")
    style.hint("Set VAULTBOT_MARKETPLACE_URL or wait for marketplace launch.")


@marketplace_app.command("info")
def marketplace_info(
    name: str = typer.Argument(help="Plugin name"),
) -> None:
    """Get details about a marketplace plugin."""
    setup_logging(enable_file_logging=False)
    style.info(f"Looking up plugin '{name}'...")
    style.hint("Marketplace server not configured yet.")


# --- Team commands ---


@team_app.command("create")
def team_create(
    name: str = typer.Argument(help="Team name"),
    description: str = typer.Option("", "--desc", "-d", help="Team description"),
) -> None:
    """Create a new team."""
    setup_logging(enable_file_logging=False)
    from vaultbot.security.teams import TeamManager

    mgr = TeamManager()
    try:
        mgr.create_team(name, description)
        style.success(f"Team '{name}' created.")
    except ValueError as e:
        style.error(str(e))
        raise typer.Exit(1) from e


@team_app.command("list")
def team_list() -> None:
    """List all teams."""
    setup_logging(enable_file_logging=False)
    style.info("Teams are stored in config. Use `vaultbot init` to set up teams.")
    style.hint("Team persistence coming in a future update.")


# --- SDK commands ---


@sdk_app.command("new")
def sdk_new(
    name: str = typer.Argument(help="Plugin name"),
    output_dir: Path = typer.Option(".", "--output", "-o", help="Output directory"),
    description: str = typer.Option("A VaultBot plugin", "--desc", "-d"),
    author: str = typer.Option("", "--author", "-a"),
) -> None:
    """Scaffold a new plugin project."""
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.sdk import scaffold_plugin

    plugin_dir = scaffold_plugin(output_dir, name, description, author)
    style.success(f"Plugin '{name}' scaffolded.")
    style.key_value("Location", str(plugin_dir))
    style.hint("Edit plugin.py to implement your logic.")
    style.command_hint(f"vaultbot sdk test {plugin_dir}")


@sdk_app.command("test")
def sdk_test(
    plugin_dir: Path = typer.Argument(help="Path to plugin directory"),
) -> None:
    """Run the test harness against a plugin."""
    setup_logging(enable_file_logging=False)
    import importlib.util

    from vaultbot.plugins.sdk import PluginTestHarness

    module_path = plugin_dir / "plugin.py"
    if not module_path.exists():
        style.error(f"No plugin.py found in {plugin_dir}")
        raise typer.Exit(1)

    # Load the plugin
    spec = importlib.util.spec_from_file_location("plugin_module", module_path)
    if spec is None or spec.loader is None:
        style.error("Cannot load plugin module.")
        raise typer.Exit(1)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find the plugin class
    plugin_cls = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and hasattr(attr, "manifest")
            and hasattr(attr, "handle")
            and attr_name != "PluginBase"
        ):
            plugin_cls = attr
            break

    if plugin_cls is None:
        style.error("No PluginBase subclass found in plugin.py")
        raise typer.Exit(1)

    plugin = plugin_cls()
    harness = PluginTestHarness(plugin)

    style.header(f"Testing plugin: {plugin.manifest().name}")
    style.divider()

    results = asyncio.run(harness.run_all())

    for r in results:
        if r.passed:
            style.success(r.test_name)
        else:
            style.error(f"{r.test_name} — {r.message}")

    style.divider()
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    if passed == total:
        style.success(f"All {total} tests passed!")
    else:
        style.warning(f"{passed}/{total} tests passed.")
        raise typer.Exit(1)


@sdk_app.command("validate")
def sdk_validate(
    plugin_dir: Path = typer.Argument(help="Path to plugin directory"),
) -> None:
    """Validate a plugin's manifest file."""
    setup_logging(enable_file_logging=False)
    from vaultbot.plugins.sdk import validate_manifest

    manifest_path = plugin_dir / "vaultbot_plugin.json"
    errors = validate_manifest(manifest_path)

    if not errors:
        style.success("Manifest is valid.")
    else:
        style.error("Manifest validation failed:")
        for err in errors:
            style.hint(err)
        raise typer.Exit(1)
