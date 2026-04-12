"""Unit tests for i18n expansion."""

from __future__ import annotations

from vaultbot.i18n.detection import detect_language, is_rtl
from vaultbot.i18n.locale_manager import LocaleManager


class TestLocaleManager:
    def test_default_locale(self) -> None:
        mgr = LocaleManager()
        assert mgr.default_locale == "en"

    def test_set_and_get_user_locale(self) -> None:
        mgr = LocaleManager()
        mgr.set_user_locale("u1", "ja")
        assert mgr.get_user_locale("u1") == "ja"

    def test_get_user_locale_default(self) -> None:
        mgr = LocaleManager()
        assert mgr.get_user_locale("missing") == "en"

    def test_set_and_get_channel_locale(self) -> None:
        mgr = LocaleManager()
        mgr.set_channel_locale("c1", "fr")
        assert mgr.get_channel_locale("c1") == "fr"

    def test_resolve_user_over_channel(self) -> None:
        mgr = LocaleManager()
        mgr.set_user_locale("u1", "ja")
        mgr.set_channel_locale("c1", "fr")
        assert mgr.resolve_locale("u1", "c1") == "ja"

    def test_resolve_channel_fallback(self) -> None:
        mgr = LocaleManager()
        mgr.set_channel_locale("c1", "fr")
        assert mgr.resolve_locale("unknown", "c1") == "fr"

    def test_resolve_default_fallback(self) -> None:
        mgr = LocaleManager()
        assert mgr.resolve_locale("unknown", "unknown") == "en"

    def test_fallback_chain(self) -> None:
        mgr = LocaleManager()
        chain = mgr.get_fallback_chain("zh-TW")
        assert chain[0] == "zh-TW"
        assert "zh-CN" in chain
        assert "en" in chain

    def test_fallback_chain_default(self) -> None:
        mgr = LocaleManager()
        chain = mgr.get_fallback_chain("de")
        assert chain == ["de", "en"]


class TestLanguageDetection:
    def test_detect_chinese(self) -> None:
        assert detect_language("你好世界") == "zh"

    def test_detect_japanese(self) -> None:
        assert detect_language("こんにちは") == "ja"

    def test_detect_korean(self) -> None:
        assert detect_language("안녕하세요") == "ko"

    def test_detect_arabic(self) -> None:
        assert detect_language("مرحبا") == "ar"

    def test_detect_english_default(self) -> None:
        assert detect_language("Hello world") == "en"

    def test_detect_empty(self) -> None:
        assert detect_language("") == "en"

    def test_is_rtl_arabic(self) -> None:
        assert is_rtl("ar") is True

    def test_is_rtl_english(self) -> None:
        assert is_rtl("en") is False
