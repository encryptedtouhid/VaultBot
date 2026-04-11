"""Multi-user and team management.

Extends the auth system with team-based access control:
- Users can belong to multiple teams
- Teams share conversation contexts and plugin configurations
- Per-team rate limits and permissions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vaultbot.security.auth import Role
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TeamMember:
    """A user's membership in a team."""

    user_id: str
    platform: str
    role: Role = Role.USER

    @property
    def qualified_id(self) -> str:
        return f"{self.platform}:{self.user_id}"


@dataclass
class Team:
    """A team with shared access and configuration."""

    name: str
    description: str = ""
    members: list[TeamMember] = field(default_factory=list)
    enabled_plugins: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)

    # Per-team limits
    max_messages_per_day: int = 1000
    daily_message_count: int = 0

    def add_member(
        self, platform: str, user_id: str, role: Role = Role.USER
    ) -> None:
        """Add a member to the team."""
        # Check for duplicates
        qualified = f"{platform}:{user_id}"
        for member in self.members:
            if member.qualified_id == qualified:
                member.role = role
                logger.info("team_member_updated", team=self.name, user=qualified)
                return
        self.members.append(TeamMember(user_id=user_id, platform=platform, role=role))
        logger.info("team_member_added", team=self.name, user=qualified)

    def remove_member(self, platform: str, user_id: str) -> bool:
        """Remove a member from the team."""
        qualified = f"{platform}:{user_id}"
        before = len(self.members)
        self.members = [m for m in self.members if m.qualified_id != qualified]
        removed = len(self.members) < before
        if removed:
            logger.info("team_member_removed", team=self.name, user=qualified)
        return removed

    def is_member(self, platform: str, user_id: str) -> bool:
        """Check if a user is in this team."""
        qualified = f"{platform}:{user_id}"
        return any(m.qualified_id == qualified for m in self.members)

    def get_member_role(self, platform: str, user_id: str) -> Role | None:
        """Get a member's role in this team."""
        qualified = f"{platform}:{user_id}"
        for member in self.members:
            if member.qualified_id == qualified:
                return member.role
        return None

    def is_admin(self, platform: str, user_id: str) -> bool:
        """Check if a user is a team admin."""
        return self.get_member_role(platform, user_id) == Role.ADMIN

    def has_budget(self) -> bool:
        """Check if the team has remaining message budget."""
        return self.daily_message_count < self.max_messages_per_day

    def consume_budget(self) -> bool:
        """Consume one message from the team budget. Returns False if over limit."""
        if not self.has_budget():
            return False
        self.daily_message_count += 1
        return True

    def reset_daily_budget(self) -> None:
        """Reset the daily message counter (call via scheduled job)."""
        self.daily_message_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "members": [
                {"user_id": m.user_id, "platform": m.platform, "role": m.role.value}
                for m in self.members
            ],
            "enabled_plugins": self.enabled_plugins,
            "settings": self.settings,
            "max_messages_per_day": self.max_messages_per_day,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Team:
        team = cls(
            name=data["name"],
            description=data.get("description", ""),
            enabled_plugins=data.get("enabled_plugins", []),
            settings=data.get("settings", {}),
            max_messages_per_day=data.get("max_messages_per_day", 1000),
        )
        for m in data.get("members", []):
            team.members.append(
                TeamMember(
                    user_id=m["user_id"],
                    platform=m["platform"],
                    role=Role(m.get("role", "user")),
                )
            )
        return team


class TeamManager:
    """Manages teams and provides team-aware lookups."""

    def __init__(self) -> None:
        self._teams: dict[str, Team] = {}

    def create_team(self, name: str, description: str = "") -> Team:
        """Create a new team."""
        if name in self._teams:
            raise ValueError(f"Team '{name}' already exists.")
        team = Team(name=name, description=description)
        self._teams[name] = team
        logger.info("team_created", team=name)
        return team

    def get_team(self, name: str) -> Team | None:
        """Get a team by name."""
        return self._teams.get(name)

    def delete_team(self, name: str) -> bool:
        """Delete a team."""
        if name in self._teams:
            del self._teams[name]
            logger.info("team_deleted", team=name)
            return True
        return False

    def list_teams(self) -> list[Team]:
        """List all teams."""
        return list(self._teams.values())

    def get_user_teams(self, platform: str, user_id: str) -> list[Team]:
        """Get all teams a user belongs to."""
        return [
            team for team in self._teams.values()
            if team.is_member(platform, user_id)
        ]

    def is_team_member(self, team_name: str, platform: str, user_id: str) -> bool:
        """Check if a user is a member of a specific team."""
        team = self._teams.get(team_name)
        if team is None:
            return False
        return team.is_member(platform, user_id)

    def reset_all_daily_budgets(self) -> None:
        """Reset daily budgets for all teams."""
        for team in self._teams.values():
            team.reset_daily_budget()
