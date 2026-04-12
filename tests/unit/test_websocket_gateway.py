"""Unit tests for WebSocket gateway, protocol, and control plane."""

from __future__ import annotations

import pytest

from vaultbot.gateway.control_plane import (
    ControlCommand,
    ControlPlane,
    InstanceStatus,
)
from vaultbot.gateway.protocol import (
    ClientInfo,
    ConnectionState,
    MessageType,
    WSMessage,
)
from vaultbot.gateway.websocket_server import WebSocketGateway

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_message_type_enum(self) -> None:
        assert MessageType.CHAT.value == "chat"
        assert MessageType.AUTH.value == "auth"

    def test_connection_state_enum(self) -> None:
        assert ConnectionState.CONNECTED.value == "connected"

    def test_ws_message_defaults(self) -> None:
        msg = WSMessage(type=MessageType.PING)
        assert msg.type == MessageType.PING
        assert msg.payload == {}
        assert msg.id
        assert msg.timestamp > 0

    def test_ws_message_to_dict(self) -> None:
        msg = WSMessage(type=MessageType.CHAT, payload={"text": "hello"})
        d = msg.to_dict()
        assert d["type"] == "chat"
        assert d["payload"]["text"] == "hello"

    def test_ws_message_from_dict(self) -> None:
        msg = WSMessage.from_dict({"type": "pong", "id": "abc", "timestamp": 1.0, "payload": {}})
        assert msg.type == MessageType.PONG
        assert msg.id == "abc"

    def test_client_info_defaults(self) -> None:
        info = ClientInfo(client_id="c1")
        assert info.state == ConnectionState.CONNECTING
        assert info.user_id == ""


# ---------------------------------------------------------------------------
# WebSocket Gateway
# ---------------------------------------------------------------------------


class TestWebSocketGateway:
    def test_init_defaults(self) -> None:
        gw = WebSocketGateway()
        assert gw.host == "0.0.0.0"
        assert gw.port == 8765
        assert gw.client_count == 0

    def test_connect_client(self) -> None:
        gw = WebSocketGateway()
        info = gw.connect_client("c1", "user1")
        assert info.client_id == "c1"
        assert gw.client_count == 1

    def test_disconnect_client(self) -> None:
        gw = WebSocketGateway()
        gw.connect_client("c1")
        gw.disconnect_client("c1")
        assert gw.client_count == 0

    def test_disconnect_unknown_client(self) -> None:
        gw = WebSocketGateway()
        gw.disconnect_client("nonexistent")
        assert gw.client_count == 0

    def test_auth_no_token_required(self) -> None:
        gw = WebSocketGateway()
        assert gw.authenticate_client("c1", "") is True

    def test_auth_with_valid_token(self) -> None:
        gw = WebSocketGateway(auth_token="secret")
        gw.connect_client("c1")
        assert gw.authenticate_client("c1", "secret") is True

    def test_auth_with_invalid_token(self) -> None:
        gw = WebSocketGateway(auth_token="secret")
        gw.connect_client("c1")
        assert gw.authenticate_client("c1", "wrong") is False

    @pytest.mark.asyncio
    async def test_handle_auth_message(self) -> None:
        gw = WebSocketGateway(auth_token="secret")
        gw.connect_client("c1")
        msg = WSMessage(type=MessageType.AUTH, payload={"token": "secret"})
        resp = await gw.handle_message("c1", msg)
        assert resp is not None
        assert resp.type == MessageType.AUTH_OK

    @pytest.mark.asyncio
    async def test_handle_auth_fail(self) -> None:
        gw = WebSocketGateway(auth_token="secret")
        gw.connect_client("c1")
        msg = WSMessage(type=MessageType.AUTH, payload={"token": "wrong"})
        resp = await gw.handle_message("c1", msg)
        assert resp is not None
        assert resp.type == MessageType.AUTH_FAIL

    @pytest.mark.asyncio
    async def test_handle_ping(self) -> None:
        gw = WebSocketGateway()
        gw.connect_client("c1")
        msg = WSMessage(type=MessageType.PING)
        resp = await gw.handle_message("c1", msg)
        assert resp is not None
        assert resp.type == MessageType.PONG

    @pytest.mark.asyncio
    async def test_handle_unknown_client(self) -> None:
        gw = WebSocketGateway()
        msg = WSMessage(type=MessageType.CHAT)
        resp = await gw.handle_message("unknown", msg)
        assert resp is not None
        assert resp.type == MessageType.ERROR

    @pytest.mark.asyncio
    async def test_handle_unauthenticated(self) -> None:
        gw = WebSocketGateway(auth_token="secret")
        gw.connect_client("c1")
        msg = WSMessage(type=MessageType.CHAT, payload={"text": "hi"})
        resp = await gw.handle_message("c1", msg)
        assert resp is not None
        assert resp.type == MessageType.ERROR

    @pytest.mark.asyncio
    async def test_handle_with_custom_handler(self) -> None:
        gw = WebSocketGateway()
        gw.connect_client("c1")

        async def chat_handler(cid: str, msg: WSMessage) -> WSMessage:
            return WSMessage(type=MessageType.CHAT_RESPONSE, payload={"reply": "hi"})

        gw.register_handler(MessageType.CHAT, chat_handler)
        msg = WSMessage(type=MessageType.CHAT, payload={"text": "hello"})
        resp = await gw.handle_message("c1", msg)
        assert resp is not None
        assert resp.type == MessageType.CHAT_RESPONSE

    @pytest.mark.asyncio
    async def test_broadcast(self) -> None:
        gw = WebSocketGateway()
        gw.connect_client("c1")
        gw.connect_client("c2")
        msg = WSMessage(type=MessageType.EVENT, payload={"event": "update"})
        sent = await gw.broadcast(msg)
        assert sent == 2

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self) -> None:
        gw = WebSocketGateway()
        gw.connect_client("c1")
        gw.connect_client("c2")
        msg = WSMessage(type=MessageType.EVENT)
        sent = await gw.broadcast(msg, exclude={"c1"})
        assert sent == 1

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        gw = WebSocketGateway()
        assert not gw.is_running
        await gw.start()
        assert gw.is_running
        await gw.stop()
        assert not gw.is_running


