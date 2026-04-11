"""Tests for multi-user and team management."""

import pytest

from zenbot.security.auth import Role
from zenbot.security.teams import Team, TeamManager


class TestTeam:
    def test_add_member(self) -> None:
        team = Team(name="devs")
        team.add_member("telegram", "user1")
        assert team.is_member("telegram", "user1")
        assert not team.is_member("telegram", "user999")

    def test_remove_member(self) -> None:
        team = Team(name="devs")
        team.add_member("telegram", "user1")
        assert team.remove_member("telegram", "user1")
        assert not team.is_member("telegram", "user1")

    def test_remove_nonexistent_member(self) -> None:
        team = Team(name="devs")
        assert not team.remove_member("telegram", "nobody")

    def test_member_roles(self) -> None:
        team = Team(name="devs")
        team.add_member("telegram", "admin1", Role.ADMIN)
        team.add_member("telegram", "user1", Role.USER)
        assert team.is_admin("telegram", "admin1")
        assert not team.is_admin("telegram", "user1")
        assert team.get_member_role("telegram", "admin1") == Role.ADMIN

    def test_update_existing_member_role(self) -> None:
        team = Team(name="devs")
        team.add_member("telegram", "user1", Role.USER)
        team.add_member("telegram", "user1", Role.ADMIN)
        assert team.is_admin("telegram", "user1")
        assert len(team.members) == 1

    def test_daily_budget(self) -> None:
        team = Team(name="devs", max_messages_per_day=3)
        assert team.has_budget()
        assert team.consume_budget()
        assert team.consume_budget()
        assert team.consume_budget()
        assert not team.has_budget()
        assert not team.consume_budget()

    def test_reset_daily_budget(self) -> None:
        team = Team(name="devs", max_messages_per_day=1)
        team.consume_budget()
        assert not team.has_budget()
        team.reset_daily_budget()
        assert team.has_budget()

    def test_serialization(self) -> None:
        team = Team(name="devs", description="Dev team")
        team.add_member("telegram", "user1", Role.ADMIN)
        team.enabled_plugins = ["weather"]

        data = team.to_dict()
        restored = Team.from_dict(data)

        assert restored.name == "devs"
        assert restored.description == "Dev team"
        assert len(restored.members) == 1
        assert restored.members[0].role == Role.ADMIN
        assert restored.enabled_plugins == ["weather"]

    def test_cross_platform_isolation(self) -> None:
        team = Team(name="devs")
        team.add_member("telegram", "user1")
        assert team.is_member("telegram", "user1")
        assert not team.is_member("discord", "user1")


class TestTeamManager:
    def test_create_and_get_team(self) -> None:
        mgr = TeamManager()
        mgr.create_team("devs", "Dev team")
        team = mgr.get_team("devs")
        assert team is not None
        assert team.name == "devs"

    def test_create_duplicate_raises(self) -> None:
        mgr = TeamManager()
        mgr.create_team("devs")
        with pytest.raises(ValueError, match="already exists"):
            mgr.create_team("devs")

    def test_delete_team(self) -> None:
        mgr = TeamManager()
        mgr.create_team("devs")
        assert mgr.delete_team("devs")
        assert mgr.get_team("devs") is None

    def test_delete_nonexistent(self) -> None:
        mgr = TeamManager()
        assert not mgr.delete_team("nope")

    def test_list_teams(self) -> None:
        mgr = TeamManager()
        mgr.create_team("team-a")
        mgr.create_team("team-b")
        assert len(mgr.list_teams()) == 2

    def test_get_user_teams(self) -> None:
        mgr = TeamManager()
        t1 = mgr.create_team("team-a")
        t2 = mgr.create_team("team-b")
        t1.add_member("telegram", "user1")
        t2.add_member("telegram", "user1")

        teams = mgr.get_user_teams("telegram", "user1")
        assert len(teams) == 2

    def test_reset_all_budgets(self) -> None:
        mgr = TeamManager()
        t1 = mgr.create_team("team-a")
        t2 = mgr.create_team("team-b")
        t1.max_messages_per_day = 1
        t2.max_messages_per_day = 1
        t1.consume_budget()
        t2.consume_budget()

        assert not t1.has_budget()
        assert not t2.has_budget()

        mgr.reset_all_daily_budgets()
        assert t1.has_budget()
        assert t2.has_budget()
