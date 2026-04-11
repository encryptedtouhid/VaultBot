"""Security policy engine with immutable defaults.

Certain security settings cannot be turned off. The policy engine enforces
this at runtime, overriding any user configuration that attempts to weaken
the security posture.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ActionSeverity(str, Enum):
    """Severity levels for bot actions. Higher = more dangerous."""

    INFO = "info"  # Read-only, auto-approved
    LOW = "low"  # Auto-approved with audit log
    MEDIUM = "medium"  # Requires explicit user confirmation
    HIGH = "high"  # Confirmation + cooldown
    CRITICAL = "critical"  # Confirmation + passphrase/2FA


# These defaults CANNOT be overridden to less secure values
_IMMUTABLE_DEFAULTS: dict[str, Any] = {
    "auth.require_allowlist": True,
    "plugins.require_signature": True,
    "actions.require_approval_medium_and_above": True,
    "audit.enabled": True,
}


class SecurityPolicy:
    """Enforces security policies with immutable defaults."""

    def __init__(self, user_config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = {}
        if user_config:
            self._config.update(user_config)
        self._enforce_immutable_defaults()

    def _enforce_immutable_defaults(self) -> None:
        """Override any user config that weakens immutable security settings."""
        for key, required_value in _IMMUTABLE_DEFAULTS.items():
            if self._config.get(key) != required_value:
                if key in self._config:
                    logger.warning(
                        "immutable_policy_enforced",
                        key=key,
                        attempted_value=self._config[key],
                        enforced_value=required_value,
                    )
                self._config[key] = required_value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a policy value."""
        return self._config.get(key, default)

    def requires_approval(self, severity: ActionSeverity) -> bool:
        """Check if an action of this severity requires user approval."""
        if severity in (ActionSeverity.INFO, ActionSeverity.LOW):
            return False
        return True

    def requires_cooldown(self, severity: ActionSeverity) -> bool:
        """Check if an action requires a cooldown period after approval."""
        return severity in (ActionSeverity.HIGH, ActionSeverity.CRITICAL)

    def requires_2fa(self, severity: ActionSeverity) -> bool:
        """Check if an action requires secondary authentication."""
        return severity == ActionSeverity.CRITICAL

    @staticmethod
    def classify_action(action_name: str) -> ActionSeverity:
        """Classify an action's severity based on its name/type.

        This is the default classifier. Plugins can declare their own
        severity levels in their manifests.
        """
        destructive = {"delete", "remove", "drop", "reset", "format", "kill"}
        sensitive = {"send", "post", "publish", "deploy", "execute", "install"}
        read_only = {"get", "list", "read", "search", "fetch", "check"}

        action_lower = action_name.lower()

        for keyword in destructive:
            if keyword in action_lower:
                return ActionSeverity.HIGH

        for keyword in sensitive:
            if keyword in action_lower:
                return ActionSeverity.MEDIUM

        for keyword in read_only:
            if keyword in action_lower:
                return ActionSeverity.INFO

        # Default to MEDIUM for unknown actions (safe default)
        return ActionSeverity.MEDIUM
