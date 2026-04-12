"""Secrets management with provider resolution, caching, and audit trails."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SecretType(str, Enum):
    ENV = "env"
    FILE = "file"
    EXEC = "exec"
    OAUTH = "oauth"
    STATIC = "static"


@dataclass(frozen=True, slots=True)
class SecretRef:
    """A reference to a secret."""

    name: str
    secret_type: SecretType = SecretType.ENV
    source: str = ""


@dataclass(frozen=True, slots=True)
class ResolvedSecret:
    name: str
    value: str
    secret_type: SecretType
    resolved_at: float = field(default_factory=time.time)
    cached: bool = False


@dataclass(frozen=True, slots=True)
class SecretAccessLog:
    name: str
    accessor: str
    timestamp: float = field(default_factory=time.time)


@runtime_checkable
class SecretProvider(Protocol):
    @property
    def provider_type(self) -> SecretType: ...
    async def resolve(self, ref: SecretRef) -> str: ...


class EnvSecretProvider:
    """Resolve secrets from environment variables."""

    @property
    def provider_type(self) -> SecretType:
        return SecretType.ENV

    async def resolve(self, ref: SecretRef) -> str:
        value = os.environ.get(ref.source or ref.name, "")
        return value


class StaticSecretProvider:
    """Resolve secrets from a static map."""

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets = secrets or {}

    @property
    def provider_type(self) -> SecretType:
        return SecretType.STATIC

    async def resolve(self, ref: SecretRef) -> str:
        return self._secrets.get(ref.name, "")

    def set(self, name: str, value: str) -> None:
        self._secrets[name] = value


class SecretManager:
    """Manages secret resolution with caching and audit."""

    def __init__(self, cache_ttl: float = 300.0) -> None:
        self._providers: dict[SecretType, SecretProvider] = {}
        self._cache: dict[str, ResolvedSecret] = {}
        self._cache_ttl = cache_ttl
        self._audit_log: list[SecretAccessLog] = []

    def register_provider(self, provider: SecretProvider) -> None:
        self._providers[provider.provider_type] = provider

    async def resolve(self, ref: SecretRef, accessor: str = "") -> ResolvedSecret:
        # Check cache
        cached = self._cache.get(ref.name)
        if cached and (time.time() - cached.resolved_at) < self._cache_ttl:
            self._audit_log.append(SecretAccessLog(name=ref.name, accessor=accessor))
            return ResolvedSecret(
                name=ref.name,
                value=cached.value,
                secret_type=ref.secret_type,
                cached=True,
            )

        provider = self._providers.get(ref.secret_type)
        if not provider:
            raise ValueError(f"No provider for secret type: {ref.secret_type}")

        value = await provider.resolve(ref)
        resolved = ResolvedSecret(name=ref.name, value=value, secret_type=ref.secret_type)
        self._cache[ref.name] = resolved
        self._audit_log.append(SecretAccessLog(name=ref.name, accessor=accessor))
        return resolved

    def invalidate(self, name: str) -> bool:
        if name in self._cache:
            del self._cache[name]
            return True
        return False

    def get_audit_log(self, name: str = "", limit: int = 50) -> list[SecretAccessLog]:
        logs = self._audit_log
        if name:
            logs = [log for log in logs if log.name == name]
        return logs[-limit:]

    @property
    def cache_size(self) -> int:
        return len(self._cache)
