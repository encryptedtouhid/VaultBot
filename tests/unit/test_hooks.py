"""Unit tests for hooks engine."""

from __future__ import annotations

import pytest

from vaultbot.hooks.engine import HookContext, HookEngine, HookEvent, HookResult


class TestHookEngine:
    def test_register_hook(self) -> None:
        engine = HookEngine()

        async def handler(ctx: HookContext) -> HookResult:
            return HookResult()

        engine.register("test_hook", HookEvent.BEFORE_TOOL, handler)
        hooks = engine.list_hooks(HookEvent.BEFORE_TOOL)
        assert len(hooks) == 1
        assert hooks[0].name == "test_hook"

    def test_unregister_hook(self) -> None:
        engine = HookEngine()

        async def handler(ctx: HookContext) -> HookResult:
            return HookResult()

        engine.register("h1", HookEvent.BEFORE_TOOL, handler)
        assert engine.unregister("h1") is True
        assert len(engine.list_hooks(HookEvent.BEFORE_TOOL)) == 0

    def test_unregister_nonexistent(self) -> None:
        engine = HookEngine()
        assert engine.unregister("nonexistent") is False

    @pytest.mark.asyncio
    async def test_execute_allows(self) -> None:
        engine = HookEngine()

        async def allowing(ctx: HookContext) -> HookResult:
            return HookResult(allow=True)

        engine.register("allow", HookEvent.BEFORE_TOOL, allowing)
        result = await engine.execute(HookContext(event=HookEvent.BEFORE_TOOL))
        assert result.allow is True
        assert engine.execution_count == 1

    @pytest.mark.asyncio
    async def test_execute_blocks(self) -> None:
        engine = HookEngine()

        async def blocking(ctx: HookContext) -> HookResult:
            return HookResult(allow=False, reason="dangerous tool")

        engine.register("block", HookEvent.BEFORE_TOOL, blocking)
        result = await engine.execute(HookContext(event=HookEvent.BEFORE_TOOL))
        assert result.allow is False
        assert result.reason == "dangerous tool"

    @pytest.mark.asyncio
    async def test_execute_priority_order(self) -> None:
        engine = HookEngine()
        execution_order: list[str] = []

        async def hook_a(ctx: HookContext) -> HookResult:
            execution_order.append("a")
            return HookResult()

        async def hook_b(ctx: HookContext) -> HookResult:
            execution_order.append("b")
            return HookResult()

        engine.register("b", HookEvent.BEFORE_TOOL, hook_b, priority=10)
        engine.register("a", HookEvent.BEFORE_TOOL, hook_a, priority=1)

        await engine.execute(HookContext(event=HookEvent.BEFORE_TOOL))
        assert execution_order == ["a", "b"]  # Lower priority first

    @pytest.mark.asyncio
    async def test_execute_stops_on_block(self) -> None:
        engine = HookEngine()
        reached: list[str] = []

        async def blocker(ctx: HookContext) -> HookResult:
            reached.append("blocker")
            return HookResult(allow=False, reason="blocked")

        async def after(ctx: HookContext) -> HookResult:
            reached.append("after")
            return HookResult()

        engine.register("blocker", HookEvent.BEFORE_TOOL, blocker, priority=1)
        engine.register("after", HookEvent.BEFORE_TOOL, after, priority=2)

        await engine.execute(HookContext(event=HookEvent.BEFORE_TOOL))
        assert reached == ["blocker"]  # "after" not reached

    @pytest.mark.asyncio
    async def test_disabled_hook_skipped(self) -> None:
        engine = HookEngine()

        async def handler(ctx: HookContext) -> HookResult:
            return HookResult(allow=False)

        engine.register("h1", HookEvent.BEFORE_TOOL, handler)
        engine.disable("h1")

        result = await engine.execute(HookContext(event=HookEvent.BEFORE_TOOL))
        assert result.allow is True  # Disabled hook didn't run

    @pytest.mark.asyncio
    async def test_enable_hook(self) -> None:
        engine = HookEngine()

        async def handler(ctx: HookContext) -> HookResult:
            return HookResult(allow=False)

        engine.register("h1", HookEvent.BEFORE_TOOL, handler)
        engine.disable("h1")
        engine.enable("h1")

        result = await engine.execute(HookContext(event=HookEvent.BEFORE_TOOL))
        assert result.allow is False

    @pytest.mark.asyncio
    async def test_error_in_hook_continues(self) -> None:
        engine = HookEngine()

        async def bad_hook(ctx: HookContext) -> HookResult:
            raise RuntimeError("hook crashed")

        async def good_hook(ctx: HookContext) -> HookResult:
            return HookResult(allow=True)

        engine.register("bad", HookEvent.BEFORE_TOOL, bad_hook, priority=1)
        engine.register("good", HookEvent.BEFORE_TOOL, good_hook, priority=2)

        result = await engine.execute(HookContext(event=HookEvent.BEFORE_TOOL))
        assert result.allow is True

    def test_list_all_hooks(self) -> None:
        engine = HookEngine()

        async def handler(ctx: HookContext) -> HookResult:
            return HookResult()

        engine.register("h1", HookEvent.BEFORE_TOOL, handler)
        engine.register("h2", HookEvent.AFTER_TOOL, handler)

        all_hooks = engine.list_hooks()
        assert len(all_hooks) == 2

    @pytest.mark.asyncio
    async def test_no_hooks_allows(self) -> None:
        engine = HookEngine()
        result = await engine.execute(HookContext(event=HookEvent.ON_STARTUP))
        assert result.allow is True

    @pytest.mark.asyncio
    async def test_hook_with_context_data(self) -> None:
        engine = HookEngine()
        received_data: dict = {}

        async def handler(ctx: HookContext) -> HookResult:
            received_data.update(ctx.data)
            return HookResult()

        engine.register("h1", HookEvent.BEFORE_TOOL, handler)
        await engine.execute(HookContext(
            event=HookEvent.BEFORE_TOOL,
            tool_name="web_search",
            data={"query": "test"},
        ))
        assert received_data == {"query": "test"}
