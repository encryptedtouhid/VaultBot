"""Unit tests for canvas host and node host."""

from __future__ import annotations

import pytest

from vaultbot.canvas.server import CanvasConfig, CanvasServer
from vaultbot.execution.node_host import ApprovalState, ExecPolicy, NodeHost


class TestCanvasServer:
    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        server = CanvasServer()
        await server.start()
        assert server.is_running is True
        await server.stop()
        assert server.is_running is False

    def test_connections(self) -> None:
        server = CanvasServer()
        server.add_connection()
        assert server.connection_count == 1
        server.remove_connection()
        assert server.connection_count == 0

    def test_custom_config(self) -> None:
        config = CanvasConfig(port=3000, live_reload=True)
        server = CanvasServer(config)
        assert server.config.port == 3000


class TestExecPolicy:
    def test_allowed_command(self) -> None:
        policy = ExecPolicy()
        assert policy.evaluate(["echo", "hi"]) == ApprovalState.APPROVED

    def test_denied_command(self) -> None:
        policy = ExecPolicy()
        assert policy.evaluate(["rm", "-rf", "/"]) == ApprovalState.DENIED

    def test_unknown_command_pending(self) -> None:
        policy = ExecPolicy()
        assert policy.evaluate(["custom_tool"]) == ApprovalState.PENDING

    def test_empty_command_denied(self) -> None:
        policy = ExecPolicy()
        assert policy.evaluate([]) == ApprovalState.DENIED

    def test_add_allowed(self) -> None:
        policy = ExecPolicy()
        policy.add_allowed("custom_tool")
        assert policy.evaluate(["custom_tool"]) == ApprovalState.APPROVED


class TestNodeHost:
    def test_auto_approved(self) -> None:
        host = NodeHost()
        req = host.request(["echo", "hi"])
        assert req.approval == ApprovalState.APPROVED
        assert host.approved_count == 1

    def test_auto_denied(self) -> None:
        host = NodeHost()
        req = host.request(["rm", "-rf"])
        assert req.approval == ApprovalState.DENIED

    def test_pending_approval(self) -> None:
        host = NodeHost()
        req = host.request(["custom_tool"])
        assert req.approval == ApprovalState.PENDING
        assert host.pending_count == 1

    def test_approve_pending(self) -> None:
        host = NodeHost()
        host.request(["custom_tool"])
        approved = host.approve_pending()
        assert approved is not None
        assert approved.approval == ApprovalState.APPROVED

    def test_deny_pending(self) -> None:
        host = NodeHost()
        host.request(["custom_tool"])
        denied = host.deny_pending()
        assert denied is not None
        assert denied.approval == ApprovalState.DENIED
