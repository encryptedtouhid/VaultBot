"""Device control and automation capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class DeviceAction(str, Enum):
    """Available device actions."""

    SCREENSHOT = "screenshot"
    NOTIFICATION = "notification"
    CLIPBOARD_GET = "clipboard_get"
    CLIPBOARD_SET = "clipboard_set"
    APP_LAUNCH = "app_launch"
    APP_CLOSE = "app_close"
    VOLUME_SET = "volume_set"
    BRIGHTNESS_SET = "brightness_set"
    LOCK_SCREEN = "lock_screen"


class DeviceCapability(str, Enum):
    """Device capabilities."""

    SCREEN_CAPTURE = "screen_capture"
    NOTIFICATIONS = "notifications"
    CLIPBOARD = "clipboard"
    APP_CONTROL = "app_control"
    AUDIO = "audio"
    DISPLAY = "display"


@dataclass(frozen=True, slots=True)
class DeviceCommand:
    """A device control command."""

    action: DeviceAction
    params: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DeviceResult:
    """Result of a device control command."""

    success: bool
    action: DeviceAction
    data: dict[str, object] = field(default_factory=dict)
    error: str = ""


@runtime_checkable
class DeviceProvider(Protocol):
    """Protocol for device control providers."""

    @property
    def provider_name(self) -> str: ...

    def capabilities(self) -> list[DeviceCapability]: ...

    async def execute(self, command: DeviceCommand) -> DeviceResult: ...


class DeviceControlManager:
    """Manages device control across providers."""

    def __init__(self) -> None:
        self._providers: dict[str, DeviceProvider] = {}
        self._execution_count = 0

    def register_provider(self, provider: DeviceProvider) -> None:
        self._providers[provider.provider_name] = provider
        logger.info("device_provider_registered", provider=provider.provider_name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def get_capabilities(self, provider: str | None = None) -> list[DeviceCapability]:
        if provider and provider in self._providers:
            return self._providers[provider].capabilities()
        all_caps: list[DeviceCapability] = []
        for p in self._providers.values():
            all_caps.extend(p.capabilities())
        return list(set(all_caps))

    async def execute(self, command: DeviceCommand, *, provider: str | None = None) -> DeviceResult:
        name = provider or next(iter(self._providers), "")
        if not name or name not in self._providers:
            return DeviceResult(success=False, action=command.action, error="No provider available")
        result = await self._providers[name].execute(command)
        self._execution_count += 1
        return result

    @property
    def execution_count(self) -> int:
        return self._execution_count
