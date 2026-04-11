"""Configuration management with Pydantic validation and secure defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from vaultbot.security.auth import Role

CONFIG_DIR = Path.home() / ".vaultbot"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    user_capacity: float = 10.0
    user_refill_rate: float = 1.0
    global_capacity: float = 50.0
    global_refill_rate: float = 10.0


class PlatformConfig(BaseModel):
    """Configuration for a messaging platform."""

    enabled: bool = False
    # Credential keys are stored in the credential store, not here
    credential_key: str = ""


class LLMConfig(BaseModel):
    """Configuration for the LLM provider."""

    provider: str = "claude"
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096
    credential_key: str = "llm_api_key"


class AllowlistEntry(BaseModel):
    """A user in the allowlist."""

    platform: str
    user_id: str
    role: str = "user"


class VaultBotConfig(BaseSettings):
    """Main VaultBot configuration with secure defaults."""

    # General
    system_prompt: str = Field(
        default="You are VaultBot, a helpful and secure AI assistant. "
        "Be concise, accurate, and respectful.",
    )
    max_history: int = 20
    log_level: str = "INFO"
    log_json: bool = False
    log_file: bool = True  # Write logs to ~/.vaultbot/logs/
    log_dir: str = ""  # Custom log directory (empty = default)

    # Platforms
    telegram: PlatformConfig = PlatformConfig(credential_key="telegram_bot_token")
    discord: PlatformConfig = PlatformConfig(credential_key="discord_bot_token")
    whatsapp: PlatformConfig = PlatformConfig(credential_key="whatsapp_api_token")
    signal: PlatformConfig = PlatformConfig(credential_key="signal_phone_number")
    slack: PlatformConfig = PlatformConfig(credential_key="slack_bot_token")
    teams: PlatformConfig = PlatformConfig(credential_key="teams_app_id")
    imessage: PlatformConfig = PlatformConfig(credential_key="imessage")
    irc: PlatformConfig = PlatformConfig(credential_key="irc_server")
    matrix: PlatformConfig = PlatformConfig(credential_key="matrix_access_token")
    mattermost: PlatformConfig = PlatformConfig(credential_key="mattermost_token")

    # LLM
    llm: LLMConfig = LLMConfig()

    # Rate limiting
    rate_limit: RateLimitConfig = RateLimitConfig()

    # Allowlist
    allowlist: list[AllowlistEntry] = Field(default_factory=list)

    model_config = {
        "env_prefix": "VAULTBOT_",
        "env_nested_delimiter": "__",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def get_allowlist(self) -> dict[str, Role]:
        """Convert allowlist entries to the format expected by AuthManager."""
        result: dict[str, Role] = {}
        for entry in self.allowlist:
            if isinstance(entry, dict):
                qualified = f"{entry['platform']}:{entry['user_id']}"
                result[qualified] = Role(entry.get("role", "user"))
            else:
                qualified = f"{entry.platform}:{entry.user_id}"
                result[qualified] = Role(entry.role)
        return result

    @classmethod
    def load(cls, path: Path | None = None) -> VaultBotConfig:
        """Load config from YAML file, falling back to defaults."""
        config_path = path or CONFIG_FILE
        if config_path.exists():
            with open(config_path) as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()

    def save(self, path: Path | None = None) -> None:
        """Save current config to YAML file."""
        config_path = path or CONFIG_FILE
        config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with open(config_path, "w") as f:
            yaml.dump(
                self.model_dump(exclude_defaults=False),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
        config_path.chmod(0o600)
