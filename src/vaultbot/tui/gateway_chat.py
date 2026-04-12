"""Gateway chat client for real-time TUI communication."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    model: str = ""
    token_count: int = 0


class GatewayChat:
    """TUI gateway chat client with message history and streaming."""

    def __init__(self, gateway_url: str = "ws://localhost:8765") -> None:
        self._gateway_url = gateway_url
        self._messages: list[ChatMessage] = []
        self._connected = False
        self._streaming = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def message_count(self) -> int:
        return len(self._messages)

    async def connect(self) -> None:
        self._connected = True
        logger.info("tui_chat_connected", url=self._gateway_url)

    async def disconnect(self) -> None:
        self._connected = False

    def add_user_message(self, content: str) -> ChatMessage:
        msg = ChatMessage(role="user", content=content)
        self._messages.append(msg)
        return msg

    def add_assistant_message(self, content: str, model: str = "") -> ChatMessage:
        msg = ChatMessage(role="assistant", content=content, model=model)
        self._messages.append(msg)
        return msg

    def get_history(self, limit: int = 50) -> list[ChatMessage]:
        return self._messages[-limit:]

    def clear_history(self) -> None:
        self._messages.clear()

    def start_streaming(self) -> None:
        self._streaming = True

    def stop_streaming(self) -> None:
        self._streaming = False

    @property
    def is_streaming(self) -> bool:
        return self._streaming
