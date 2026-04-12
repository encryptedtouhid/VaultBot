"""Unit tests for conversation labels."""

from __future__ import annotations

from vaultbot.core.labels import LabelManager


class TestLabelManager:
    def test_set_name(self) -> None:
        mgr = LabelManager()
        mgr.set_name("c1", "Bug Discussion")
        assert mgr.get_or_create("c1").name == "Bug Discussion"

    def test_add_label(self) -> None:
        mgr = LabelManager()
        mgr.add_label("c1", "important", "red")
        labels = mgr.get_labels("c1")
        assert len(labels) == 1
        assert labels[0].name == "important"

    def test_add_duplicate_label(self) -> None:
        mgr = LabelManager()
        mgr.add_label("c1", "bug")
        mgr.add_label("c1", "bug")
        assert len(mgr.get_labels("c1")) == 1

    def test_remove_label(self) -> None:
        mgr = LabelManager()
        mgr.add_label("c1", "bug")
        assert mgr.remove_label("c1", "bug") is True
        assert len(mgr.get_labels("c1")) == 0

    def test_remove_nonexistent(self) -> None:
        mgr = LabelManager()
        assert mgr.remove_label("nope", "bug") is False

    def test_search_by_label(self) -> None:
        mgr = LabelManager()
        mgr.add_label("c1", "bug")
        mgr.add_label("c2", "feature")
        mgr.add_label("c3", "bug")
        results = mgr.search_by_label("bug")
        assert set(results) == {"c1", "c3"}

    def test_auto_name(self) -> None:
        mgr = LabelManager()
        name = mgr.auto_name("c1", "How do I configure the database?")
        assert name == "How do I configure the database?"

    def test_auto_name_long(self) -> None:
        mgr = LabelManager()
        name = mgr.auto_name("c1", "x" * 100)
        assert name.endswith("...")
        assert len(name) <= 54

    def test_get_labels_empty(self) -> None:
        mgr = LabelManager()
        assert mgr.get_labels("nope") == []
