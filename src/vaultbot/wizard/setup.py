"""Main setup wizard orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SetupStep(str, Enum):
    WELCOME = "welcome"
    CHANNEL_SELECT = "channel_select"
    PROVIDER_SELECT = "provider_select"
    MODEL_SELECT = "model_select"
    PLUGIN_DISCOVER = "plugin_discover"
    HEALTH_CHECK = "health_check"
    COMPLETE = "complete"


@dataclass(slots=True)
class SetupState:
    current_step: SetupStep = SetupStep.WELCOME
    selected_channels: list[str] = field(default_factory=list)
    selected_provider: str = ""
    selected_model: str = ""
    installed_plugins: list[str] = field(default_factory=list)
    health_passed: bool = False
    completed: bool = False


class SetupWizard:
    """Interactive setup wizard for VaultBot configuration."""

    def __init__(self) -> None:
        self._state = SetupState()
        self._available_channels = [
            "telegram",
            "discord",
            "slack",
            "whatsapp",
            "signal",
            "teams",
            "matrix",
            "irc",
            "mattermost",
        ]
        self._available_providers = ["claude", "openai", "deepseek", "local"]
        self._available_plugins = ["weather", "calculator", "reminder"]

    @property
    def state(self) -> SetupState:
        return self._state

    @property
    def current_step(self) -> SetupStep:
        return self._state.current_step

    def get_available_channels(self) -> list[str]:
        return list(self._available_channels)

    def select_channels(self, channels: list[str]) -> None:
        self._state.selected_channels = channels
        self._state.current_step = SetupStep.PROVIDER_SELECT

    def get_available_providers(self) -> list[str]:
        return list(self._available_providers)

    def select_provider(self, provider: str) -> None:
        self._state.selected_provider = provider
        self._state.current_step = SetupStep.MODEL_SELECT

    def select_model(self, model: str) -> None:
        self._state.selected_model = model
        self._state.current_step = SetupStep.PLUGIN_DISCOVER

    def install_plugins(self, plugins: list[str]) -> None:
        self._state.installed_plugins = plugins
        self._state.current_step = SetupStep.HEALTH_CHECK

    def run_health_check(self) -> dict[str, bool]:
        checks = {
            "config_valid": bool(self._state.selected_provider),
            "channels_configured": len(self._state.selected_channels) > 0,
            "model_selected": bool(self._state.selected_model),
        }
        self._state.health_passed = all(checks.values())
        self._state.current_step = SetupStep.COMPLETE
        return checks

    def complete(self) -> SetupState:
        self._state.completed = True
        logger.info("setup_wizard_completed")
        return self._state

    def reset(self) -> None:
        self._state = SetupState()
