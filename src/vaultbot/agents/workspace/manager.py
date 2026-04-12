"""Agent-scoped workspace management."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class WorkspaceScope(str, Enum):
    SESSION = "session"
    AGENT = "agent"
    SHARED = "shared"


@dataclass(frozen=True, slots=True)
class WorkspaceConfig:
    base_dir: str = ""
    scope: WorkspaceScope = WorkspaceScope.AGENT
    template_dir: str = ""
    auto_seed: bool = False


@dataclass(slots=True)
class AgentWorkspace:
    agent_id: str
    path: Path
    scope: WorkspaceScope = WorkspaceScope.AGENT
    created: bool = False


class WorkspaceManager:
    """Manages per-agent workspace directories."""

    def __init__(self, base_dir: str = "") -> None:
        self._base = Path(base_dir) if base_dir else Path(tempfile.mkdtemp(prefix="vaultbot_ws_"))
        self._workspaces: dict[str, AgentWorkspace] = {}

    @property
    def base_dir(self) -> Path:
        return self._base

    def create(self, agent_id: str, config: WorkspaceConfig | None = None) -> AgentWorkspace:
        cfg = config or WorkspaceConfig()
        ws_path = self._base / agent_id
        ws_path.mkdir(parents=True, exist_ok=True)
        ws = AgentWorkspace(agent_id=agent_id, path=ws_path, scope=cfg.scope, created=True)
        self._workspaces[agent_id] = ws

        # Seed from template if configured
        if cfg.template_dir and cfg.auto_seed:
            self._seed_from_template(ws_path, Path(cfg.template_dir))

        logger.info("workspace_created", agent_id=agent_id, path=str(ws_path))
        return ws

    def get(self, agent_id: str) -> AgentWorkspace | None:
        return self._workspaces.get(agent_id)

    def resolve(self, agent_id: str) -> Path:
        """Resolve workspace path, creating if needed."""
        ws = self._workspaces.get(agent_id)
        if ws:
            return ws.path
        return self.create(agent_id).path

    def destroy(self, agent_id: str) -> bool:
        ws = self._workspaces.pop(agent_id, None)
        if not ws:
            return False
        import shutil

        if ws.path.exists():
            shutil.rmtree(ws.path, ignore_errors=True)
        return True

    def list_workspaces(self) -> list[AgentWorkspace]:
        return list(self._workspaces.values())

    @staticmethod
    def _seed_from_template(ws_path: Path, template_path: Path) -> None:
        if not template_path.exists():
            return
        import shutil

        for item in template_path.iterdir():
            dest = ws_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
