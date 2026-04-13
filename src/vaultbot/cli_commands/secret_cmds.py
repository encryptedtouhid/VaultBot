"""Secret management CLI commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecretInfo:
    name: str
    provider: str = "env"
    masked_value: str = "****"
    last_rotated: str = ""


class SecretCommands:
    """CLI commands for secret management."""

    def __init__(self) -> None:
        self._secrets: dict[str, SecretInfo] = {}

    def set_secret(self, name: str, provider: str = "env") -> SecretInfo:
        info = SecretInfo(name=name, provider=provider)
        self._secrets[name] = info
        return info

    def get_secret(self, name: str) -> SecretInfo | None:
        return self._secrets.get(name)

    def list_secrets(self) -> list[SecretInfo]:
        return list(self._secrets.values())

    def delete_secret(self, name: str) -> bool:
        if name in self._secrets:
            del self._secrets[name]
            return True
        return False

    def rotate(self, name: str) -> bool:
        return name in self._secrets
