"""Authentication credential profiles for agents."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum


class AuthType(str, Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"
    NONE = "none"


class ProfileState(str, Enum):
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    FAILED = "failed"


@dataclass(slots=True)
class AuthProfile:
    name: str
    auth_type: AuthType = AuthType.API_KEY
    credential: str = ""
    state: ProfileState = ProfileState.ACTIVE
    last_used: float = 0.0
    failure_count: int = 0
    cooldown_until: float = 0.0


class AuthProfileManager:
    """Manages authentication profiles for agents."""

    def __init__(self) -> None:
        self._profiles: dict[str, AuthProfile] = {}

    def add(self, profile: AuthProfile) -> None:
        self._profiles[profile.name] = profile

    def get(self, name: str) -> AuthProfile | None:
        profile = self._profiles.get(name)
        if profile and profile.state == ProfileState.COOLDOWN:
            if time.time() >= profile.cooldown_until:
                profile.state = ProfileState.ACTIVE
        return profile

    def use(self, name: str) -> bool:
        profile = self._profiles.get(name)
        if not profile or profile.state != ProfileState.ACTIVE:
            return False
        profile.last_used = time.time()
        return True

    def mark_failed(self, name: str, cooldown_seconds: float = 300.0) -> None:
        profile = self._profiles.get(name)
        if profile:
            profile.failure_count += 1
            profile.state = ProfileState.COOLDOWN
            profile.cooldown_until = time.time() + cooldown_seconds

    def get_best(self) -> AuthProfile | None:
        """Get the best available profile (most recently used active one)."""
        active = [p for p in self._profiles.values() if p.state == ProfileState.ACTIVE]
        if not active:
            return None
        return max(active, key=lambda p: p.last_used)

    def list_profiles(self) -> list[AuthProfile]:
        return list(self._profiles.values())

    def remove(self, name: str) -> bool:
        if name in self._profiles:
            del self._profiles[name]
            return True
        return False
