"""Unit tests for internationalization."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vaultbot.i18n.translator import Translator


class TestTranslator:
    def test_translate_english(self) -> None:
        t = Translator()
        assert "VaultBot" in t.t("greeting")

    def test_translate_with_variables(self) -> None:
        t = Translator()
        result = t.t("errors.rate_limited", seconds=30)
        assert "30" in result

    def test_translate_missing_key_returns_key(self) -> None:
        t = Translator()
        assert t.t("nonexistent.key") == "nonexistent.key"

    def test_translate_nested_key(self) -> None:
        t = Translator()
        result = t.t("commands.help")
        assert "/help" in result

    def test_translate_spanish(self) -> None:
        t = Translator()
        result = t.t("greeting", locale="es")
        assert "Hola" in result

    def test_fallback_to_default(self) -> None:
        t = Translator()
        # Japanese locale doesn't exist, should fall back to English
        result = t.t("greeting", locale="ja")
        assert "VaultBot" in result

    def test_set_default_locale(self) -> None:
        t = Translator()
        t.set_default_locale("es")
        assert t.default_locale == "es"
        assert "Hola" in t.t("greeting")

    def test_available_locales(self) -> None:
        t = Translator()
        locales = t.available_locales()
        assert "en" in locales
        assert "es" in locales

    def test_custom_locales_dir(self, tmp_path: Path) -> None:
        locale_file = tmp_path / "fr.yml"
        locale_file.write_text("greeting: Bonjour!\n")

        t = Translator(default_locale="fr", locales_dir=tmp_path)
        assert t.t("greeting") == "Bonjour!"

    def test_variable_substitution_error_returns_raw(self) -> None:
        t = Translator()
        # Pass wrong variable name
        result = t.t("errors.rate_limited", wrong_var="test")
        assert "rate limited" in result.lower() or "seconds" in result

    def test_security_strings(self) -> None:
        t = Translator()
        assert "blocked" in t.t("security.blocked_prompt").lower()
        assert t.t("security.approval_required", level="HIGH")

    def test_plugin_strings(self) -> None:
        t = Translator()
        result = t.t("plugins.installed", name="calculator", version="1.0")
        assert "calculator" in result
        assert "1.0" in result

    def test_flatten_nested_dict(self) -> None:
        data = {"a": {"b": {"c": "value"}}}
        result = Translator._flatten(data)
        assert result["a.b.c"] == "value"

    def test_flatten_simple(self) -> None:
        data = {"key": "value"}
        result = Translator._flatten(data)
        assert result["key"] == "value"
