"""Unit tests for link understanding."""

from __future__ import annotations

from vaultbot.tools.link_understanding import extract_links, is_safe_url


class TestIsSafeUrl:
    def test_safe(self) -> None:
        safe, _ = is_safe_url("https://example.com")
        assert safe is True

    def test_blocked_localhost(self) -> None:
        safe, reason = is_safe_url("http://localhost/secret")
        assert safe is False

    def test_blocked_private(self) -> None:
        safe, _ = is_safe_url("http://192.168.1.1")
        assert safe is False

    def test_blocked_scheme(self) -> None:
        safe, _ = is_safe_url("ftp://example.com")
        assert safe is False


class TestExtractLinks:
    def test_extract_from_text(self) -> None:
        text = "Check https://example.com and https://other.com"
        links = extract_links(text)
        assert len(links) == 2

    def test_dedup(self) -> None:
        text = "https://example.com https://example.com"
        links = extract_links(text)
        assert len(links) == 1

    def test_no_dedup(self) -> None:
        text = "https://example.com https://example.com"
        links = extract_links(text, deduplicate=False)
        assert len(links) == 2

    def test_max_links(self) -> None:
        text = " ".join(f"https://example.com/{i}" for i in range(50))
        links = extract_links(text, max_links=5)
        assert len(links) == 5

    def test_marks_unsafe(self) -> None:
        text = "Visit http://localhost/admin"
        links = extract_links(text)
        assert len(links) == 1
        assert links[0].safe is False

    def test_no_links(self) -> None:
        assert extract_links("no links here") == []

    def test_strips_trailing_punctuation(self) -> None:
        text = "See https://example.com."
        links = extract_links(text)
        assert links[0].url == "https://example.com"
