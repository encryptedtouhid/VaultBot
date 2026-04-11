"""Plugin SDK — tools for plugin developers.

Provides:
- Scaffolding to create new plugin projects
- Mock context for local testing without a running bot
- Test harness to validate plugin behavior
- Manifest validation
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vaultbot.plugins.base import (
    PermissionLevel,
    PluginBase,
    PluginContext,
    PluginResult,
    PluginResultStatus,
)
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Plugin scaffolding
# =============================================================================

_PLUGIN_TEMPLATE = '''\
"""{{name}} — {{description}}"""

from __future__ import annotations

from vaultbot.plugins.base import (
    PluginBase,
    PluginContext,
    PluginManifest,
    PluginResult,
    PluginResultStatus,
)


class {{class_name}}(PluginBase):
    """{{description}}"""

    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="{{name}}",
            version="1.0.0",
            description="{{description}}",
            author="{{author}}",
        )

    async def handle(self, ctx: PluginContext) -> PluginResult:
        # TODO: Implement your plugin logic here
        return PluginResult(
            status=PluginResultStatus.SUCCESS,
            output=f"Hello from {{name}}! You said: {ctx.user_input}",
        )
'''

_MANIFEST_TEMPLATE = {
    "name": "",
    "version": "1.0.0",
    "description": "",
    "author": "",
    "min_zenbot_version": "0.1.0",
    "network_domains": [],
    "filesystem": "none",
    "secrets": [],
    "timeout_seconds": 30.0,
    "max_memory_mb": 256,
}


def scaffold_plugin(
    output_dir: Path,
    name: str,
    description: str = "A VaultBot plugin",
    author: str = "",
) -> Path:
    """Create a new plugin project with boilerplate files.

    Returns the path to the created plugin directory.
    """
    plugin_dir = output_dir / name
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Generate class name from plugin name
    class_name = "".join(
        word.capitalize() for word in name.replace("-", "_").split("_")
    ) + "Plugin"

    # Write plugin.py
    plugin_code = _PLUGIN_TEMPLATE.replace("{{name}}", name)
    plugin_code = plugin_code.replace("{{description}}", description)
    plugin_code = plugin_code.replace("{{class_name}}", class_name)
    plugin_code = plugin_code.replace("{{author}}", author)
    (plugin_dir / "plugin.py").write_text(plugin_code)

    # Write manifest
    manifest = _MANIFEST_TEMPLATE.copy()
    manifest["name"] = name
    manifest["description"] = description
    manifest["author"] = author
    (plugin_dir / "vaultbot_plugin.json").write_text(
        json.dumps(manifest, indent=2)
    )

    logger.info("plugin_scaffolded", name=name, path=str(plugin_dir))
    return plugin_dir


# =============================================================================
# Mock context for testing
# =============================================================================


def mock_context(
    user_input: str = "test input",
    *,
    chat_id: str = "test-chat",
    user_id: str = "test-user",
    platform: str = "test",
    secrets: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> PluginContext:
    """Create a mock PluginContext for local testing."""
    return PluginContext(
        user_input=user_input,
        chat_id=chat_id,
        user_id=user_id,
        platform=platform,
        secrets=secrets or {},
        metadata=metadata or {},
    )


# =============================================================================
# Test harness
# =============================================================================


@dataclass
class TestResult:
    """Result of a plugin test run."""

    passed: bool
    test_name: str
    message: str = ""
    plugin_result: PluginResult | None = None


class PluginTestHarness:
    """Test harness for validating plugin behavior.

    Usage:
        harness = PluginTestHarness(MyPlugin())
        results = await harness.run_all()
        harness.print_results(results)
    """

    def __init__(self, plugin: PluginBase) -> None:
        self._plugin = plugin

    async def run_all(self) -> list[TestResult]:
        """Run all built-in tests against the plugin."""
        results: list[TestResult] = []
        results.append(await self.test_manifest_valid())
        results.append(await self.test_handle_returns_result())
        results.append(await self.test_handle_empty_input())
        results.append(await self.test_handle_long_input())
        results.append(await self.test_lifecycle_hooks())
        return results

    async def test_manifest_valid(self) -> TestResult:
        """Verify the manifest has all required fields."""
        try:
            m = self._plugin.manifest()
            errors = []
            if not m.name:
                errors.append("name is empty")
            if not m.version:
                errors.append("version is empty")
            if not m.description:
                errors.append("description is empty")
            if not m.author:
                errors.append("author is empty")
            if m.timeout_seconds <= 0:
                errors.append("timeout must be positive")
            if m.max_memory_mb <= 0:
                errors.append("max_memory must be positive")

            if errors:
                return TestResult(
                    passed=False,
                    test_name="manifest_valid",
                    message=f"Manifest errors: {', '.join(errors)}",
                )
            return TestResult(passed=True, test_name="manifest_valid")
        except Exception as e:
            return TestResult(
                passed=False,
                test_name="manifest_valid",
                message=f"manifest() raised: {e}",
            )

    async def test_handle_returns_result(self) -> TestResult:
        """Verify handle() returns a valid PluginResult."""
        try:
            ctx = mock_context("Hello, plugin!")
            result = await self._plugin.handle(ctx)

            if not isinstance(result, PluginResult):
                return TestResult(
                    passed=False,
                    test_name="handle_returns_result",
                    message=f"Expected PluginResult, got {type(result).__name__}",
                )

            if result.status not in PluginResultStatus:
                return TestResult(
                    passed=False,
                    test_name="handle_returns_result",
                    message=f"Invalid status: {result.status}",
                )

            return TestResult(
                passed=True,
                test_name="handle_returns_result",
                plugin_result=result,
            )
        except Exception as e:
            return TestResult(
                passed=False,
                test_name="handle_returns_result",
                message=f"handle() raised: {e}",
            )

    async def test_handle_empty_input(self) -> TestResult:
        """Verify handle() gracefully handles empty input."""
        try:
            ctx = mock_context("")
            result = await self._plugin.handle(ctx)
            return TestResult(
                passed=isinstance(result, PluginResult),
                test_name="handle_empty_input",
                plugin_result=result,
            )
        except Exception as e:
            return TestResult(
                passed=False,
                test_name="handle_empty_input",
                message=f"Crashed on empty input: {e}",
            )

    async def test_handle_long_input(self) -> TestResult:
        """Verify handle() handles very long input without crashing."""
        try:
            ctx = mock_context("x" * 10000)
            result = await self._plugin.handle(ctx)
            return TestResult(
                passed=isinstance(result, PluginResult),
                test_name="handle_long_input",
                plugin_result=result,
            )
        except Exception as e:
            return TestResult(
                passed=False,
                test_name="handle_long_input",
                message=f"Crashed on long input: {e}",
            )

    async def test_lifecycle_hooks(self) -> TestResult:
        """Verify on_load/on_unload don't crash."""
        try:
            await self._plugin.on_load()
            await self._plugin.on_unload()
            return TestResult(passed=True, test_name="lifecycle_hooks")
        except Exception as e:
            return TestResult(
                passed=False,
                test_name="lifecycle_hooks",
                message=f"Lifecycle hook raised: {e}",
            )

    @staticmethod
    def print_results(results: list[TestResult]) -> None:
        """Print test results to stdout."""
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        for r in results:
            icon = "PASS" if r.passed else "FAIL"
            msg = f"  [{icon}] {r.test_name}"
            if r.message:
                msg += f" — {r.message}"
            print(msg)  # noqa: T201

        print(f"\n  {passed}/{total} tests passed.")  # noqa: T201


def validate_manifest(manifest_path: Path) -> list[str]:
    """Validate a plugin manifest file. Returns list of errors (empty = valid)."""
    errors: list[str] = []

    if not manifest_path.exists():
        return ["Manifest file does not exist"]

    try:
        data = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    required = ["name", "version", "description", "author"]
    for field in required:
        if not data.get(field):
            errors.append(f"Missing or empty field: {field}")

    # Validate filesystem permission
    fs = data.get("filesystem", "none")
    valid_fs = [p.value for p in PermissionLevel]
    if fs not in valid_fs:
        errors.append(f"Invalid filesystem permission: {fs}. Must be one of {valid_fs}")

    # Validate timeout
    timeout = data.get("timeout_seconds", 30)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        errors.append("timeout_seconds must be a positive number")

    # Validate network domains
    domains = data.get("network_domains", [])
    if not isinstance(domains, list):
        errors.append("network_domains must be a list")

    return errors
