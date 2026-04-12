"""Unit tests for proxy capture."""

from __future__ import annotations

from vaultbot.tools.proxy_capture import CapturedRequest, ProxyCaptureStore


class TestProxyCaptureStore:
    def test_record(self) -> None:
        store = ProxyCaptureStore()
        store.record(CapturedRequest(method="GET", url="https://api.example.com", status_code=200))
        assert store.count == 1

    def test_search_by_url(self) -> None:
        store = ProxyCaptureStore()
        store.record(CapturedRequest(method="GET", url="https://api.example.com/users"))
        store.record(CapturedRequest(method="POST", url="https://api.example.com/posts"))
        results = store.search(url_pattern="users")
        assert len(results) == 1

    def test_search_by_method(self) -> None:
        store = ProxyCaptureStore()
        store.record(CapturedRequest(method="GET", url="https://a.com"))
        store.record(CapturedRequest(method="POST", url="https://b.com"))
        results = store.search(method="POST")
        assert len(results) == 1

    def test_get_recent(self) -> None:
        store = ProxyCaptureStore()
        for i in range(10):
            store.record(CapturedRequest(method="GET", url=f"https://a.com/{i}"))
        recent = store.get_recent(limit=3)
        assert len(recent) == 3

    def test_clear(self) -> None:
        store = ProxyCaptureStore()
        store.record(CapturedRequest(method="GET", url="https://a.com"))
        assert store.clear() == 1
        assert store.count == 0

    def test_max_entries(self) -> None:
        store = ProxyCaptureStore(max_entries=2)
        store.record(CapturedRequest(method="GET", url="https://1.com"))
        store.record(CapturedRequest(method="GET", url="https://2.com"))
        store.record(CapturedRequest(method="GET", url="https://3.com"))
        assert store.count == 2

    def test_stats(self) -> None:
        store = ProxyCaptureStore()
        store.record(CapturedRequest(method="GET", url="https://a.com"))
        store.record(CapturedRequest(method="GET", url="https://b.com"))
        store.record(CapturedRequest(method="POST", url="https://c.com"))
        stats = store.stats()
        assert stats["GET"] == 2
        assert stats["POST"] == 1
