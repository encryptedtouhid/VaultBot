"""User authentication and access control.

Zero-trust model: every user must be explicitly allow-listed before the bot
responds. Unknown senders receive a "not authorized" message and an audit entry.
"""

from __future__ import annotations

from enum import Enum

from zenbot.utils.logging import get_logger

logger = get_logger(__name__)


class Role(str, Enum):
    """User roles with ascending privilege levels."""

    USER = "user"
    ADMIN = "admin"


class AuthManager:
    """Manages user allowlist and role-based access control."""

    def __init__(self, allowlist: dict[str, Role] | None = None) -> None:
        # Maps platform-qualified user ID -> role
        # e.g. "telegram:123456" -> Role.ADMIN
        self._allowlist: dict[str, Role] = allowlist or {}

    @staticmethod
    def _qualify_id(platform: str, user_id: str) -> str:
        """Create a platform-qualified user identifier."""
        return f"{platform}:{user_id}"

    def is_authorized(self, platform: str, user_id: str) -> bool:
        """Check if a user is in the allowlist."""
        qualified = self._qualify_id(platform, user_id)
        authorized = qualified in self._allowlist

        if not authorized:
            logger.warning(
                "auth_denied",
                platform=platform,
                user_id=user_id,
                reason="not_in_allowlist",
            )

        return authorized

    def get_role(self, platform: str, user_id: str) -> Role | None:
        """Get the role of an authorized user."""
        qualified = self._qualify_id(platform, user_id)
        return self._allowlist.get(qualified)

    def is_admin(self, platform: str, user_id: str) -> bool:
        """Check if a user has admin privileges."""
        return self.get_role(platform, user_id) == Role.ADMIN

    def add_user(self, platform: str, user_id: str, role: Role = Role.USER) -> None:
        """Add a user to the allowlist. Requires admin action."""
        qualified = self._qualify_id(platform, user_id)
        self._allowlist[qualified] = role
        logger.info("user_added", qualified_id=qualified, role=role.value)

    def remove_user(self, platform: str, user_id: str) -> None:
        """Remove a user from the allowlist."""
        qualified = self._qualify_id(platform, user_id)
        self._allowlist.pop(qualified, None)
        logger.info("user_removed", qualified_id=qualified)

    def list_users(self) -> dict[str, str]:
        """Return the current allowlist as {qualified_id: role}."""
        return {k: v.value for k, v in self._allowlist.items()}
