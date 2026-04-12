"""Unit tests for pluggable context engine."""

from __future__ import annotations

import pytest

from vaultbot.core.context_engine import (
    ContextEngine,
    ContextEngineRegistry,
    InMemoryContextEngine,
)
from vaultbot.core.message import ChatMessage
from vaultbot.core.transcript import TranscriptManager


class TestInMemoryContextEngine:
    def test_is_context_engine(self) -> None:
        assert isinstance(InMemoryContextEngine(), ContextEngine)

    @pytest.mark.asyncio
    async def test_bootstrap_and_ingest(self) -> None:
        engine = InMemoryContextEngine()
        await engine.bootstrap("s1")
        await engine.ingest("s1", ChatMessage(role="user", content="hello"))
        assert engine.message_count("s1") == 1

    @pytest.mark.asyncio
    async def test_assemble_within_budget(self) -> None:
        engine = InMemoryContextEngine()
        await engine.bootstrap("s1")
        await engine.ingest("s1", ChatMessage(role="user", content="hello world"))
        result = await engine.assemble("s1", token_budget=1000)
        assert len(result.messages) == 1
        assert not result.truncated

    @pytest.mark.asyncio
    async def test_assemble_truncated(self) -> None:
        engine = InMemoryContextEngine()
        await engine.bootstrap("s1")
        for i in range(50):
            await engine.ingest("s1", ChatMessage(role="user", content=f"msg {i} " * 20))
        result = await engine.assemble("s1", token_budget=100)
        assert result.truncated

    @pytest.mark.asyncio
    async def test_compact(self) -> None:
        engine = InMemoryContextEngine()
        await engine.bootstrap("s1")
        for i in range(20):
            await engine.ingest("s1", ChatMessage(role="user", content=f"msg {i}"))
        freed = await engine.compact("s1")
        assert freed > 0
        assert engine.message_count("s1") == 10

    @pytest.mark.asyncio
    async def test_compact_small_session(self) -> None:
        engine = InMemoryContextEngine()
        await engine.bootstrap("s1")
        await engine.ingest("s1", ChatMessage(role="user", content="hello"))
        freed = await engine.compact("s1")
        assert freed == 0

    @pytest.mark.asyncio
    async def test_max_messages(self) -> None:
        engine = InMemoryContextEngine(max_messages=5)
        await engine.bootstrap("s1")
        for i in range(10):
            await engine.ingest("s1", ChatMessage(role="user", content=f"msg {i}"))
        assert engine.message_count("s1") == 5


class TestContextEngineRegistry:
    def test_register_and_create(self) -> None:
        reg = ContextEngineRegistry()
        reg.register("memory", InMemoryContextEngine)
        engine = reg.create("memory")
        assert isinstance(engine, InMemoryContextEngine)

    def test_create_default(self) -> None:
        reg = ContextEngineRegistry()
        reg.register("memory", InMemoryContextEngine)
        engine = reg.create()
        assert isinstance(engine, InMemoryContextEngine)

    def test_create_unknown_raises(self) -> None:
        reg = ContextEngineRegistry()
        with pytest.raises(ValueError, match="Unknown context engine"):
            reg.create("nope")

    def test_list_engines(self) -> None:
        reg = ContextEngineRegistry()
        reg.register("a", InMemoryContextEngine)
        reg.register("b", InMemoryContextEngine)
        assert set(reg.list_engines()) == {"a", "b"}


class TestTranscriptManager:
    def test_create_version(self) -> None:
        mgr = TranscriptManager()
        v = mgr.create_version("s1", message_count=5)
        assert v.message_count == 5
        assert mgr.version_count("s1") == 1

    def test_get_latest(self) -> None:
        mgr = TranscriptManager()
        mgr.create_version("s1")
        v2 = mgr.create_version("s1")
        assert mgr.get_latest("s1").version_id == v2.version_id

    def test_branch(self) -> None:
        mgr = TranscriptManager()
        v1 = mgr.create_version("s1", message_count=10)
        branch = mgr.branch("s1")
        assert branch is not None
        assert branch.parent_id == v1.version_id
        assert mgr.version_count("s1") == 2

    def test_branch_empty(self) -> None:
        mgr = TranscriptManager()
        assert mgr.branch("empty") is None
