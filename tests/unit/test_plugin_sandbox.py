"""Tests for plugin sandbox execution."""

import tempfile
from pathlib import Path

import pytest

from vaultbot.plugins.base import PluginContext, PluginResultStatus
from vaultbot.plugins.sandbox import PluginSandbox, SandboxConfig


@pytest.fixture
def sandbox() -> PluginSandbox:
    return PluginSandbox(SandboxConfig(timeout_seconds=10.0))


@pytest.fixture
def context() -> PluginContext:
    return PluginContext(
        user_input="2 + 3",
        chat_id="test-chat",
        user_id="test-user",
        platform="test",
    )


def _write_plugin(tmpdir: str, code: str) -> Path:
    """Write a plugin file and return its path."""
    plugin_path = Path(tmpdir) / "plugin.py"
    plugin_path.write_text(code)
    return plugin_path


@pytest.mark.asyncio
async def test_execute_simple_plugin(sandbox: PluginSandbox, context: PluginContext) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = _write_plugin(
            tmpdir,
            """
from vaultbot.plugins.base import (
    PluginBase, PluginContext, PluginManifest,
    PluginResult, PluginResultStatus)

class TestPlugin(PluginBase):
    def manifest(self):
        return PluginManifest(name="test", version="1.0", description="t", author="t")

    async def handle(self, ctx):
        return PluginResult(status=PluginResultStatus.SUCCESS, output=f"Got: {ctx.user_input}")
""",
        )
        result = await sandbox.execute(plugin_path, context)
        assert result.status == PluginResultStatus.SUCCESS
        assert "Got: 2 + 3" in result.output


@pytest.mark.asyncio
async def test_timeout_kills_plugin(context: PluginContext) -> None:
    sandbox = PluginSandbox(SandboxConfig(timeout_seconds=2.0))
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = _write_plugin(
            tmpdir,
            """
import time
from vaultbot.plugins.base import (
    PluginBase, PluginContext, PluginManifest,
    PluginResult, PluginResultStatus)

class SlowPlugin(PluginBase):
    def manifest(self):
        return PluginManifest(name="slow", version="1.0", description="t", author="t")

    async def handle(self, ctx):
        time.sleep(30)
        return PluginResult(status=PluginResultStatus.SUCCESS, output="done")
""",
        )
        result = await sandbox.execute(plugin_path, context)
        assert result.status == PluginResultStatus.ERROR
        assert "timed out" in result.error


@pytest.mark.asyncio
async def test_plugin_error_captured(sandbox: PluginSandbox, context: PluginContext) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_path = _write_plugin(
            tmpdir,
            """
from vaultbot.plugins.base import (
    PluginBase, PluginContext, PluginManifest,
    PluginResult, PluginResultStatus)

class BadPlugin(PluginBase):
    def manifest(self):
        return PluginManifest(name="bad", version="1.0", description="t", author="t")

    async def handle(self, ctx):
        raise ValueError("Something went wrong")
""",
        )
        result = await sandbox.execute(plugin_path, context)
        assert result.status == PluginResultStatus.ERROR
        assert "Something went wrong" in result.error


@pytest.mark.asyncio
async def test_invalid_module_path(sandbox: PluginSandbox, context: PluginContext) -> None:
    result = await sandbox.execute(Path("/nonexistent/plugin.py"), context)
    assert result.status == PluginResultStatus.ERROR
