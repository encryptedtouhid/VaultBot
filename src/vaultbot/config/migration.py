"""Legacy config migration with version tracking."""

from __future__ import annotations

from dataclasses import dataclass

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MigrationStep:
    from_version: int
    to_version: int
    description: str = ""
    transform: str = ""  # Key path of the transformation


class ConfigMigrator:
    """Migrates config between versions."""

    def __init__(self) -> None:
        self._migrations: list[MigrationStep] = []

    def add_migration(self, step: MigrationStep) -> None:
        self._migrations.append(step)
        self._migrations.sort(key=lambda s: s.from_version)

    def get_version(self, config: dict[str, object]) -> int:
        return int(config.get("_config_version", 0))

    def needs_migration(self, config: dict[str, object], target_version: int) -> bool:
        return self.get_version(config) < target_version

    def migrate(
        self, config: dict[str, object], target_version: int
    ) -> tuple[dict[str, object], list[MigrationStep]]:
        """Migrate config to target version. Returns (new_config, applied_steps)."""
        current = self.get_version(config)
        applied: list[MigrationStep] = []
        result = dict(config)

        for step in self._migrations:
            if step.from_version >= current and step.to_version <= target_version:
                result["_config_version"] = step.to_version
                applied.append(step)
                logger.info(
                    "config_migrated",
                    from_v=step.from_version,
                    to_v=step.to_version,
                )

        return result, applied

    @property
    def migration_count(self) -> int:
        return len(self._migrations)
