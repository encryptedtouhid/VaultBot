"""Node discovery, health monitoring, and capability management."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class NodeStatus(str, Enum):
    DISCOVERED = "discovered"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass(slots=True)
class NodeInfo:
    node_id: str
    name: str = ""
    address: str = ""
    status: NodeStatus = NodeStatus.DISCOVERED
    capabilities: list[str] = field(default_factory=list)
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)


class NodeManager:
    """Manages gateway node discovery, health, and capabilities."""

    def __init__(self, heartbeat_timeout: float = 60.0) -> None:
        self._nodes: dict[str, NodeInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def register(self, node_id: str, name: str = "", address: str = "") -> NodeInfo:
        node = NodeInfo(node_id=node_id, name=name or node_id, address=address)
        self._nodes[node_id] = node
        logger.info("node_registered", node_id=node_id)
        return node

    def unregister(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False

    def heartbeat(self, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.last_heartbeat = time.time()
        node.status = NodeStatus.HEALTHY
        return True

    def get_node(self, node_id: str) -> NodeInfo | None:
        return self._nodes.get(node_id)

    def list_nodes(self, status: NodeStatus | None = None) -> list[NodeInfo]:
        if status:
            return [n for n in self._nodes.values() if n.status == status]
        return list(self._nodes.values())

    def check_health(self) -> dict[str, NodeStatus]:
        now = time.time()
        result: dict[str, NodeStatus] = {}
        for nid, node in self._nodes.items():
            if node.status in (NodeStatus.HEALTHY, NodeStatus.DISCOVERED):
                if (now - node.last_heartbeat) > self._heartbeat_timeout:
                    node.status = NodeStatus.DEGRADED
            result[nid] = node.status
        return result

    def set_capabilities(self, node_id: str, capabilities: list[str]) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.capabilities = capabilities
        return True

    def find_by_capability(self, capability: str) -> list[NodeInfo]:
        return [n for n in self._nodes.values() if capability in n.capabilities]
