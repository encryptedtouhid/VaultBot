"""Unit tests for deep gateway features."""

from __future__ import annotations

import pytest

from vaultbot.gateway.auth import Role
from vaultbot.gateway.openai_compat import (
    OpenAIChoice,
    OpenAIResponse,
    OpenAIUsage,
    format_sse_chunk,
    resolve_model,
)
from vaultbot.gateway.rpc_router import RPCMethod, RPCRequest, RPCRouter
from vaultbot.gateway.session_gateway import SessionGateway


class TestRPCRouter:
    @pytest.mark.asyncio
    async def test_register_and_dispatch(self) -> None:
        router = RPCRouter()

        async def health_handler() -> dict[str, object]:
            return {"status": "ok"}

        router.register(RPCMethod(name="health", handler=health_handler))
        resp = await router.dispatch(RPCRequest(method="health"))
        assert resp.success is True
        assert resp.result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_unknown_method(self) -> None:
        router = RPCRouter()
        resp = await router.dispatch(RPCRequest(method="nope"))
        assert resp.success is False
        assert "Unknown" in resp.error

    @pytest.mark.asyncio
    async def test_role_check(self) -> None:
        router = RPCRouter()

        async def admin_handler() -> dict[str, object]:
            return {"admin": True}

        router.register(RPCMethod(name="admin.do", handler=admin_handler, required_role=Role.ADMIN))
        resp = await router.dispatch(RPCRequest(method="admin.do", caller_role=Role.READ))
        assert resp.success is False
        assert "Insufficient" in resp.error

        resp = await router.dispatch(RPCRequest(method="admin.do", caller_role=Role.ADMIN))
        assert resp.success is True

    @pytest.mark.asyncio
    async def test_handler_error(self) -> None:
        router = RPCRouter()

        async def bad_handler() -> dict[str, object]:
            raise RuntimeError("boom")

        router.register(RPCMethod(name="bad", handler=bad_handler))
        resp = await router.dispatch(RPCRequest(method="bad"))
        assert resp.success is False
        assert "boom" in resp.error

    def test_list_methods(self) -> None:
        router = RPCRouter()

        async def handler() -> dict[str, object]:
            return {}

        router.register(RPCMethod(name="a", handler=handler, required_role=Role.READ))
        router.register(RPCMethod(name="b", handler=handler, required_role=Role.ADMIN))
        read_methods = router.list_methods(role=Role.READ)
        assert len(read_methods) == 1
        admin_methods = router.list_methods(role=Role.ADMIN)
        assert len(admin_methods) == 2


class TestOpenAICompat:
    def test_resolve_known_model(self) -> None:
        provider, model = resolve_model("gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_resolve_unknown_model(self) -> None:
        provider, model = resolve_model("custom-model")
        assert provider == "compatible"

    def test_response_to_dict(self) -> None:
        resp = OpenAIResponse(
            id="chatcmpl-123",
            model="gpt-4o",
            choices=[OpenAIChoice(message={"role": "assistant", "content": "hi"})],
            usage=OpenAIUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
        d = resp.to_dict()
        assert d["model"] == "gpt-4o"
        assert d["choices"][0]["message"]["content"] == "hi"
        assert d["usage"]["total_tokens"] == 15

    def test_format_sse_chunk(self) -> None:
        chunk = format_sse_chunk("id1", "gpt-4o", "hello")
        assert "data:" in chunk
        assert "hello" in chunk

    def test_format_sse_finish(self) -> None:
        chunk = format_sse_chunk("id1", "gpt-4o", "", finish=True)
        assert "[DONE]" in chunk


class TestSessionGateway:
    def test_create_and_get(self) -> None:
        gw = SessionGateway()
        gw.create("s1", agent_id="a1")
        assert gw.get("s1") is not None
        assert gw.session_count == 1

    def test_subscribe_unsubscribe(self) -> None:
        gw = SessionGateway()
        gw.create("s1")
        gw.subscribe("s1", "client1")
        assert "client1" in gw.get_subscribers("s1")
        gw.unsubscribe("s1", "client1")
        assert "client1" not in gw.get_subscribers("s1")

    def test_record_message(self) -> None:
        gw = SessionGateway()
        gw.create("s1")
        gw.record_message("s1")
        assert gw.get("s1").message_count == 1

    def test_delete(self) -> None:
        gw = SessionGateway()
        gw.create("s1")
        assert gw.delete("s1") is True
        assert gw.session_count == 0

    def test_list_by_agent(self) -> None:
        gw = SessionGateway()
        gw.create("s1", agent_id="a1")
        gw.create("s2", agent_id="a2")
        gw.create("s3", agent_id="a1")
        assert len(gw.list_sessions("a1")) == 2
