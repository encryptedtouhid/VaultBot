"""Translation system with locale support and fallback.

Loads translation strings from YAML files and provides locale-aware
string lookup with English fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_LOCALES_DIR = Path(__file__).parent / "locales"
_DEFAULT_LOCALE = "en"


class Translator:
    """Locale-aware string translator with fallback.

    Parameters
    ----------
    default_locale:
        Default locale code (e.g. ``en``, ``es``, ``ja``).
    locales_dir:
        Directory containing locale YAML files.
    """

    def __init__(
        self,
        default_locale: str = _DEFAULT_LOCALE,
        locales_dir: Path = _LOCALES_DIR,
    ) -> None:
        self._default_locale = default_locale
        self._locales_dir = locales_dir
        self._strings: dict[str, dict[str, str]] = {}
        self._load_locale(default_locale)

    def _load_locale(self, locale: str) -> None:
        """Load a locale file into memory."""
        if locale in self._strings:
            return

        path = self._locales_dir / f"{locale}.yml"
        if not path.exists():
            path = self._locales_dir / f"{locale}.yaml"

        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            self._strings[locale] = self._flatten(data)
            logger.info("locale_loaded", locale=locale, keys=len(self._strings[locale]))
        else:
            self._strings[locale] = {}
            logger.warning("locale_not_found", locale=locale, path=str(path))

    def t(self, key: str, locale: str | None = None, **kwargs: Any) -> str:
        """Translate a key, with optional variable substitution.

        Parameters
        ----------
        key:
            Dot-separated translation key (e.g. ``errors.rate_limited``).
        locale:
            Locale override.  Falls back to default locale.
        **kwargs:
            Variables to substitute in the translated string.

        Returns
        -------
        str
            Translated string, or the key itself if not found.
        """
        loc = locale or self._default_locale

        # Load locale on demand
        if loc not in self._strings:
            self._load_locale(loc)

        # Try requested locale, then default, then return key
        text = self._strings.get(loc, {}).get(key)
        if text is None and loc != self._default_locale:
            text = self._strings.get(self._default_locale, {}).get(key)
        if text is None:
            return key

        # Substitute variables
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text

        return text

    def set_default_locale(self, locale: str) -> None:
        """Change the default locale."""
        self._default_locale = locale
        self._load_locale(locale)

    def available_locales(self) -> list[str]:
        """List available locale codes based on files in locales dir."""
        locales: list[str] = []
        if self._locales_dir.exists():
            for f in sorted(self._locales_dir.iterdir()):
                if f.suffix in (".yml", ".yaml"):
                    locales.append(f.stem)
        return locales

    @property
    def default_locale(self) -> str:
        return self._default_locale

    @staticmethod
    def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
        """Flatten nested dict into dot-separated keys."""
        result: dict[str, str] = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(Translator._flatten(value, full_key))
            else:
                result[full_key] = str(value)
        return result
