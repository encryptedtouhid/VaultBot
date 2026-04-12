"""Event bus for broadcasting events to subscribers."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class GatewayEvent:
    event_type: str
    payload: dict[str, object] = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)


EventCallback = Callable[[GatewayEvent], None]


class EventBus:
    """Publish-subscribe event bus for gateway events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventCallback]] = {}
        self._event_count = 0

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback: EventCallback) -> bool:
        subs = self._subscribers.get(event_type, [])
        if callback in subs:
            subs.remove(callback)
            return True
        return False

    def publish(self, event: GatewayEvent) -> int:
        """Publish event to all subscribers. Returns count notified."""
        callbacks = self._subscribers.get(event.event_type, [])
        wildcard = self._subscribers.get("*", [])
        all_callbacks = callbacks + wildcard
        for cb in all_callbacks:
            try:
                cb(event)
            except Exception as exc:
                logger.warning("event_handler_error", event_type=event.event_type, error=str(exc))
        self._event_count += 1
        return len(all_callbacks)

    @property
    def event_count(self) -> int:
        return self._event_count

    def subscriber_count(self, event_type: str | None = None) -> int:
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(v) for v in self._subscribers.values())
