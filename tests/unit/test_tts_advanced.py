"""Unit tests for advanced TTS."""

from __future__ import annotations

from vaultbot.media.tts_directives import parse_directives, truncate_for_tts, validate_language


class TestTTSDirectives:
    def test_parse_voice(self) -> None:
        directive, clean = parse_directives("voice:alloy\nHello world")
        assert directive.voice == "alloy"
        assert clean == "Hello world"

    def test_parse_speed(self) -> None:
        directive, clean = parse_directives("speed:1.5 Hello")
        assert directive.speed == 1.5
        assert "speed:" not in clean

    def test_no_directives(self) -> None:
        directive, clean = parse_directives("Just normal text")
        assert directive.voice == ""
        assert clean == "Just normal text"


class TestLanguageValidation:
    def test_supported(self) -> None:
        assert validate_language("en") is True
        assert validate_language("ja") is True
        assert validate_language("zh") is True

    def test_unsupported(self) -> None:
        assert validate_language("xx") is False

    def test_case_insensitive(self) -> None:
        assert validate_language("EN") is True


class TestTruncation:
    def test_short_text(self) -> None:
        assert truncate_for_tts("hello") == "hello"

    def test_long_text(self) -> None:
        result = truncate_for_tts("x" * 10000, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")
