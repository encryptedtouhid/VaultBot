"""Plugin base classes, manifest schema, and execution context.

Every plugin declares its capabilities and permissions in a manifest.
Plugins receive a restricted PluginContext and return structured results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionLevel(str, Enum):
    """Filesystem access levels for plugins."""

    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Declares a plugin's identity, capabilities, and required permissions.

    This is the security contract between the plugin and ZenBot.
    Permissions are enforced by the sandbox at runtime.
    """

    name: str
    version: str
    description: str
    author: str
    min_zenbot_version: str = "0.1.0"

    # Permissions — principle of least privilege
    network_domains: list[str] = field(default_factory=list)  # Allowed outbound domains
    filesystem: PermissionLevel = PermissionLevel.NONE
    secrets: list[str] = field(default_factory=list)  # Credential keys it needs

    # Execution constraints
    timeout_seconds: float = 30.0
    max_memory_mb: int = 256

    def to_dict(self) -> dict[str, Any]:
        """Serialize manifest to dict for JSON-RPC transport."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "min_zenbot_version": self.min_zenbot_version,
            "network_domains": self.network_domains,
            "filesystem": self.filesystem.value,
            "secrets": self.secrets,
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        """Deserialize manifest from dict."""
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            min_zenbot_version=data.get("min_zenbot_version", "0.1.0"),
            network_domains=data.get("network_domains", []),
            filesystem=PermissionLevel(data.get("filesystem", "none")),
            secrets=data.get("secrets", []),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            max_memory_mb=data.get("max_memory_mb", 256),
        )


@dataclass(frozen=True, slots=True)
class PluginContext:
    """The execution context passed to a plugin when it handles a request.

    Contains only the information the plugin needs — no access to the
    full bot state, credentials, or other plugins.
    """

    user_input: str
    chat_id: str
    user_id: str
    platform: str
    secrets: dict[str, str] = field(default_factory=dict)  # Only requested secrets
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_input": self.user_input,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "platform": self.platform,
            "secrets": self.secrets,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginContext:
        return cls(
            user_input=data["user_input"],
            chat_id=data["chat_id"],
            user_id=data["user_id"],
            platform=data["platform"],
            secrets=data.get("secrets", {}),
            metadata=data.get("metadata", {}),
        )


class PluginResultStatus(str, Enum):
    """Status of a plugin execution."""

    SUCCESS = "success"
    ERROR = "error"
    NEEDS_APPROVAL = "needs_approval"


@dataclass(frozen=True, slots=True)
class PluginResult:
    """Structured result returned by a plugin after execution."""

    status: PluginResultStatus
    output: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    action_description: str = ""  # Human-readable for approval prompts

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "action_description": self.action_description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginResult:
        return cls(
            status=PluginResultStatus(data["status"]),
            output=data.get("output", ""),
            data=data.get("data", {}),
            error=data.get("error", ""),
            action_description=data.get("action_description", ""),
        )


class PluginBase(ABC):
    """Abstract base class for all ZenBot plugins.

    Plugins must implement `manifest()` and `handle()`.
    Optional lifecycle hooks: `on_load()` and `on_unload()`.
    """

    @abstractmethod
    def manifest(self) -> PluginManifest:
        """Return the plugin's manifest declaring identity and permissions."""
        ...

    @abstractmethod
    async def handle(self, ctx: PluginContext) -> PluginResult:
        """Handle a user request within the plugin's scope."""
        ...

    async def on_load(self) -> None:
        """Called when the plugin is loaded. Override for setup logic."""

    async def on_unload(self) -> None:
        """Called when the plugin is unloaded. Override for cleanup logic."""
