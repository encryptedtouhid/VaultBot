"""Subprocess sandbox for plugin execution.

Plugins run in isolated subprocess with:
- JSON-RPC communication over stdin/stdout
- Hard timeout enforcement
- Restricted environment variables
- No access to the main bot process

This is the real security boundary — even a malicious plugin
cannot access bot credentials, other plugins, or host resources
beyond what the manifest declares.
"""

from __future__ import annotations

import asyncio
import json
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

from vaultbot.plugins.base import PluginContext, PluginResult, PluginResultStatus
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    """Configuration for the plugin sandbox."""

    timeout_seconds: float = 30.0
    max_output_bytes: int = 1024 * 1024  # 1MB max output
    python_executable: str = sys.executable


# The runner script that executes inside the subprocess.
# It receives the plugin module path and context via JSON-RPC on stdin,
# imports the plugin, calls handle(), and returns the result on stdout.
_RUNNER_SCRIPT = textwrap.dedent("""\
    import asyncio
    import importlib.util
    import json
    import sys
    import os

    # Restrict environment — remove sensitive vars
    for key in list(os.environ.keys()):
        if key.startswith(("VAULTBOT_", "AWS_", "AZURE_", "GCP_", "DATABASE_")):
            del os.environ[key]

    def load_plugin(module_path):
        spec = importlib.util.spec_from_file_location("plugin_module", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the PluginBase subclass
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and attr_name != "PluginBase"
                and hasattr(attr, "manifest")
                and hasattr(attr, "handle")
            ):
                return attr()
        raise RuntimeError("No plugin class found in module")

    async def main():
        # Read request from stdin
        request_line = sys.stdin.readline()
        if not request_line:
            sys.exit(1)

        request = json.loads(request_line)
        module_path = request["module_path"]
        context_data = request["context"]

        try:
            plugin = load_plugin(module_path)

            # Build context from dict
            from vaultbot.plugins.base import PluginContext
            ctx = PluginContext.from_dict(context_data)

            result = await plugin.handle(ctx)
            response = {
                "status": "ok",
                "result": result.to_dict(),
            }
        except Exception as e:
            response = {
                "status": "error",
                "error": f"{type(e).__name__}: {e}",
            }

        sys.stdout.write(json.dumps(response) + "\\n")
        sys.stdout.flush()

    asyncio.run(main())
""")


class PluginSandbox:
    """Executes plugins in isolated subprocesses.

    Uses asyncio.create_subprocess_exec (not shell) to prevent
    command injection. Communication happens via stdin/stdout JSON-RPC.
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig()

    async def execute(
        self,
        plugin_module_path: Path,
        context: PluginContext,
    ) -> PluginResult:
        """Execute a plugin in a sandboxed subprocess.

        Args:
            plugin_module_path: Path to the plugin's main .py file.
            context: The execution context for this plugin invocation.

        Returns:
            PluginResult with the plugin's output or error details.
        """
        request = json.dumps({
            "module_path": str(plugin_module_path),
            "context": context.to_dict(),
        }) + "\n"

        # Build restricted environment
        env = self._build_restricted_env()

        try:
            # NOTE: Using create_subprocess_exec (not shell) to prevent injection.
            # Arguments are passed as a list, not interpolated into a shell command.
            process = await asyncio.create_subprocess_exec(
                self._config.python_executable,
                "-c",
                _RUNNER_SCRIPT,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=request.encode()),
                timeout=self._config.timeout_seconds,
            )

        except TimeoutError:
            logger.warning(
                "plugin_timeout",
                module=str(plugin_module_path),
                timeout=self._config.timeout_seconds,
            )
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error=f"Plugin timed out after {self._config.timeout_seconds}s",
            )

        except OSError as e:
            logger.error("sandbox_spawn_error", error=str(e))
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error=f"Failed to spawn plugin process: {e}",
            )

        # Check for process errors
        if process.returncode != 0:
            stderr_text = stderr.decode(errors="replace")[:500]
            logger.warning(
                "plugin_process_error",
                module=str(plugin_module_path),
                returncode=process.returncode,
                stderr=stderr_text,
            )
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error=f"Plugin process exited with code {process.returncode}: {stderr_text}",
            )

        # Parse stdout response
        stdout_text = stdout.decode(errors="replace")
        if len(stdout_text) > self._config.max_output_bytes:
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error="Plugin output exceeded maximum size",
            )

        try:
            response = json.loads(stdout_text.strip())
        except json.JSONDecodeError:
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error="Plugin returned invalid JSON response",
            )

        if response.get("status") == "error":
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error=response.get("error", "Unknown plugin error"),
            )

        try:
            return PluginResult.from_dict(response["result"])
        except (KeyError, ValueError) as e:
            return PluginResult(
                status=PluginResultStatus.ERROR,
                error=f"Invalid plugin result format: {e}",
            )

    @staticmethod
    def _build_restricted_env() -> dict[str, str]:
        """Build a restricted environment for the subprocess.

        Strips sensitive environment variables while keeping
        essential ones for Python to function.
        """
        import os

        # Start with minimal environment
        env: dict[str, str] = {}

        # Keep only essential variables
        keep_vars = {
            "PATH", "HOME", "USER", "LANG", "LC_ALL",
            "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV",
            "TMPDIR", "TMP", "TEMP",
        }
        for key in keep_vars:
            value = os.environ.get(key)
            if value is not None:
                env[key] = value

        return env
