"""Generic webhook bridge as a channel type."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from vaultbot.core.message import InboundMessage, OutboundMessage
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class WebhookMapping:
    """Maps webhook payload fields to message fields."""

    content_path: str = "text"
    user_id_path: str = "user.id"
    chat_id_path: str = "channel"


@dataclass(slots=True)
class WebhookBridgeConfig:
    name: str = "webhook"
    secret: str = ""
    mapping: WebhookMapping = field(default_factory=WebhookMapping)


class WebhookBridge:
    """Generic webhook bridge for receiving messages from any source."""

    def __init__(self, config: WebhookBridgeConfig | None = None) -> None:
        self._config = config or WebhookBridgeConfig()
        self._queue: list[InboundMessage] = []
        self._running = False

    @property
    def platform_name(self) -> str:
        return self._config.name

    async def connect(self) -> None:
        self._running = True
        logger.info("webhook_bridge_connected", name=self._config.name)

    async def disconnect(self) -> None:
        self._running = False

    async def listen(self) -> AsyncIterator[InboundMessage]:
        while self._queue:
            yield self._queue.pop(0)

    async def send(self, message: OutboundMessage) -> None:
        logger.info("webhook_bridge_send", content=message.content[:50])

    async def healthcheck(self) -> bool:
        return self._running

    def ingest_payload(self, payload: dict[str, object]) -> InboundMessage | None:
        """Transform a raw webhook payload into an InboundMessage."""
        mapping = self._config.mapping
        content = self._extract_path(payload, mapping.content_path)
        user_id = self._extract_path(payload, mapping.user_id_path)
        if not content:
            return None
        msg = InboundMessage(
            id="",
            platform=self._config.name,
            sender_id=str(user_id),
            chat_id="",
            text=str(content),
        )
        self._queue.append(msg)
        return msg

    @staticmethod
    def _extract_path(data: dict[str, object], path: str) -> object:
        """Extract a value from nested dict using dot-separated path."""
        current: object = data
        for key in path.split("."):
            if isinstance(current, dict):
                current = current.get(key, "")
            else:
                return ""
        return current
