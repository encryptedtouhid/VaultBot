"""WebSocket gateway message protocol definitions."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class MessageType(str, Enum):
    """WebSocket message types."""

    AUTH = "auth"
    AUTH_OK = "auth_ok"
    AUTH_FAIL = "auth_fail"
    CHAT = "chat"
    CHAT_RESPONSE = "chat_response"
    COMMAND = "command"
    COMMAND_RESULT = "command_result"
    EVENT = "event"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    STATUS = "status"


class ConnectionState(str, Enum):
    """Client connection state."""

    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


@dataclass(frozen=True, slots=True)
class WSMessage:
    """A WebSocket protocol message."""

    type: MessageType
    payload: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type.value,
            "id": self.id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WSMessage:
        return cls(
            type=MessageType(str(data.get("type", "error"))),
            payload=dict(data.get("payload", {})),  # type: ignore[arg-type]
            id=str(data.get("id", uuid.uuid4().hex[:12])),
            timestamp=float(data.get("timestamp", time.time())),
        )


@dataclass(slots=True)
class ClientInfo:
    """Information about a connected client."""

    client_id: str
    user_id: str = ""
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)
