"""Unit tests for routing engine."""

from __future__ import annotations

from vaultbot.core.route_resolver import (
    BindingScope,
    ChatType,
    RouteBinding,
    RouteResolver,
    derive_session_key,
    normalize_account,
)


class TestHelpers:
    def test_derive_session_key(self) -> None:
        key = derive_session_key("agent1", ChatType.DM, "user123")
        assert key == "agent:agent1:dm:user123"

    def test_normalize_account(self) -> None:
        assert normalize_account("  UserName  ") == "username"
        assert normalize_account("UPPER") == "upper"


class TestRouteResolver:
    def test_add_binding(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(RouteBinding(scope=BindingScope.DEFAULT, agent_id="a1"))
        assert resolver.binding_count == 1

    def test_resolve_default(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(RouteBinding(scope=BindingScope.DEFAULT, agent_id="a1"))
        result = resolver.resolve("general")
        assert result is not None
        assert result.agent_id == "a1"

    def test_resolve_channel_over_default(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(RouteBinding(scope=BindingScope.DEFAULT, agent_id="default"))
        resolver.add_binding(
            RouteBinding(scope=BindingScope.CHANNEL, agent_id="specific", channel="support")
        )
        result = resolver.resolve("support")
        assert result is not None
        assert result.agent_id == "specific"

    def test_resolve_peer_highest_priority(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(RouteBinding(scope=BindingScope.DEFAULT, agent_id="default"))
        resolver.add_binding(
            RouteBinding(scope=BindingScope.EXPLICIT_PEER, agent_id="peer_agent", peer="user1")
        )
        result = resolver.resolve("general", peer="user1")
        assert result is not None
        assert result.agent_id == "peer_agent"

    def test_resolve_role(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(
            RouteBinding(scope=BindingScope.GUILD_ROLES, agent_id="admin_agent", role="admin")
        )
        result = resolver.resolve("general", role="admin")
        assert result is not None
        assert result.agent_id == "admin_agent"

    def test_resolve_no_match(self) -> None:
        resolver = RouteResolver()
        assert resolver.resolve("unknown") is None

    def test_resolve_session_key(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(RouteBinding(scope=BindingScope.DEFAULT, agent_id="a1"))
        result = resolver.resolve("general", chat_type=ChatType.DM, peer="user1")
        assert result is not None
        assert "agent:a1:dm:" in result.session_key

    def test_remove_binding(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(RouteBinding(scope=BindingScope.DEFAULT, agent_id="a1"))
        removed = resolver.remove_binding("a1")
        assert removed == 1
        assert resolver.binding_count == 0

    def test_account_binding(self) -> None:
        resolver = RouteResolver()
        resolver.add_binding(
            RouteBinding(scope=BindingScope.ACCOUNT, agent_id="acct_agent", account="MyAccount")
        )
        result = resolver.resolve("general", account="myaccount")
        assert result is not None
        assert result.agent_id == "acct_agent"
