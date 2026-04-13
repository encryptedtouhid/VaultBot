"""Plugin SDK channel lifecycle hooks."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ChannelEvent(str, Enum):
    SETUP = "setup"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    MESSAGE_IN = "message_in"
    MESSAGE_OUT = "message_out"
    PAIRING = "pairing"
    ERROR = "error"


LifecycleHandler = Callable[..., Coroutine[Any, Any, None]]


@dataclass(frozen=True, slots=True)
class ChannelLifecycleHook:
    channel: str
    event: ChannelEvent
    handler: LifecycleHandler
    priority: int = 0


class ChannelLifecycleManager:
    """Manages channel lifecycle hooks for plugins."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[ChannelLifecycleHook]] = {}

    def register(self, hook: ChannelLifecycleHook) -> None:
        key = f"{hook.channel}:{hook.event.value}"
        self._hooks.setdefault(key, []).append(hook)
        self._hooks[key].sort(key=lambda h: h.priority, reverse=True)

    async def trigger(self, channel: str, event: ChannelEvent, **kwargs: object) -> int:
        key = f"{channel}:{event.value}"
        hooks = self._hooks.get(key, [])
        triggered = 0
        for hook in hooks:
            try:
                await hook.handler(**kwargs)
                triggered += 1
            except Exception as exc:
                logger.warning("lifecycle_hook_error", channel=channel, error=str(exc))
        return triggered

    def list_hooks(self, channel: str = "") -> list[ChannelLifecycleHook]:
        if channel:
            return [h for hooks in self._hooks.values() for h in hooks if h.channel == channel]
        return [h for hooks in self._hooks.values() for h in hooks]

    @property
    def hook_count(self) -> int:
        return sum(len(v) for v in self._hooks.values())
