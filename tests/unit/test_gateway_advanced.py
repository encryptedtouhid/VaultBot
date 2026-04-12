"""Unit tests for enterprise gateway."""

from __future__ import annotations

from vaultbot.gateway.auth import AuthMode, GatewayAuth, Role
from vaultbot.gateway.event_bus import EventBus, GatewayEvent
from vaultbot.gateway.network import (
    get_local_ip,
    ip_in_cidr,
    is_loopback,
    is_private_ip,
    validate_origin,
)
from vaultbot.gateway.node_manager import NodeManager, NodeStatus

# ---------------------------------------------------------------------------
# Gateway Auth
# ---------------------------------------------------------------------------


class TestGatewayAuth:
    def test_no_auth(self) -> None:
        auth = GatewayAuth()
        result = auth.authenticate(AuthMode.NONE, "")
        assert result.authenticated is True

    def test_token_auth_valid(self) -> None:
        auth = GatewayAuth(token="secret")
        result = auth.authenticate(AuthMode.TOKEN, "secret")
        assert result.authenticated is True
        assert result.role == Role.ADMIN

    def test_token_auth_invalid(self) -> None:
        auth = GatewayAuth(token="secret")
        result = auth.authenticate(AuthMode.TOKEN, "wrong")
        assert result.authenticated is False

    def test_token_auth_no_token_configured(self) -> None:
        auth = GatewayAuth()
        result = auth.authenticate(AuthMode.TOKEN, "anything")
        assert result.authenticated is True

    def test_password_auth_valid(self) -> None:
        auth = GatewayAuth(password="mypass")
        result = auth.authenticate(AuthMode.PASSWORD, "mypass")
        assert result.authenticated is True

    def test_password_auth_invalid(self) -> None:
        auth = GatewayAuth(password="mypass")
        result = auth.authenticate(AuthMode.PASSWORD, "wrong")
        assert result.authenticated is False

    def test_device_pair_auth(self) -> None:
        auth = GatewayAuth()
        auth.register_device("dev1", "token123")
        auth.approve_device("dev1")
        result = auth.authenticate(AuthMode.DEVICE_PAIR, "token123", device_id="dev1")
        assert result.authenticated is True

    def test_device_not_approved(self) -> None:
        auth = GatewayAuth()
        auth.register_device("dev1", "token123")
        result = auth.authenticate(AuthMode.DEVICE_PAIR, "token123", device_id="dev1")
        assert result.authenticated is False

    def test_revoke_device(self) -> None:
        auth = GatewayAuth()
        auth.register_device("dev1", "token123")
        assert auth.revoke_device("dev1") is True
        assert auth.revoke_device("dev1") is False

    def test_rate_limit(self) -> None:
        auth = GatewayAuth()
        for _ in range(5):
            assert auth.check_rate_limit("c1", max_per_minute=5) is True
        assert auth.check_rate_limit("c1", max_per_minute=5) is False

    def test_method_access_admin(self) -> None:
        auth = GatewayAuth()
        assert auth.check_method_access(Role.ADMIN, "system.shutdown") is True

    def test_method_access_write(self) -> None:
        auth = GatewayAuth()
        assert auth.check_method_access(Role.WRITE, "chat.send") is True
        assert auth.check_method_access(Role.WRITE, "system.shutdown") is False

    def test_method_access_read(self) -> None:
        auth = GatewayAuth()
        assert auth.check_method_access(Role.READ, "chat.send") is False
        assert auth.check_method_access(Role.READ, "session.list") is True


# ---------------------------------------------------------------------------
# Node Manager
# ---------------------------------------------------------------------------


class TestNodeManager:
    def test_register_node(self) -> None:
        mgr = NodeManager()
        node = mgr.register("n1", "Node 1", "192.168.1.1")
        assert node.name == "Node 1"
        assert mgr.node_count == 1

    def test_unregister(self) -> None:
        mgr = NodeManager()
        mgr.register("n1")
        assert mgr.unregister("n1") is True
        assert mgr.node_count == 0

    def test_heartbeat(self) -> None:
        mgr = NodeManager()
        mgr.register("n1")
        assert mgr.heartbeat("n1") is True
        assert mgr.get_node("n1").status == NodeStatus.HEALTHY

    def test_health_check_degraded(self) -> None:
        mgr = NodeManager(heartbeat_timeout=0)
        mgr.register("n1")
        mgr.heartbeat("n1")
        mgr.get_node("n1").last_heartbeat = 0
        health = mgr.check_health()
        assert health["n1"] == NodeStatus.DEGRADED

    def test_capabilities(self) -> None:
        mgr = NodeManager()
        mgr.register("n1")
        mgr.set_capabilities("n1", ["chat", "exec"])
        nodes = mgr.find_by_capability("chat")
        assert len(nodes) == 1

    def test_list_by_status(self) -> None:
        mgr = NodeManager()
        mgr.register("n1")
        mgr.heartbeat("n1")
        mgr.register("n2")
        healthy = mgr.list_nodes(NodeStatus.HEALTHY)
        assert len(healthy) == 1


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


class TestEventBus:
    def test_publish_subscribe(self) -> None:
        bus = EventBus()
        received: list[str] = []
        bus.subscribe("chat", lambda e: received.append(e.event_type))
        bus.publish(GatewayEvent(event_type="chat", payload={"text": "hi"}))
        assert received == ["chat"]

    def test_wildcard_subscriber(self) -> None:
        bus = EventBus()
        received: list[str] = []
        bus.subscribe("*", lambda e: received.append(e.event_type))
        bus.publish(GatewayEvent(event_type="any_event"))
        assert received == ["any_event"]

    def test_unsubscribe(self) -> None:
        bus = EventBus()
        cb = lambda e: None  # noqa: E731
        bus.subscribe("chat", cb)
        assert bus.unsubscribe("chat", cb) is True
        assert bus.subscriber_count("chat") == 0

    def test_event_count(self) -> None:
        bus = EventBus()
        bus.publish(GatewayEvent(event_type="a"))
        bus.publish(GatewayEvent(event_type="b"))
        assert bus.event_count == 2

    def test_handler_error_doesnt_crash(self) -> None:
        bus = EventBus()

        def bad_handler(e: GatewayEvent) -> None:
            raise RuntimeError("boom")

        bus.subscribe("test", bad_handler)
        count = bus.publish(GatewayEvent(event_type="test"))
        assert count == 1  # Still counted


# ---------------------------------------------------------------------------
# Network Utilities
# ---------------------------------------------------------------------------


class TestNetwork:
    def test_get_local_ip(self) -> None:
        ip = get_local_ip()
        assert ip  # Should return something

    def test_is_private(self) -> None:
        assert is_private_ip("192.168.1.1") is True
        assert is_private_ip("8.8.8.8") is False

    def test_is_loopback(self) -> None:
        assert is_loopback("127.0.0.1") is True
        assert is_loopback("192.168.1.1") is False

    def test_ip_in_cidr(self) -> None:
        assert ip_in_cidr("192.168.1.5", "192.168.1.0/24") is True
        assert ip_in_cidr("10.0.0.1", "192.168.1.0/24") is False

    def test_validate_origin(self) -> None:
        assert validate_origin("http://localhost", ["*"]) is True
        assert validate_origin("http://evil.com", ["http://localhost"]) is False
        assert validate_origin("http://localhost", ["http://localhost"]) is True
        assert validate_origin("anything", []) is True
