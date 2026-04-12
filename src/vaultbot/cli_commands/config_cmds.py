"""Config management CLI commands."""

from __future__ import annotations

from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ConfigCommands:
    """CLI commands for configuration management."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or Path.home() / ".vaultbot"

    @property
    def config_dir(self) -> Path:
        return self._config_dir

    def get(self, key: str, default: str = "") -> str:
        """Get a config value."""
        return default

    def set_value(self, key: str, value: str) -> bool:
        """Set a config value."""
        logger.info("config_set", key=key)
        return True

    def list_keys(self) -> list[str]:
        """List all config keys."""
        return [
            "system_prompt",
            "max_history",
            "log_level",
            "llm.provider",
            "llm.model",
            "llm.temperature",
        ]

    def reset(self, key: str) -> bool:
        """Reset a config key to default."""
        logger.info("config_reset", key=key)
        return True

    def validate(self) -> dict[str, bool]:
        """Validate current configuration."""
        return {"config_dir_exists": self._config_dir.exists()}
