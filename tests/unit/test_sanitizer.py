"""Tests for input sanitization."""

from vaultbot.security.sanitizer import (
    contains_excessive_repetition,
    is_empty_after_sanitization,
    sanitize,
)


def test_strips_zero_width_characters() -> None:
    text = "Hello\u200b\u200cWorld"
    assert sanitize(text) == "HelloWorld"


def test_strips_control_characters() -> None:
    text = "Hello\x00\x01\x02World"
    assert sanitize(text) == "HelloWorld"


def test_strips_directional_overrides() -> None:
    text = "Hello\u202aWorld\u202c"
    assert sanitize(text) == "HelloWorld"


def test_preserves_newlines_and_tabs() -> None:
    text = "Hello\nWorld\tFoo"
    assert sanitize(text) == "Hello\nWorld\tFoo"


def test_truncates_long_messages() -> None:
    text = "a" * 5000
    result = sanitize(text, max_length=100)
    assert len(result) == 100


def test_strips_whitespace() -> None:
    text = "  Hello World  "
    assert sanitize(text) == "Hello World"


def test_normalizes_unicode() -> None:
    # Combining acute accent (NFD) vs precomposed (NFC)
    text = "e\u0301"  # NFD: e + combining acute
    result = sanitize(text)
    assert result == "\u00e9"  # NFC: precomposed e-acute


def test_empty_after_sanitization() -> None:
    assert is_empty_after_sanitization("\u200b\u200c\u200d")
    assert not is_empty_after_sanitization("Hello")


def test_excessive_char_repetition() -> None:
    text = "a" * 100
    assert contains_excessive_repetition(text, threshold=50)


def test_no_excessive_repetition_normal_text() -> None:
    text = "This is a normal message with no excessive repetition."
    assert not contains_excessive_repetition(text)


def test_excessive_word_repetition() -> None:
    text = " ".join(["hello"] * 30)
    assert contains_excessive_repetition(text, threshold=50)
