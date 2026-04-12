"""Unit tests for cross-platform reactions."""

from __future__ import annotations

from vaultbot.core.reactions import ReactionManager, normalize_emoji


class TestNormalizeEmoji:
    def test_alias(self) -> None:
        assert normalize_emoji(":thumbsup:") == "\U0001f44d"
        assert normalize_emoji("+1") == "\U0001f44d"

    def test_passthrough(self) -> None:
        assert normalize_emoji("\U0001f44d") == "\U0001f44d"


class TestReactionManager:
    def test_add_reaction(self) -> None:
        mgr = ReactionManager()
        r = mgr.add_reaction("msg1", ":heart:", "user1", "discord")
        assert r.emoji == "\u2764\ufe0f"

    def test_get_reactions(self) -> None:
        mgr = ReactionManager()
        mgr.add_reaction("msg1", ":fire:", "user1", "telegram")
        mgr.add_reaction("msg1", ":fire:", "user2", "telegram")
        assert len(mgr.get_reactions("msg1")) == 2

    def test_get_reactions_empty(self) -> None:
        mgr = ReactionManager()
        assert mgr.get_reactions("nope") == []

    def test_remove_reaction(self) -> None:
        mgr = ReactionManager()
        mgr.add_reaction("msg1", ":fire:", "user1", "telegram")
        assert mgr.remove_reaction("msg1", ":fire:", "user1") is True
        assert len(mgr.get_reactions("msg1")) == 0

    def test_remove_nonexistent(self) -> None:
        mgr = ReactionManager()
        assert mgr.remove_reaction("msg1", ":fire:", "user1") is False

    def test_reaction_counts(self) -> None:
        mgr = ReactionManager()
        mgr.add_reaction("msg1", ":fire:", "u1", "tg")
        mgr.add_reaction("msg1", ":fire:", "u2", "tg")
        mgr.add_reaction("msg1", ":heart:", "u1", "tg")
        counts = mgr.get_reaction_counts("msg1")
        assert counts["\U0001f525"] == 2
        assert counts["\u2764\ufe0f"] == 1

    def test_clear_reactions(self) -> None:
        mgr = ReactionManager()
        mgr.add_reaction("msg1", ":fire:", "u1", "tg")
        mgr.clear_reactions("msg1")
        assert mgr.get_reactions("msg1") == []
