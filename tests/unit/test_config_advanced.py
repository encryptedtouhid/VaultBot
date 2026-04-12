"""Unit tests for advanced config system."""

from __future__ import annotations

from vaultbot.config.hot_reload import HotReloadConfig, validate_config


class TestHotReloadConfig:
    def test_get_set(self) -> None:
        cfg = HotReloadConfig()
        cfg.set("key", "value")
        assert cfg.get("key") == "value"

    def test_get_default(self) -> None:
        cfg = HotReloadConfig()
        assert cfg.get("missing", "default") == "default"

    def test_patch(self) -> None:
        cfg = HotReloadConfig()
        cfg.patch({"a": 1, "b": 2})
        assert cfg.get("a") == 1
        assert cfg.get("b") == 2

    def test_version_increments(self) -> None:
        cfg = HotReloadConfig()
        cfg.set("a", 1)
        cfg.set("b", 2)
        assert cfg.version == 2

    def test_listener(self) -> None:
        cfg = HotReloadConfig()
        received: list[dict] = []
        cfg.add_listener(lambda d: received.append(d))
        cfg.set("key", "value")
        assert len(received) == 1

    def test_remove_listener(self) -> None:
        cfg = HotReloadConfig()
        cb = lambda d: None  # noqa: E731
        cfg.add_listener(cb)
        assert cfg.remove_listener(cb) is True

    def test_snapshot(self) -> None:
        cfg = HotReloadConfig()
        cfg.set("key", "value")
        snap = cfg.snapshot()
        assert snap.data["key"] == "value"
        assert snap.version == 1

    def test_reload(self) -> None:
        cfg = HotReloadConfig()
        cfg.set("old", "data")
        cfg.reload({"new": "data"})
        assert cfg.get("new") == "data"
        assert cfg.get("old") is None


class TestValidation:
    def test_valid(self) -> None:
        errors = validate_config({"name": "test", "port": 8080}, {"name": str, "port": int})
        assert errors == []

    def test_missing_key(self) -> None:
        errors = validate_config({}, {"name": str})
        assert len(errors) == 1
        assert "Missing" in errors[0]

    def test_wrong_type(self) -> None:
        errors = validate_config({"port": "not_int"}, {"port": int})
        assert len(errors) == 1
        assert "Invalid type" in errors[0]
