"""Control plane for managing bot instances and health."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class InstanceStatus(str, Enum):
    """Bot instance status."""

    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass(slots=True)
class BotInstance:
    """Represents a managed bot instance."""

    instance_id: str
    name: str = ""
    status: InstanceStatus = InstanceStatus.STOPPED
    started_at: float = 0.0
    last_heartbeat: float = 0.0
    platforms: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlCommand:
    """A control plane command."""

    action: str
    target: str = ""
    params: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlResult:
    """Result of a control plane command."""

    success: bool
    message: str = ""
    data: dict[str, object] = field(default_factory=dict)


class ControlPlane:
    """Control plane for managing bot instances."""

    def __init__(self, heartbeat_timeout: float = 60.0) -> None:
        self._instances: dict[str, BotInstance] = {}
        self._heartbeat_timeout = heartbeat_timeout

    @property
    def instance_count(self) -> int:
        return len(self._instances)

    def get_instances(self) -> dict[str, BotInstance]:
        return dict(self._instances)

    def register_instance(
        self, instance_id: str, name: str = "", platforms: list[str] | None = None,
    ) -> BotInstance:
        instance = BotInstance(
            instance_id=instance_id,
            name=name or instance_id,
            platforms=platforms or [],
        )
        self._instances[instance_id] = instance
        logger.info("instance_registered", id=instance_id)
        return instance

    def unregister_instance(self, instance_id: str) -> bool:
        if instance_id in self._instances:
            del self._instances[instance_id]
            logger.info("instance_unregistered", id=instance_id)
            return True
        return False

    def start_instance(self, instance_id: str) -> ControlResult:
        inst = self._instances.get(instance_id)
        if not inst:
            return ControlResult(success=False, message="instance not found")
        inst.status = InstanceStatus.RUNNING
        inst.started_at = time.time()
        inst.last_heartbeat = time.time()
        return ControlResult(success=True, message="started")

    def stop_instance(self, instance_id: str) -> ControlResult:
        inst = self._instances.get(instance_id)
        if not inst:
            return ControlResult(success=False, message="instance not found")
        inst.status = InstanceStatus.STOPPED
        return ControlResult(success=True, message="stopped")

    def heartbeat(self, instance_id: str) -> bool:
        inst = self._instances.get(instance_id)
        if not inst:
            return False
        inst.last_heartbeat = time.time()
        return True

    def check_health(self) -> dict[str, InstanceStatus]:
        """Check health of all instances, marking stale ones as degraded."""
        now = time.time()
        result: dict[str, InstanceStatus] = {}
        for iid, inst in self._instances.items():
            if inst.status == InstanceStatus.RUNNING:
                if (now - inst.last_heartbeat) > self._heartbeat_timeout:
                    inst.status = InstanceStatus.DEGRADED
            result[iid] = inst.status
        return result

    def execute_command(self, command: ControlCommand) -> ControlResult:
        """Execute a control plane command."""
        if command.action == "start":
            return self.start_instance(command.target)
        if command.action == "stop":
            return self.stop_instance(command.target)
        if command.action == "status":
            health = self.check_health()
            inst_map = {k: v.value for k, v in health.items()}
            return ControlResult(success=True, data={"instances": inst_map})
        if command.action == "list":
            names = {iid: inst.name for iid, inst in self._instances.items()}
            return ControlResult(success=True, data={"instances": names})
        return ControlResult(success=False, message=f"unknown action: {command.action}")
