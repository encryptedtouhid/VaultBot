"""Hook registration with event types."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class HookEvent(str, Enum):
    BEFORE_REPLY = "before_reply"
    AFTER_REPLY = "after_reply"
    ON_COMMAND = "on_command"
    ON_ERROR = "on_error"
    ON_SESSION_START = "on_session_start"
    ON_SESSION_END = "on_session_end"
    ON_BOOT = "on_boot"
    ON_SHUTDOWN = "on_shutdown"


HookCallback = Callable[..., Coroutine[Any, Any, None]]


@dataclass(frozen=True, slots=True)
class HookDefinition:
    name: str
    event: HookEvent
    callback: HookCallback
    priority: int = 0
    enabled: bool = True


class HookRegistry:
    """Registry for event-driven hooks."""

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[HookDefinition]] = {}

    def register(self, hook: HookDefinition) -> None:
        self._hooks.setdefault(hook.event, []).append(hook)
        self._hooks[hook.event].sort(key=lambda h: h.priority, reverse=True)
        logger.info("hook_registered", name=hook.name, hook_event=hook.event.value)

    def unregister(self, name: str) -> bool:
        for event_hooks in self._hooks.values():
            before = len(event_hooks)
            event_hooks[:] = [h for h in event_hooks if h.name != name]
            if len(event_hooks) < before:
                return True
        return False

    async def trigger(self, event: HookEvent, **kwargs: object) -> int:
        hooks = self._hooks.get(event, [])
        triggered = 0
        for hook in hooks:
            if not hook.enabled:
                continue
            try:
                await hook.callback(**kwargs)
                triggered += 1
            except Exception as exc:
                logger.warning("hook_error", name=hook.name, error=str(exc))
        return triggered

    def list_hooks(self, event: HookEvent | None = None) -> list[HookDefinition]:
        if event:
            return list(self._hooks.get(event, []))
        return [h for hooks in self._hooks.values() for h in hooks]

    @property
    def hook_count(self) -> int:
        return sum(len(v) for v in self._hooks.values())
