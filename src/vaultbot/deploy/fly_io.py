"""Fly.io deployment helper."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FlyConfig:
    app_name: str = "vaultbot"
    region: str = "iad"
    vm_size: str = "shared-cpu-1x"
    memory_mb: int = 256
    env_vars: dict[str, str] = field(default_factory=dict)


class FlyDeployer:
    """Generate Fly.io deployment configuration."""

    def __init__(self, config: FlyConfig | None = None) -> None:
        self._config = config or FlyConfig()

    def generate_fly_toml(self) -> str:
        lines = [
            f'app = "{self._config.app_name}"',
            "",
            "[build]",
            '  dockerfile = "Dockerfile"',
            "",
            "[http_service]",
            "  internal_port = 8080",
            "  force_https = true",
            "",
            "[[vm]]",
            f'  size = "{self._config.vm_size}"',
            f"  memory = {self._config.memory_mb}",
        ]
        if self._config.env_vars:
            lines.append("")
            lines.append("[env]")
            for k, v in self._config.env_vars.items():
                lines.append(f'  {k} = "{v}"')
        return "\n".join(lines) + "\n"

    def generate_deploy_command(self) -> str:
        return f"fly deploy --app {self._config.app_name} --region {self._config.region}"
