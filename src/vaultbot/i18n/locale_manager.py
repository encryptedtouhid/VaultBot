"""Locale management with per-user preferences and fallback chains."""

from __future__ import annotations

from dataclasses import dataclass

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class LocalePreference:
    """User locale preference."""

    user_id: str
    locale: str
    platform: str = ""


class LocaleManager:
    """Manages per-user and per-channel locale preferences."""

    def __init__(self, default_locale: str = "en") -> None:
        self._default = default_locale
        self._user_prefs: dict[str, str] = {}
        self._channel_prefs: dict[str, str] = {}
        self._fallback_chains: dict[str, list[str]] = {
            "zh-TW": ["zh-CN", "en"],
            "pt-BR": ["pt", "en"],
            "en-GB": ["en"],
        }

    @property
    def default_locale(self) -> str:
        return self._default

    def set_user_locale(self, user_id: str, locale: str) -> None:
        self._user_prefs[user_id] = locale
        logger.info("user_locale_set", user_id=user_id, locale=locale)

    def get_user_locale(self, user_id: str) -> str:
        return self._user_prefs.get(user_id, self._default)

    def set_channel_locale(self, channel_id: str, locale: str) -> None:
        self._channel_prefs[channel_id] = locale

    def get_channel_locale(self, channel_id: str) -> str:
        return self._channel_prefs.get(channel_id, self._default)

    def resolve_locale(self, user_id: str, channel_id: str = "") -> str:
        """Resolve locale: user > channel > default."""
        if user_id in self._user_prefs:
            return self._user_prefs[user_id]
        if channel_id and channel_id in self._channel_prefs:
            return self._channel_prefs[channel_id]
        return self._default

    def get_fallback_chain(self, locale: str) -> list[str]:
        """Get fallback chain for a locale."""
        chain = [locale]
        chain.extend(self._fallback_chains.get(locale, []))
        if self._default not in chain:
            chain.append(self._default)
        return chain
