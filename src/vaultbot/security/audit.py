"""Structured audit logging for security events.

All actions, authentication events, plugin loads, config changes, and errors
are logged. Logs are append-only — the bot process cannot delete them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

_AUDIT_LOG_DIR = Path.home() / ".vaultbot" / "audit"


class EventType(str, Enum):
    """Categories of auditable events."""

    AUTH_SUCCESS = "auth.success"
    AUTH_DENIED = "auth.denied"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    ACTION_REQUESTED = "action.requested"
    ACTION_APPROVED = "action.approved"
    ACTION_DENIED = "action.denied"
    ACTION_EXECUTED = "action.executed"
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_REJECTED = "plugin.rejected"
    CONFIG_CHANGED = "config.changed"
    CREDENTIAL_ACCESSED = "credential.accessed"
    RATE_LIMITED = "rate.limited"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A single auditable event."""

    event_type: EventType
    platform: str = ""
    user_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class AuditLogger:
    """Append-only structured audit logger.

    Writes to the 'vaultbot.audit' logger which is routed to:
    - Console (via root logger)
    - ~/.vaultbot/logs/audit.log (dedicated audit file)
    - ~/.vaultbot/logs/zenbot.log (main application log)
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        self._log_dir = log_dir or _AUDIT_LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._logger = structlog.get_logger("vaultbot.audit")

    def log(self, event: AuditEvent) -> None:
        """Record an audit event."""
        self._logger.info(
            event.event_type.value,
            platform=event.platform,
            user_id=event.user_id,
            timestamp=event.timestamp,
            **event.details,
        )

    def log_auth(
        self, *, platform: str, user_id: str, success: bool, reason: str = ""
    ) -> None:
        """Shorthand for logging authentication events."""
        event_type = EventType.AUTH_SUCCESS if success else EventType.AUTH_DENIED
        self.log(
            AuditEvent(
                event_type=event_type,
                platform=platform,
                user_id=user_id,
                details={"reason": reason},
            )
        )

    def log_action(
        self,
        *,
        event_type: EventType,
        platform: str = "",
        user_id: str = "",
        action_name: str = "",
        severity: str = "",
        **extra: Any,
    ) -> None:
        """Shorthand for logging action-related events."""
        self.log(
            AuditEvent(
                event_type=event_type,
                platform=platform,
                user_id=user_id,
                details={"action": action_name, "severity": severity, **extra},
            )
        )

    def log_error(
        self, *, error: str, platform: str = "", user_id: str = "", **extra: Any
    ) -> None:
        """Log an error event."""
        self.log(
            AuditEvent(
                event_type=EventType.ERROR,
                platform=platform,
                user_id=user_id,
                details={"error": error, **extra},
            )
        )
