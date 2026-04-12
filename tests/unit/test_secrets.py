"""Unit tests for secrets management."""

from __future__ import annotations

import pytest

from vaultbot.security.secrets import (
    EnvSecretProvider,
    SecretManager,
    SecretProvider,
    SecretRef,
    SecretType,
    StaticSecretProvider,
)


class TestEnvSecretProvider:
    def test_is_provider(self) -> None:
        assert isinstance(EnvSecretProvider(), SecretProvider)

    @pytest.mark.asyncio
    async def test_resolve_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_SECRET", "secret_value")
        provider = EnvSecretProvider()
        value = await provider.resolve(SecretRef(name="TEST_SECRET", secret_type=SecretType.ENV))
        assert value == "secret_value"

    @pytest.mark.asyncio
    async def test_resolve_missing(self) -> None:
        provider = EnvSecretProvider()
        value = await provider.resolve(
            SecretRef(name="NONEXISTENT_VAR_XYZ", secret_type=SecretType.ENV)
        )
        assert value == ""


class TestStaticSecretProvider:
    def test_is_provider(self) -> None:
        assert isinstance(StaticSecretProvider(), SecretProvider)

    @pytest.mark.asyncio
    async def test_resolve(self) -> None:
        provider = StaticSecretProvider({"api_key": "sk-test"})
        value = await provider.resolve(SecretRef(name="api_key", secret_type=SecretType.STATIC))
        assert value == "sk-test"

    @pytest.mark.asyncio
    async def test_resolve_missing(self) -> None:
        provider = StaticSecretProvider()
        value = await provider.resolve(SecretRef(name="nope", secret_type=SecretType.STATIC))
        assert value == ""


class TestSecretManager:
    @pytest.mark.asyncio
    async def test_resolve_with_provider(self) -> None:
        mgr = SecretManager()
        mgr.register_provider(StaticSecretProvider({"key": "val"}))
        result = await mgr.resolve(SecretRef(name="key", secret_type=SecretType.STATIC))
        assert result.value == "val"
        assert result.cached is False

    @pytest.mark.asyncio
    async def test_resolve_cached(self) -> None:
        mgr = SecretManager()
        mgr.register_provider(StaticSecretProvider({"key": "val"}))
        await mgr.resolve(SecretRef(name="key", secret_type=SecretType.STATIC))
        result = await mgr.resolve(SecretRef(name="key", secret_type=SecretType.STATIC))
        assert result.cached is True

    @pytest.mark.asyncio
    async def test_resolve_no_provider(self) -> None:
        mgr = SecretManager()
        with pytest.raises(ValueError, match="No provider"):
            await mgr.resolve(SecretRef(name="key", secret_type=SecretType.EXEC))

    @pytest.mark.asyncio
    async def test_invalidate_cache(self) -> None:
        mgr = SecretManager()
        mgr.register_provider(StaticSecretProvider({"key": "val"}))
        await mgr.resolve(SecretRef(name="key", secret_type=SecretType.STATIC))
        assert mgr.invalidate("key") is True
        assert mgr.cache_size == 0

    @pytest.mark.asyncio
    async def test_audit_log(self) -> None:
        mgr = SecretManager()
        mgr.register_provider(StaticSecretProvider({"key": "val"}))
        await mgr.resolve(SecretRef(name="key", secret_type=SecretType.STATIC), accessor="user1")
        logs = mgr.get_audit_log("key")
        assert len(logs) == 1
        assert logs[0].accessor == "user1"
