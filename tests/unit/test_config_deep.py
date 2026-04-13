"""Unit tests for deep config system."""

from __future__ import annotations

import pytest

from vaultbot.config.env_substitution import substitute_dict, substitute_env
from vaultbot.config.migration import ConfigMigrator, MigrationStep


class TestEnvSubstitution:
    def test_substitute_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_VAR", "hello")
        assert substitute_env("${TEST_VAR}") == "hello"

    def test_substitute_with_default(self) -> None:
        result = substitute_env("${MISSING_VAR:-fallback}")
        assert result == "fallback"

    def test_no_substitution(self) -> None:
        assert substitute_env("plain text") == "plain text"

    def test_substitute_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "localhost")
        data = {"host": "${DB_HOST}", "port": 5432, "nested": {"url": "${DB_HOST}:5432"}}
        result = substitute_dict(data)
        assert result["host"] == "localhost"
        assert result["port"] == 5432
        assert result["nested"]["url"] == "localhost:5432"


class TestConfigMigrator:
    def test_needs_migration(self) -> None:
        migrator = ConfigMigrator()
        assert migrator.needs_migration({"_config_version": 1}, target_version=2) is True
        assert migrator.needs_migration({"_config_version": 2}, target_version=2) is False

    def test_migrate(self) -> None:
        migrator = ConfigMigrator()
        migrator.add_migration(
            MigrationStep(from_version=0, to_version=1, description="Add logging")
        )
        migrator.add_migration(MigrationStep(from_version=1, to_version=2, description="Add auth"))
        config, steps = migrator.migrate({"_config_version": 0}, target_version=2)
        assert config["_config_version"] == 2
        assert len(steps) == 2

    def test_no_migration_needed(self) -> None:
        migrator = ConfigMigrator()
        config, steps = migrator.migrate({"_config_version": 5}, target_version=5)
        assert len(steps) == 0

    def test_get_version_default(self) -> None:
        migrator = ConfigMigrator()
        assert migrator.get_version({}) == 0
