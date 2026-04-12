"""Podman deployment support."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PodmanConfig:
    image: str = "vaultbot:latest"
    container_name: str = "vaultbot"
    ports: list[str] = field(default_factory=lambda: ["8080:8080"])
    env_file: str = ".env"
    volumes: list[str] = field(default_factory=list)
    rootless: bool = True


class PodmanDeployer:
    """Generate Podman deployment commands and configurations."""

    def __init__(self, config: PodmanConfig | None = None) -> None:
        self._config = config or PodmanConfig()

    def generate_run_command(self) -> str:
        parts = ["podman", "run", "-d", f"--name={self._config.container_name}"]
        for port in self._config.ports:
            parts.append(f"-p {port}")
        if self._config.env_file:
            parts.append(f"--env-file={self._config.env_file}")
        for vol in self._config.volumes:
            parts.append(f"-v {vol}")
        parts.append(self._config.image)
        return " ".join(parts)

    def generate_compose(self) -> dict[str, object]:
        return {
            "version": "3",
            "services": {
                "vaultbot": {
                    "image": self._config.image,
                    "container_name": self._config.container_name,
                    "ports": self._config.ports,
                    "env_file": self._config.env_file,
                    "restart": "unless-stopped",
                }
            },
        }
