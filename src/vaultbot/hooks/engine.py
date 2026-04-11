"""Hook engine for before/after tool execution and lifecycle events.

Allows registering custom logic that fires before/after any tool call,
on agent startup, or on other lifecycle events.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class HookEvent(str, Enum):
    """Events that can trigger hooks."""

    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    BEFORE_LLM = "before_llm"
    AFTER_LLM = "after_llm"
    ON_MESSAGE = "on_message"
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"
    ON_ERROR = "on_error"


@dataclass(frozen=True, slots=True)
class HookContext:
    """Context passed to hook functions."""

    event: HookEvent
    tool_name: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HookResult:
    """Result from a hook execution."""

    allow: bool = True  # If False, the action is blocked
    modified_data: dict[str, Any] | None = None
    reason: str = ""


HookFn = Callable[[HookContext], Coroutine[Any, Any, HookResult]]


@dataclass
class RegisteredHook:
    """A registered hook with metadata."""

    name: str
    event: HookEvent
    handler: HookFn
    priority: int = 0  # Lower = runs first
    enabled: bool = True


class HookEngine:
    """Manages and executes hooks for lifecycle events."""

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[RegisteredHook]] = {event: [] for event in HookEvent}
        self._execution_count: int = 0

    def register(
        self,
        name: str,
        event: HookEvent,
        handler: HookFn,
        *,
        priority: int = 0,
    ) -> None:
        """Register a hook for an event."""
        hook = RegisteredHook(name=name, event=event, handler=handler, priority=priority)
        self._hooks[event].append(hook)
        self._hooks[event].sort(key=lambda h: h.priority)
        logger.info("hook_registered", hook_name=name, hook_event=event.value, priority=priority)

    def unregister(self, name: str) -> bool:
        """Unregister a hook by name (from all events)."""
        removed = False
        for event in HookEvent:
            before = len(self._hooks[event])
            self._hooks[event] = [h for h in self._hooks[event] if h.name != name]
            if len(self._hooks[event]) < before:
                removed = True
        return removed

    def enable(self, name: str) -> bool:
        """Enable a hook by name."""
        return self._set_enabled(name, True)

    def disable(self, name: str) -> bool:
        """Disable a hook by name."""
        return self._set_enabled(name, False)

    async def execute(self, context: HookContext) -> HookResult:
        """Execute all hooks for an event in priority order.

        If any hook returns allow=False, execution stops and the
        blocking result is returned.
        """
        hooks = self._hooks.get(context.event, [])
        for hook in hooks:
            if not hook.enabled:
                continue
            try:
                result = await hook.handler(context)
                self._execution_count += 1
                if not result.allow:
                    logger.info(
                        "hook_blocked",
                        hook=hook.name,
                        hook_event=context.event.value,
                        reason=result.reason,
                    )
                    return result
            except Exception as exc:
                logger.error("hook_error", hook=hook.name, error=str(exc))

        return HookResult(allow=True)

    def list_hooks(self, event: HookEvent | None = None) -> list[RegisteredHook]:
        """List registered hooks, optionally filtered by event."""
        if event:
            return list(self._hooks.get(event, []))
        return [h for hooks in self._hooks.values() for h in hooks]

    @property
    def execution_count(self) -> int:
        return self._execution_count

    def _set_enabled(self, name: str, enabled: bool) -> bool:
        found = False
        for hooks in self._hooks.values():
            for hook in hooks:
                if hook.name == name:
                    hook.enabled = enabled
                    found = True
        return found
