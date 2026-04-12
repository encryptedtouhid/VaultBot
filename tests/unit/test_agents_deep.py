"""Unit tests for deep agents module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vaultbot.agents.bash_tools.exec_approvals import (
    ApprovalDecision,
    ExecApprovalEngine,
)
from vaultbot.agents.bash_tools.process_registry import ProcessMode, ProcessRegistry
from vaultbot.agents.sandbox.backend import (
    LocalSandbox,
    SandboxBackend,
    SandboxConfig,
    SandboxManager,
    SandboxState,
    SandboxType,
)
from vaultbot.agents.sandbox.fs_bridge import FsBridge, PathTraversalError, WorkspaceBoundary
from vaultbot.agents.sandbox.tool_policy import ToolAccess, ToolPolicy, ToolPolicyRule
from vaultbot.agents.skills.contract import SkillContract, SkillRegistry, SkillSource
from vaultbot.agents.subagent.registry import SubagentRegistry, SubagentRole
from vaultbot.agents.transcript.policy import (
    TranscriptPolicy,
    normalize_tool_call_id,
    pair_tool_results,
)
from vaultbot.agents.workspace.manager import WorkspaceManager


class TestSandboxBackend:
    def test_local_is_backend(self) -> None:
        assert isinstance(LocalSandbox(), SandboxBackend)

    @pytest.mark.asyncio
    async def test_local_create_and_execute(self) -> None:
        sandbox = LocalSandbox()
        instance = await sandbox.create(SandboxConfig(working_dir=""))
        await sandbox.start(instance)
        assert instance.state == SandboxState.RUNNING
        code, stdout, _ = await sandbox.execute(instance, ["echo", "hello"])
        assert code == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_sandbox_manager(self) -> None:
        mgr = SandboxManager()
        mgr.register_backend(LocalSandbox())
        config = SandboxConfig(sandbox_type=SandboxType.LOCAL, working_dir="")
        inst = await mgr.create_sandbox(config)
        assert mgr.instance_count == 1
        await mgr.start_sandbox(inst.instance_id)
        code, stdout, _ = await mgr.execute_in_sandbox(inst.instance_id, ["echo", "test"])
        assert code == 0
        await mgr.destroy_sandbox(inst.instance_id)
        assert mgr.instance_count == 0


class TestFsBridge:
    def test_resolve_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bridge = FsBridge(WorkspaceBoundary(root=root))
            path = bridge.resolve_safe("test.txt")
            assert str(path).startswith(str(root))

    def test_path_traversal_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bridge = FsBridge(WorkspaceBoundary(root=Path(tmp)))
            with pytest.raises(PathTraversalError):
                bridge.resolve_safe("../../etc/passwd")

    def test_write_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bridge = FsBridge(WorkspaceBoundary(root=Path(tmp)))
            bridge.write_file("test.txt", b"hello")
            data = bridge.read_file("test.txt")
            assert data == b"hello"

    def test_readonly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bridge = FsBridge(WorkspaceBoundary(root=Path(tmp), readonly=True))
            with pytest.raises(PermissionError):
                bridge.write_file("test.txt", b"data")


class TestToolPolicy:
    def test_default_allow(self) -> None:
        policy = ToolPolicy()
        assert policy.evaluate("any_tool") == ToolAccess.ALLOW

    def test_deny_rule(self) -> None:
        policy = ToolPolicy()
        policy.add_rule(ToolPolicyRule(tool_name="dangerous", access=ToolAccess.DENY))
        assert policy.evaluate("dangerous") == ToolAccess.DENY
        assert policy.evaluate("safe") == ToolAccess.ALLOW


class TestExecApprovals:
    def test_safe_command(self) -> None:
        engine = ExecApprovalEngine()
        analysis = engine.analyze(["echo", "hello"])
        assert analysis.decision == ApprovalDecision.AUTO_APPROVE

    def test_dangerous_command(self) -> None:
        engine = ExecApprovalEngine()
        analysis = engine.analyze(["shutdown", "-h", "now"])
        assert analysis.decision == ApprovalDecision.DENY

    def test_medium_command(self) -> None:
        engine = ExecApprovalEngine()
        analysis = engine.analyze(["curl", "https://example.com"])
        assert analysis.decision == ApprovalDecision.ASK_USER

    def test_unknown_command(self) -> None:
        engine = ExecApprovalEngine()
        analysis = engine.analyze(["custom_tool"])
        assert analysis.decision == ApprovalDecision.ASK_USER

    def test_empty_command(self) -> None:
        engine = ExecApprovalEngine()
        analysis = engine.analyze([])
        assert analysis.decision == ApprovalDecision.DENY


class TestProcessRegistry:
    def test_register_and_complete(self) -> None:
        reg = ProcessRegistry()
        job = reg.register(["echo", "hi"])
        assert reg.job_count == 1
        reg.complete(job.job_id, exit_code=0, output="hi")
        assert job.exit_code == 0

    def test_background_jobs(self) -> None:
        reg = ProcessRegistry()
        reg.register(["sleep", "10"], mode=ProcessMode.BACKGROUND)
        assert len(reg.list_background()) == 1

    def test_cleanup(self) -> None:
        reg = ProcessRegistry()
        job = reg.register(["echo"])
        reg.complete(job.job_id)
        assert reg.cleanup_finished() == 1


class TestSkillRegistry:
    def test_register_and_get(self) -> None:
        reg = SkillRegistry()
        reg.register(SkillContract(name="weather", source=SkillSource.BUNDLED))
        assert reg.get("weather") is not None
        assert reg.skill_count == 1

    def test_eligibility(self) -> None:
        reg = SkillRegistry()
        reg.register(SkillContract(name="mac_only", platforms=["darwin"]))
        assert reg.is_eligible("mac_only", "darwin") is True
        assert reg.is_eligible("mac_only", "linux") is False

    def test_filter_for_agent(self) -> None:
        reg = SkillRegistry()
        reg.register(SkillContract(name="a"))
        reg.register(SkillContract(name="b"))
        reg.register(SkillContract(name="c"))
        filtered = reg.filter_for_agent(["a", "c"])
        assert len(filtered) == 2


class TestSubagentRegistry:
    def test_spawn(self) -> None:
        reg = SubagentRegistry()
        entry = reg.spawn("child1", parent_id="", role=SubagentRole.LEAF)
        assert entry is not None
        assert reg.agent_count == 1

    def test_depth_limit(self) -> None:
        reg = SubagentRegistry(max_depth=1)
        reg.spawn("a", parent_id="")
        child = reg.spawn("b", parent_id="a")
        assert child is not None
        grandchild = reg.spawn("c", parent_id="b")
        assert grandchild is None  # Depth exceeded

    def test_complete_and_announce(self) -> None:
        reg = SubagentRegistry()
        reg.spawn("child", parent_id="parent")
        reg.complete("child", result="done")
        msgs = reg.drain_announce_queue()
        assert len(msgs) == 1
        assert msgs[0].result == "done"

    def test_orphan_recovery(self) -> None:
        reg = SubagentRegistry()
        entry = reg.spawn("stale")
        entry.spawned_at = 0  # Make it old
        count = reg.recover_orphans(timeout_seconds=0)
        assert count == 1

    def test_token_budget(self) -> None:
        reg = SubagentRegistry()
        entry = reg.spawn("a")
        entry.token_budget = 100
        assert reg.update_token_usage("a", 50) is True
        assert reg.update_token_usage("a", 60) is False  # Over budget


class TestTranscriptPolicy:
    def test_defaults(self) -> None:
        policy = TranscriptPolicy()
        assert policy.strip_thinking_blocks is True

    def test_normalize_tool_call_id(self) -> None:
        assert normalize_tool_call_id("call_123") == "call_123"
        assert normalize_tool_call_id("").startswith("call_")

    def test_pair_tool_results(self) -> None:
        messages = [
            {"role": "assistant", "tool_calls": [{"id": "tc1"}]},
            {"role": "tool", "tool_call_id": "tc1", "content": "result"},
        ]
        pairs = pair_tool_results(messages)
        assert len(pairs) == 1
        assert pairs[0][1] is not None


class TestWorkspaceManager:
    def test_create_and_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = WorkspaceManager(base_dir=tmp)
            ws = mgr.create("agent1")
            assert ws.created is True
            assert mgr.resolve("agent1") == ws.path

    def test_destroy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = WorkspaceManager(base_dir=tmp)
            mgr.create("agent1")
            assert mgr.destroy("agent1") is True
            assert mgr.get("agent1") is None

    def test_list_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mgr = WorkspaceManager(base_dir=tmp)
            mgr.create("a")
            mgr.create("b")
            assert len(mgr.list_workspaces()) == 2
