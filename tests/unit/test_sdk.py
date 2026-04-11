"""Tests for the plugin SDK."""

import json
import tempfile
from pathlib import Path

import pytest

from vaultbot.plugins.sdk import (
    PluginTestHarness,
    mock_context,
    scaffold_plugin,
    validate_manifest,
)


class TestScaffolding:
    def test_scaffold_creates_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = scaffold_plugin(Path(tmpdir), "my-plugin", "A test plugin", "tester")
            assert (plugin_dir / "plugin.py").exists()
            assert (plugin_dir / "vaultbot_plugin.json").exists()

    def test_scaffold_manifest_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = scaffold_plugin(Path(tmpdir), "test-plug", "desc", "me")
            manifest = json.loads((plugin_dir / "vaultbot_plugin.json").read_text())
            assert manifest["name"] == "test-plug"
            assert manifest["description"] == "desc"
            assert manifest["author"] == "me"

    def test_scaffold_plugin_code_has_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = scaffold_plugin(Path(tmpdir), "hello-world")
            code = (plugin_dir / "plugin.py").read_text()
            assert "class HelloWorldPlugin" in code
            assert "PluginBase" in code

    def test_scaffold_class_name_from_dashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = scaffold_plugin(Path(tmpdir), "my-cool-plugin")
            code = (plugin_dir / "plugin.py").read_text()
            assert "class MyCoolPluginPlugin" in code


class TestMockContext:
    def test_default_values(self) -> None:
        ctx = mock_context()
        assert ctx.user_input == "test input"
        assert ctx.chat_id == "test-chat"
        assert ctx.platform == "test"

    def test_custom_values(self) -> None:
        ctx = mock_context(
            "hello",
            chat_id="c1",
            user_id="u1",
            platform="telegram",
            secrets={"KEY": "val"},
        )
        assert ctx.user_input == "hello"
        assert ctx.chat_id == "c1"
        assert ctx.secrets == {"KEY": "val"}


class TestValidateManifest:
    def test_valid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "vaultbot_plugin.json"
            path.write_text(
                json.dumps(
                    {
                        "name": "test",
                        "version": "1.0",
                        "description": "A test",
                        "author": "me",
                    }
                )
            )
            errors = validate_manifest(path)
            assert errors == []

    def test_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "vaultbot_plugin.json"
            path.write_text(json.dumps({"name": "test"}))
            errors = validate_manifest(path)
            assert len(errors) >= 2  # missing version, description, author

    def test_nonexistent_file(self) -> None:
        errors = validate_manifest(Path("/nonexistent/manifest.json"))
        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "vaultbot_plugin.json"
            path.write_text("{bad json")
            errors = validate_manifest(path)
            assert len(errors) == 1
            assert "Invalid JSON" in errors[0]

    def test_invalid_filesystem_permission(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "vaultbot_plugin.json"
            path.write_text(
                json.dumps(
                    {
                        "name": "test",
                        "version": "1.0",
                        "description": "A test",
                        "author": "me",
                        "filesystem": "full_access",
                    }
                )
            )
            errors = validate_manifest(path)
            assert any("filesystem" in e.lower() for e in errors)


class TestPluginTestHarness:
    @pytest.mark.asyncio
    async def test_harness_against_scaffolded_plugin(self) -> None:
        """Scaffold a plugin and run the test harness against it."""
        import importlib.util

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = scaffold_plugin(Path(tmpdir), "harness-test", "Test plugin", "tester")

            # Load the scaffolded plugin
            spec = importlib.util.spec_from_file_location("plugin_module", plugin_dir / "plugin.py")
            assert spec is not None
            assert spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin class
            plugin = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "manifest")
                    and hasattr(attr, "handle")
                    and attr_name != "PluginBase"
                ):
                    plugin = attr()
                    break

            assert plugin is not None
            harness = PluginTestHarness(plugin)
            results = await harness.run_all()

            # All tests should pass for a scaffolded plugin
            for r in results:
                assert r.passed, f"{r.test_name} failed: {r.message}"
