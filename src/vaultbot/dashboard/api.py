"""Dashboard REST API handlers.

Each method returns (status_code, response_dict). The server layer handles
JSON serialization and HTTP response formatting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vaultbot.config import AllowlistEntry, VaultBotConfig
from vaultbot.core.healthcheck import HealthStatus
from vaultbot.security.audit import AuditLogger, EventType, AuditEvent
from vaultbot.security.auth import AuthManager, Role
from vaultbot.security.credentials import CredentialStore
from vaultbot.security.rate_limiter import RateLimiter
from vaultbot.security.teams import TeamManager
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DashboardContext:
    """Dependencies injected into the dashboard API layer."""

    config: VaultBotConfig
    health: HealthStatus
    auth: AuthManager
    rate_limiter: RateLimiter
    credentials: CredentialStore
    audit: AuditLogger
    teams: TeamManager


# Known credential keys that the UI should display status for
_KNOWN_CREDENTIAL_KEYS = [
    "telegram_bot_token",
    "discord_bot_token",
    "whatsapp_access_token",
    "whatsapp_phone_number_id",
    "signal_account",
    "slack_bot_token",
    "slack_app_token",
    "teams_app_id",
    "teams_app_password",
    "llm_api_key",
    "custom_llm_base_url",
]


class DashboardAPI:
    """REST API handler methods for the dashboard."""

    def __init__(self, ctx: DashboardContext) -> None:
        self._ctx = ctx

    # --- Config ---

    async def get_config(self) -> tuple[int, dict[str, Any]]:
        """Return current config with secrets stripped."""
        dump = self._ctx.config.model_dump()
        # Strip credential keys from platform configs
        for platform in ["telegram", "discord", "whatsapp", "signal", "slack", "teams", "imessage"]:
            if platform in dump:
                dump[platform].pop("credential_key", None)
        dump["llm"].pop("credential_key", None)
        return 200, dump

    async def update_config(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Update config fields. Returns list of changes and restart flag."""
        changes: list[str] = []
        requires_restart = False
        config = self._ctx.config

        if "system_prompt" in body:
            config.system_prompt = body["system_prompt"]
            changes.append("system_prompt")

        if "max_history" in body:
            config.max_history = int(body["max_history"])
            changes.append("max_history")

        if "log_level" in body:
            config.log_level = body["log_level"]
            changes.append("log_level")

        if "log_json" in body:
            config.log_json = bool(body["log_json"])
            changes.append("log_json")

        if "log_file" in body:
            config.log_file = bool(body["log_file"])
            changes.append("log_file")
            requires_restart = True

        if changes:
            config.save()
            self._ctx.audit.log(AuditEvent(
                event_type=EventType.CONFIG_CHANGED,
                details={"fields": changes, "source": "dashboard"},
            ))

        return 200, {"ok": True, "changes": changes, "requires_restart": requires_restart}

    # --- Platforms ---

    async def get_platforms(self) -> tuple[int, dict[str, Any]]:
        """List platforms with enabled and connected status."""
        config = self._ctx.config
        platforms: dict[str, Any] = {}
        for name in ["telegram", "discord", "whatsapp", "signal", "slack", "teams", "imessage"]:
            pc = getattr(config, name)
            platforms[name] = {
                "enabled": pc.enabled,
                "connected": self._ctx.health.platforms_connected.get(name, False),
            }
        return 200, {"platforms": platforms}

    async def update_platform(self, name: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Enable or disable a platform."""
        config = self._ctx.config
        pc = getattr(config, name, None)
        if pc is None:
            return 404, {"error": f"Unknown platform: {name}"}

        if "enabled" in body:
            pc.enabled = bool(body["enabled"])
            config.save()
            self._ctx.audit.log(AuditEvent(
                event_type=EventType.CONFIG_CHANGED,
                details={"field": f"{name}.enabled", "value": pc.enabled, "source": "dashboard"},
            ))

        return 200, {"ok": True, "requires_restart": True}

    # --- LLM ---

    async def get_llm(self) -> tuple[int, dict[str, Any]]:
        """Return LLM configuration."""
        llm = self._ctx.config.llm
        return 200, {
            "provider": llm.provider,
            "model": llm.model,
            "temperature": llm.temperature,
            "max_tokens": llm.max_tokens,
        }

    async def update_llm(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Update LLM settings."""
        llm = self._ctx.config.llm
        requires_restart = False
        changes: list[str] = []

        if "provider" in body and body["provider"] != llm.provider:
            llm.provider = body["provider"]
            requires_restart = True
            changes.append("provider")

        if "model" in body and body["model"] != llm.model:
            llm.model = body["model"]
            requires_restart = True
            changes.append("model")

        if "temperature" in body:
            llm.temperature = float(body["temperature"])
            changes.append("temperature")

        if "max_tokens" in body:
            llm.max_tokens = int(body["max_tokens"])
            changes.append("max_tokens")

        if changes:
            self._ctx.config.save()
            self._ctx.audit.log(AuditEvent(
                event_type=EventType.CONFIG_CHANGED,
                details={"fields": changes, "source": "dashboard"},
            ))

        return 200, {"ok": True, "changes": changes, "requires_restart": requires_restart}

    # --- Allowlist ---

    async def get_allowlist(self) -> tuple[int, dict[str, Any]]:
        """List all users with roles."""
        users = self._ctx.auth.list_users()
        entries = []
        for qualified_id, role in users.items():
            platform, user_id = qualified_id.split(":", 1)
            entries.append({"platform": platform, "user_id": user_id, "role": role})
        return 200, {"users": entries}

    async def add_allowlist_entry(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Add a user to the allowlist."""
        platform = body.get("platform", "")
        user_id = body.get("user_id", "")
        role_str = body.get("role", "user")

        if not platform or not user_id:
            return 400, {"error": "platform and user_id are required"}

        role = Role(role_str)
        self._ctx.auth.add_user(platform, user_id, role)

        # Sync to config
        self._ctx.config.allowlist.append(
            AllowlistEntry(platform=platform, user_id=user_id, role=role_str)
        )
        self._ctx.config.save()

        self._ctx.audit.log(AuditEvent(
            event_type=EventType.CONFIG_CHANGED,
            details={"action": "allowlist_add", "user": f"{platform}:{user_id}", "source": "dashboard"},
        ))
        return 200, {"ok": True}

    async def remove_allowlist_entry(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Remove a user from the allowlist."""
        platform = body.get("platform", "")
        user_id = body.get("user_id", "")

        if not platform or not user_id:
            return 400, {"error": "platform and user_id are required"}

        self._ctx.auth.remove_user(platform, user_id)

        # Sync to config
        self._ctx.config.allowlist = [
            e for e in self._ctx.config.allowlist
            if not (e.platform == platform and e.user_id == user_id)
        ]
        self._ctx.config.save()

        self._ctx.audit.log(AuditEvent(
            event_type=EventType.CONFIG_CHANGED,
            details={"action": "allowlist_remove", "user": f"{platform}:{user_id}", "source": "dashboard"},
        ))
        return 200, {"ok": True}

    # --- Plugins ---

    async def get_plugins(self) -> tuple[int, dict[str, Any]]:
        """List all installed plugins."""
        from vaultbot.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        plugins = [
            {
                "name": e.manifest.name,
                "version": e.manifest.version,
                "description": e.manifest.description,
                "enabled": e.enabled,
                "author": e.manifest.author,
            }
            for e in registry.list_plugins()
        ]
        return 200, {"plugins": plugins}

    async def enable_plugin(self, name: str) -> tuple[int, dict[str, Any]]:
        """Enable a plugin."""
        from vaultbot.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        if registry.enable(name):
            return 200, {"ok": True}
        return 404, {"error": f"Plugin '{name}' not found"}

    async def disable_plugin(self, name: str) -> tuple[int, dict[str, Any]]:
        """Disable a plugin."""
        from vaultbot.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        if registry.disable(name):
            return 200, {"ok": True}
        return 404, {"error": f"Plugin '{name}' not found"}

    async def uninstall_plugin(self, name: str) -> tuple[int, dict[str, Any]]:
        """Uninstall a plugin."""
        from vaultbot.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        entry = registry.unregister(name)
        if entry:
            return 200, {"ok": True}
        return 404, {"error": f"Plugin '{name}' not found"}

    # --- Teams ---

    async def get_teams(self) -> tuple[int, dict[str, Any]]:
        """List all teams."""
        teams = [t.to_dict() for t in self._ctx.teams.list_teams()]
        return 200, {"teams": teams}

    async def create_team(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Create a new team."""
        name = body.get("name", "")
        description = body.get("description", "")
        if not name:
            return 400, {"error": "name is required"}
        try:
            team = self._ctx.teams.create_team(name, description)
            return 200, {"ok": True, "team": team.to_dict()}
        except ValueError as e:
            return 400, {"error": str(e)}

    async def delete_team(self, name: str) -> tuple[int, dict[str, Any]]:
        """Delete a team."""
        if self._ctx.teams.delete_team(name):
            return 200, {"ok": True}
        return 404, {"error": f"Team '{name}' not found"}

    async def add_team_member(self, team_name: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Add a member to a team."""
        team = self._ctx.teams.get_team(team_name)
        if not team:
            return 404, {"error": f"Team '{team_name}' not found"}

        platform = body.get("platform", "")
        user_id = body.get("user_id", "")
        role_str = body.get("role", "user")
        if not platform or not user_id:
            return 400, {"error": "platform and user_id are required"}

        team.add_member(platform, user_id, Role(role_str))
        return 200, {"ok": True}

    async def remove_team_member(self, team_name: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Remove a member from a team."""
        team = self._ctx.teams.get_team(team_name)
        if not team:
            return 404, {"error": f"Team '{team_name}' not found"}

        platform = body.get("platform", "")
        user_id = body.get("user_id", "")
        if not platform or not user_id:
            return 400, {"error": "platform and user_id are required"}

        if team.remove_member(platform, user_id):
            return 200, {"ok": True}
        return 404, {"error": "Member not found"}

    # --- Credentials ---

    async def get_credentials(self) -> tuple[int, dict[str, Any]]:
        """List known credential keys with exists/missing status. Never returns values."""
        creds = []
        for key in _KNOWN_CREDENTIAL_KEYS:
            creds.append({"key": key, "exists": self._ctx.credentials.exists(key)})
        return 200, {"credentials": creds}

    async def set_credential(self, key: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Set a credential value."""
        value = body.get("value", "")
        if not value:
            return 400, {"error": "value is required"}

        self._ctx.credentials.set(key, value)
        self._ctx.audit.log(AuditEvent(
            event_type=EventType.CREDENTIAL_ACCESSED,
            details={"action": "set", "key": key, "source": "dashboard"},
        ))
        return 200, {"ok": True}

    async def delete_credential(self, key: str) -> tuple[int, dict[str, Any]]:
        """Delete a credential."""
        self._ctx.credentials.delete(key)
        self._ctx.audit.log(AuditEvent(
            event_type=EventType.CREDENTIAL_ACCESSED,
            details={"action": "delete", "key": key, "source": "dashboard"},
        ))
        return 200, {"ok": True}

    # --- Audit ---

    async def get_audit(self, limit: int = 50, event_type: str | None = None) -> tuple[int, dict[str, Any]]:
        """Return recent audit events from the in-memory buffer."""
        events = self._ctx.audit.recent(limit=limit, event_type=event_type)
        return 200, {"events": events}

    # --- Rate Limit ---

    async def get_ratelimit(self) -> tuple[int, dict[str, Any]]:
        """Return current rate limit config."""
        rl = self._ctx.config.rate_limit
        return 200, {
            "user_capacity": rl.user_capacity,
            "user_refill_rate": rl.user_refill_rate,
            "global_capacity": rl.global_capacity,
            "global_refill_rate": rl.global_refill_rate,
        }

    async def update_ratelimit(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Update rate limit settings (applied live)."""
        rl = self._ctx.config.rate_limit
        limiter = self._ctx.rate_limiter
        changes: list[str] = []

        if "user_capacity" in body:
            val = float(body["user_capacity"])
            rl.user_capacity = val
            limiter._user_capacity = val
            changes.append("user_capacity")

        if "user_refill_rate" in body:
            val = float(body["user_refill_rate"])
            rl.user_refill_rate = val
            limiter._user_refill_rate = val
            changes.append("user_refill_rate")

        if "global_capacity" in body:
            val = float(body["global_capacity"])
            rl.global_capacity = val
            limiter._global_bucket.capacity = val
            changes.append("global_capacity")

        if "global_refill_rate" in body:
            val = float(body["global_refill_rate"])
            rl.global_refill_rate = val
            limiter._global_bucket.refill_rate = val
            changes.append("global_refill_rate")

        if changes:
            self._ctx.config.save()
            self._ctx.audit.log(AuditEvent(
                event_type=EventType.CONFIG_CHANGED,
                details={"fields": changes, "source": "dashboard"},
            ))

        return 200, {"ok": True, "changes": changes}
