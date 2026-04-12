"""Live API key rotation and credential profiles."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class KeyStatus(str, Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(slots=True)
class APIKey:
    name: str
    key_value: str
    status: KeyStatus = KeyStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    last_used: float = 0.0
    use_count: int = 0


@dataclass(frozen=True, slots=True)
class CredentialProfile:
    name: str
    keys: dict[str, str] = field(default_factory=dict)
    description: str = ""


class KeyRotationManager:
    """Manages live API key rotation without restart."""

    def __init__(self) -> None:
        self._keys: dict[str, APIKey] = {}
        self._rotation_count = 0

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def register_key(self, name: str, key_value: str, expires_at: float = 0.0) -> APIKey:
        key = APIKey(name=name, key_value=key_value, expires_at=expires_at)
        self._keys[name] = key
        logger.info("key_registered", name=name)
        return key

    def get_key(self, name: str) -> str | None:
        key = self._keys.get(name)
        if key and key.status == KeyStatus.ACTIVE:
            key.last_used = time.time()
            key.use_count += 1
            return key.key_value
        return None

    def rotate_key(self, name: str, new_value: str) -> bool:
        key = self._keys.get(name)
        if not key:
            return False
        key.status = KeyStatus.ROTATING
        key.key_value = new_value
        key.status = KeyStatus.ACTIVE
        key.created_at = time.time()
        self._rotation_count += 1
        logger.info("key_rotated", name=name)
        return True

    def revoke_key(self, name: str) -> bool:
        key = self._keys.get(name)
        if not key:
            return False
        key.status = KeyStatus.REVOKED
        return True

    def check_expiring(self, within_seconds: float = 86400) -> list[APIKey]:
        now = time.time()
        return [
            k
            for k in self._keys.values()
            if k.expires_at > 0
            and (k.expires_at - now) < within_seconds
            and k.status == KeyStatus.ACTIVE
        ]

    @property
    def rotation_count(self) -> int:
        return self._rotation_count


class ProfileManager:
    """Manages credential profiles for different environments."""

    def __init__(self) -> None:
        self._profiles: dict[str, CredentialProfile] = {}
        self._active_profile: str = ""

    def add_profile(self, profile: CredentialProfile) -> None:
        self._profiles[profile.name] = profile
        if not self._active_profile:
            self._active_profile = profile.name

    def get_profile(self, name: str) -> CredentialProfile | None:
        return self._profiles.get(name)

    def set_active(self, name: str) -> bool:
        if name in self._profiles:
            self._active_profile = name
            return True
        return False

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def list_profiles(self) -> list[str]:
        return list(self._profiles.keys())
