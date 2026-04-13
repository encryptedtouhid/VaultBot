"""Plugin config schema validation with JSON Schema support."""

from __future__ import annotations

from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SchemaField:
    name: str
    field_type: str = "string"  # string, int, bool, list, dict
    required: bool = False
    default: object = None
    description: str = ""
    choices: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PluginConfigSchema:
    plugin_name: str
    fields: list[SchemaField] = field(default_factory=list)
    version: str = "1.0"


class ConfigSchemaValidator:
    """Validates plugin config against schemas."""

    def __init__(self) -> None:
        self._schemas: dict[str, PluginConfigSchema] = {}

    def register_schema(self, schema: PluginConfigSchema) -> None:
        self._schemas[schema.plugin_name] = schema

    def get_schema(self, plugin_name: str) -> PluginConfigSchema | None:
        return self._schemas.get(plugin_name)

    def validate(self, plugin_name: str, config: dict[str, object]) -> list[str]:
        """Validate config against schema. Returns list of errors."""
        schema = self._schemas.get(plugin_name)
        if not schema:
            return [f"No schema registered for {plugin_name}"]

        errors: list[str] = []
        for sf in schema.fields:
            if sf.required and sf.name not in config:
                errors.append(f"Missing required field: {sf.name}")
            if sf.name in config and sf.choices:
                if str(config[sf.name]) not in sf.choices:
                    errors.append(f"Invalid value for {sf.name}: must be one of {sf.choices}")
        return errors

    def get_defaults(self, plugin_name: str) -> dict[str, object]:
        """Get default config values for a plugin."""
        schema = self._schemas.get(plugin_name)
        if not schema:
            return {}
        return {sf.name: sf.default for sf in schema.fields if sf.default is not None}

    @property
    def schema_count(self) -> int:
        return len(self._schemas)
