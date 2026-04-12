"""Unit tests for key rotation and credential profiles."""

from __future__ import annotations

import time

from vaultbot.security.key_rotation import (
    CredentialProfile,
    KeyRotationManager,
    ProfileManager,
)


class TestKeyRotationManager:
    def test_register_and_get(self) -> None:
        mgr = KeyRotationManager()
        mgr.register_key("openai", "sk-test")
        assert mgr.get_key("openai") == "sk-test"
        assert mgr.key_count == 1

    def test_get_missing(self) -> None:
        mgr = KeyRotationManager()
        assert mgr.get_key("nope") is None

    def test_rotate_key(self) -> None:
        mgr = KeyRotationManager()
        mgr.register_key("openai", "old")
        assert mgr.rotate_key("openai", "new") is True
        assert mgr.get_key("openai") == "new"
        assert mgr.rotation_count == 1

    def test_revoke_key(self) -> None:
        mgr = KeyRotationManager()
        mgr.register_key("openai", "sk-test")
        assert mgr.revoke_key("openai") is True
        assert mgr.get_key("openai") is None

    def test_check_expiring(self) -> None:
        mgr = KeyRotationManager()
        mgr.register_key("soon", "sk-1", expires_at=time.time() + 3600)
        mgr.register_key("later", "sk-2", expires_at=time.time() + 999999)
        expiring = mgr.check_expiring(within_seconds=86400)
        assert len(expiring) == 1
        assert expiring[0].name == "soon"


class TestProfileManager:
    def test_add_and_get(self) -> None:
        mgr = ProfileManager()
        mgr.add_profile(CredentialProfile(name="dev", keys={"api": "key1"}))
        assert mgr.get_profile("dev") is not None

    def test_first_is_active(self) -> None:
        mgr = ProfileManager()
        mgr.add_profile(CredentialProfile(name="dev"))
        assert mgr.active_profile == "dev"

    def test_set_active(self) -> None:
        mgr = ProfileManager()
        mgr.add_profile(CredentialProfile(name="dev"))
        mgr.add_profile(CredentialProfile(name="prod"))
        assert mgr.set_active("prod") is True
        assert mgr.active_profile == "prod"

    def test_set_active_missing(self) -> None:
        mgr = ProfileManager()
        assert mgr.set_active("nope") is False

    def test_list_profiles(self) -> None:
        mgr = ProfileManager()
        mgr.add_profile(CredentialProfile(name="dev"))
        mgr.add_profile(CredentialProfile(name="prod"))
        assert set(mgr.list_profiles()) == {"dev", "prod"}