# ---------------------------------------------------------------------------
# Control Plane
# ---------------------------------------------------------------------------


class TestControlPlane:
    def test_register_instance(self) -> None:
        cp = ControlPlane()
        inst = cp.register_instance("bot1", "MyBot")
        assert inst.name == "MyBot"
        assert cp.instance_count == 1

    def test_unregister_instance(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1")
        assert cp.unregister_instance("bot1") is True
        assert cp.instance_count == 0

    def test_unregister_unknown(self) -> None:
        cp = ControlPlane()
        assert cp.unregister_instance("nope") is False

    def test_start_instance(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1")
        result = cp.start_instance("bot1")
        assert result.success is True
        assert cp.get_instances()["bot1"].status == InstanceStatus.RUNNING

    def test_stop_instance(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1")
        cp.start_instance("bot1")
        result = cp.stop_instance("bot1")
        assert result.success is True
        assert cp.get_instances()["bot1"].status == InstanceStatus.STOPPED

    def test_start_unknown(self) -> None:
        cp = ControlPlane()
        result = cp.start_instance("nope")
        assert result.success is False

    def test_heartbeat(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1")
        cp.start_instance("bot1")
        assert cp.heartbeat("bot1") is True
        assert cp.heartbeat("nope") is False

    def test_check_health_degraded(self) -> None:
        cp = ControlPlane(heartbeat_timeout=0.0)
        cp.register_instance("bot1")
        cp.start_instance("bot1")
        cp.get_instances()["bot1"].last_heartbeat = 0.0
        health = cp.check_health()
        assert health["bot1"] == InstanceStatus.DEGRADED

    def test_execute_command_start(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1")
        result = cp.execute_command(ControlCommand(action="start", target="bot1"))
        assert result.success is True

    def test_execute_command_stop(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1")
        cp.start_instance("bot1")
        result = cp.execute_command(ControlCommand(action="stop", target="bot1"))
        assert result.success is True

    def test_execute_command_status(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1")
        result = cp.execute_command(ControlCommand(action="status"))
        assert result.success is True
        assert "instances" in result.data

    def test_execute_command_list(self) -> None:
        cp = ControlPlane()
        cp.register_instance("bot1", "MyBot")
        result = cp.execute_command(ControlCommand(action="list"))
        assert result.success is True

    def test_execute_command_unknown(self) -> None:
        cp = ControlPlane()
        result = cp.execute_command(ControlCommand(action="nope"))
        assert result.success is False
