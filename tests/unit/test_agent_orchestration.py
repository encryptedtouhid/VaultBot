"""Unit tests for agent orchestration."""

from __future__ import annotations

from vaultbot.agents.auth_profiles import AuthProfile, AuthProfileManager, AuthType, ProfileState
from vaultbot.agents.model_switcher import ModelOption, ModelSwitcher, ModelSwitcherConfig
from vaultbot.agents.orchestrator import AgentConfig, AgentOrchestrator, AgentState


class TestAgentOrchestrator:
    def test_register(self) -> None:
        orch = AgentOrchestrator()
        config = AgentConfig(agent_id="a1", name="Agent 1", model="gpt-4o")
        orch.register(config)
        assert orch.agent_count == 1

    def test_resolve_default(self) -> None:
        orch = AgentOrchestrator()
        orch.register(AgentConfig(agent_id="a1"))
        assert orch.resolve() is not None
        assert orch.resolve().config.agent_id == "a1"

    def test_resolve_specific(self) -> None:
        orch = AgentOrchestrator()
        orch.register(AgentConfig(agent_id="a1"))
        orch.register(AgentConfig(agent_id="a2"))
        assert orch.resolve("a2").config.agent_id == "a2"

    def test_start_stop(self) -> None:
        orch = AgentOrchestrator()
        orch.register(AgentConfig(agent_id="a1"))
        assert orch.start("a1") is True
        assert orch.get("a1").state == AgentState.RUNNING
        assert orch.stop("a1") is True
        assert orch.get("a1").state == AgentState.STOPPED

    def test_spawn_child(self) -> None:
        orch = AgentOrchestrator()
        orch.register(AgentConfig(agent_id="parent"))
        child = orch.spawn_child("parent", AgentConfig(agent_id="child"))
        assert child is not None
        assert child.parent_id == "parent"
        assert "child" in orch.get("parent").children

    def test_get_children(self) -> None:
        orch = AgentOrchestrator()
        orch.register(AgentConfig(agent_id="p"))
        orch.spawn_child("p", AgentConfig(agent_id="c1"))
        orch.spawn_child("p", AgentConfig(agent_id="c2"))
        assert len(orch.get_children("p")) == 2

    def test_unregister(self) -> None:
        orch = AgentOrchestrator()
        orch.register(AgentConfig(agent_id="a1"))
        assert orch.unregister("a1") is True
        assert orch.agent_count == 0

    def test_list_by_state(self) -> None:
        orch = AgentOrchestrator()
        orch.register(AgentConfig(agent_id="a1"))
        orch.register(AgentConfig(agent_id="a2"))
        orch.start("a1")
        assert len(orch.list_agents(AgentState.RUNNING)) == 1


class TestAuthProfileManager:
    def test_add_and_get(self) -> None:
        mgr = AuthProfileManager()
        mgr.add(AuthProfile(name="openai", auth_type=AuthType.API_KEY, credential="sk-xxx"))
        assert mgr.get("openai") is not None

    def test_use(self) -> None:
        mgr = AuthProfileManager()
        mgr.add(AuthProfile(name="openai"))
        assert mgr.use("openai") is True

    def test_mark_failed_cooldown(self) -> None:
        mgr = AuthProfileManager()
        mgr.add(AuthProfile(name="openai"))
        mgr.mark_failed("openai", cooldown_seconds=9999)
        profile = mgr.get("openai")
        assert profile.state == ProfileState.COOLDOWN

    def test_get_best(self) -> None:
        mgr = AuthProfileManager()
        mgr.add(AuthProfile(name="old", last_used=1.0))
        mgr.add(AuthProfile(name="recent", last_used=999.0))
        best = mgr.get_best()
        assert best.name == "recent"

    def test_remove(self) -> None:
        mgr = AuthProfileManager()
        mgr.add(AuthProfile(name="test"))
        assert mgr.remove("test") is True
        assert mgr.get("test") is None


class TestModelSwitcher:
    def test_default_model(self) -> None:
        ms = ModelSwitcher()
        assert ms.current_model == "claude-sonnet-4-20250514"

    def test_switch(self) -> None:
        ms = ModelSwitcher()
        ms.register_model(ModelOption(model_id="gpt-4o"))
        assert ms.switch("gpt-4o") is True
        assert ms.current_model == "gpt-4o"
        assert ms.switch_count == 1

    def test_switch_unknown_fails(self) -> None:
        ms = ModelSwitcher()
        assert ms.switch("nonexistent") is False

    def test_fallback(self) -> None:
        config = ModelSwitcherConfig(default_model="a", fallback_chain=["a", "b", "c"])
        ms = ModelSwitcher(config)
        assert ms.fallback() == "b"
        assert ms.fallback() == "c"
        assert ms.fallback() is None

    def test_reset(self) -> None:
        ms = ModelSwitcher()
        ms.register_model(ModelOption(model_id="other"))
        ms.switch("other")
        ms.reset()
        assert ms.current_model == "claude-sonnet-4-20250514"
