"""Pluggable sandbox backends for isolated execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SandboxType(str, Enum):
    DOCKER = "docker"
    SSH = "ssh"
    LOCAL = "local"
    BROWSER = "browser"


class SandboxState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    sandbox_type: SandboxType = SandboxType.LOCAL
    image: str = ""
    working_dir: str = "/workspace"
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0
    network_enabled: bool = False
    timeout_seconds: float = 300.0
    env_vars: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SandboxInstance:
    instance_id: str = ""
    config: SandboxConfig = field(default_factory=SandboxConfig)
    state: SandboxState = SandboxState.STOPPED
    container_id: str = ""
    pid: int = 0


@runtime_checkable
class SandboxBackend(Protocol):
    """Protocol for sandbox backends."""

    @property
    def backend_type(self) -> SandboxType: ...

    async def create(self, config: SandboxConfig) -> SandboxInstance: ...

    async def start(self, instance: SandboxInstance) -> None: ...

    async def stop(self, instance: SandboxInstance) -> None: ...

    async def execute(
        self, instance: SandboxInstance, command: list[str]
    ) -> tuple[int, str, str]: ...

    async def destroy(self, instance: SandboxInstance) -> None: ...


class LocalSandbox:
    """Local process sandbox (no isolation, for development)."""

    @property
    def backend_type(self) -> SandboxType:
        return SandboxType.LOCAL

    async def create(self, config: SandboxConfig) -> SandboxInstance:
        return SandboxInstance(instance_id="local", config=config, state=SandboxState.STOPPED)

    async def start(self, instance: SandboxInstance) -> None:
        instance.state = SandboxState.RUNNING

    async def stop(self, instance: SandboxInstance) -> None:
        instance.state = SandboxState.STOPPED

    async def execute(self, instance: SandboxInstance, command: list[str]) -> tuple[int, str, str]:
        import subprocess

        try:
            result = subprocess.run(  # noqa: S603
                command,
                capture_output=True,
                text=True,
                timeout=instance.config.timeout_seconds,
                cwd=instance.config.working_dir or None,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Execution timed out"
        except FileNotFoundError:
            return -1, "", f"Command not found: {command[0]}"

    async def destroy(self, instance: SandboxInstance) -> None:
        instance.state = SandboxState.STOPPED


class DockerSandbox:
    """Docker container sandbox backend."""

    @property
    def backend_type(self) -> SandboxType:
        return SandboxType.DOCKER

    async def create(self, config: SandboxConfig) -> SandboxInstance:
        return SandboxInstance(
            instance_id=f"docker_{id(config)}", config=config, state=SandboxState.STOPPED
        )

    async def start(self, instance: SandboxInstance) -> None:
        instance.state = SandboxState.RUNNING
        logger.info("docker_sandbox_started", instance_id=instance.instance_id)

    async def stop(self, instance: SandboxInstance) -> None:
        instance.state = SandboxState.STOPPED

    async def execute(self, instance: SandboxInstance, command: list[str]) -> tuple[int, str, str]:
        if instance.state != SandboxState.RUNNING:
            return -1, "", "Sandbox not running"
        # In production, this would use docker exec
        return 0, "", ""

    async def destroy(self, instance: SandboxInstance) -> None:
        instance.state = SandboxState.STOPPED


class SandboxManager:
    """Manages sandbox backends and instances."""

    def __init__(self) -> None:
        self._backends: dict[SandboxType, SandboxBackend] = {}
        self._instances: dict[str, SandboxInstance] = {}

    def register_backend(self, backend: SandboxBackend) -> None:
        self._backends[backend.backend_type] = backend

    async def create_sandbox(self, config: SandboxConfig) -> SandboxInstance:
        backend = self._backends.get(config.sandbox_type)
        if not backend:
            raise ValueError(f"No backend for sandbox type: {config.sandbox_type}")
        instance = await backend.create(config)
        self._instances[instance.instance_id] = instance
        return instance

    async def start_sandbox(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        backend = self._backends.get(instance.config.sandbox_type)
        if not backend:
            return False
        await backend.start(instance)
        return True

    async def execute_in_sandbox(
        self, instance_id: str, command: list[str]
    ) -> tuple[int, str, str]:
        instance = self._instances.get(instance_id)
        if not instance:
            return -1, "", "Instance not found"
        backend = self._backends.get(instance.config.sandbox_type)
        if not backend:
            return -1, "", "Backend not found"
        return await backend.execute(instance, command)

    async def destroy_sandbox(self, instance_id: str) -> bool:
        instance = self._instances.pop(instance_id, None)
        if not instance:
            return False
        backend = self._backends.get(instance.config.sandbox_type)
        if backend:
            await backend.destroy(instance)
        return True

    @property
    def instance_count(self) -> int:
        return len(self._instances)

    def list_instances(self) -> list[SandboxInstance]:
        return list(self._instances.values())
