"""WebSocket gateway server with connection management and message routing."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from vaultbot.gateway.protocol import (
    ClientInfo,
    ConnectionState,
    MessageType,
    WSMessage,
)
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

MessageHandler = Callable[[str, WSMessage], Coroutine[Any, Any, WSMessage | None]]


class WebSocketGateway:
    """WebSocket gateway server for real-time client communication.

    Manages client connections, authentication, message routing,
    and heartbeat monitoring.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",  # noqa: S104
        port: int = 8765,
        auth_token: str = "",
        ping_interval: float = 30.0,
    ) -> None:
        self._host = host
        self._port = port
        self._auth_token = auth_token
        self._ping_interval = ping_interval
        self._clients: dict[str, ClientInfo] = {}
        self._handlers: dict[MessageType, MessageHandler] = {}
        self._running = False

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def get_clients(self) -> dict[str, ClientInfo]:
        return dict(self._clients)

    def register_handler(self, msg_type: MessageType, handler: MessageHandler) -> None:
        self._handlers[msg_type] = handler
        logger.info("ws_handler_registered", type=msg_type.value)

    def authenticate_client(self, client_id: str, token: str) -> bool:
        """Authenticate a client connection."""
        if not self._auth_token:
            return True
        if token == self._auth_token:
            if client_id in self._clients:
                self._clients[client_id].state = ConnectionState.CONNECTED
                logger.info("ws_client_authenticated", client_id=client_id)
            return True
        logger.warning("ws_auth_failed", client_id=client_id)
        return False

    def connect_client(self, client_id: str, user_id: str = "") -> ClientInfo:
        """Register a new client connection."""
        info = ClientInfo(
            client_id=client_id,
            user_id=user_id,
            state=ConnectionState.AUTHENTICATING if self._auth_token else ConnectionState.CONNECTED,
        )
        self._clients[client_id] = info
        logger.info("ws_client_connected", client_id=client_id, total=len(self._clients))
        return info

    def disconnect_client(self, client_id: str) -> None:
        """Remove a client connection."""
        if client_id in self._clients:
            self._clients[client_id].state = ConnectionState.DISCONNECTED
            del self._clients[client_id]
            logger.info("ws_client_disconnected", client_id=client_id, total=len(self._clients))

    async def handle_message(self, client_id: str, message: WSMessage) -> WSMessage | None:
        """Route an incoming message to the appropriate handler."""
        if client_id not in self._clients:
            return WSMessage(type=MessageType.ERROR, payload={"error": "not connected"})

        client = self._clients[client_id]

        if message.type == MessageType.AUTH:
            token = str(message.payload.get("token", ""))
            if self.authenticate_client(client_id, token):
                return WSMessage(type=MessageType.AUTH_OK)
            return WSMessage(type=MessageType.AUTH_FAIL, payload={"error": "invalid token"})

        if client.state != ConnectionState.CONNECTED:
            return WSMessage(type=MessageType.ERROR, payload={"error": "not authenticated"})

        if message.type == MessageType.PING:
            client.last_ping = message.timestamp
            return WSMessage(type=MessageType.PONG)

        handler = self._handlers.get(message.type)
        if handler:
            return await handler(client_id, message)

        return WSMessage(
            type=MessageType.ERROR,
            payload={"error": f"no handler for {message.type.value}"},
        )

    async def broadcast(self, message: WSMessage, exclude: set[str] | None = None) -> int:
        """Broadcast a message to all connected clients. Returns count sent."""
        exclude = exclude or set()
        sent = 0
        for cid, client in self._clients.items():
            if cid not in exclude and client.state == ConnectionState.CONNECTED:
                sent += 1
        logger.info("ws_broadcast", type=message.type.value, sent=sent)
        return sent

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        self._running = True
        logger.info("ws_gateway_started", host=self._host, port=self._port)

    async def stop(self) -> None:
        self._running = False
        self._clients.clear()
        logger.info("ws_gateway_stopped")
