"""Unit tests for media handling."""

from __future__ import annotations

import tempfile

from vaultbot.media.mime import is_audio, is_image, is_video, mime_from_bytes, mime_from_extension
from vaultbot.media.store import MediaStore, is_url_safe


class TestMime:
    def test_from_extension(self) -> None:
        assert mime_from_extension("photo.jpg") == "image/jpeg"
        assert mime_from_extension("song.mp3") == "audio/mpeg"
        assert mime_from_extension("noext") == "application/octet-stream"

    def test_from_bytes_png(self) -> None:
        assert mime_from_bytes(b"\x89PNG\r\n\x1a\n") == "image/png"

    def test_from_bytes_jpeg(self) -> None:
        assert mime_from_bytes(b"\xff\xd8\xff\xe0") == "image/jpeg"

    def test_from_bytes_unknown(self) -> None:
        assert mime_from_bytes(b"\x00\x00\x00") == "application/octet-stream"

    def test_type_checks(self) -> None:
        assert is_image("image/png") is True
        assert is_audio("audio/mp3") is True
        assert is_video("video/mp4") is True
        assert is_image("text/plain") is False


class TestUrlSafety:
    def test_safe_https(self) -> None:
        assert is_url_safe("https://example.com/image.jpg") is True

    def test_blocked_localhost(self) -> None:
        assert is_url_safe("http://localhost/secret") is False

    def test_blocked_metadata(self) -> None:
        assert is_url_safe("http://169.254.169.254/latest/") is False

    def test_blocked_private(self) -> None:
        assert is_url_safe("http://192.168.1.1/admin") is False

    def test_blocked_scheme(self) -> None:
        assert is_url_safe("file:///etc/passwd") is False


class TestMediaStore:
    def test_store_and_retrieve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MediaStore(workspace=tmp)
            stored = store.store(b"image data", "photo.jpg", "image/jpeg")
            assert stored.size_bytes == 10
            data = store.retrieve(stored.file_id)
            assert data == b"image data"

    def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MediaStore(workspace=tmp)
            stored = store.store(b"data", "file.txt")
            assert store.delete(stored.file_id) is True
            assert store.file_count == 0

    def test_list_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MediaStore(workspace=tmp)
            store.store(b"a", "a.txt")
            store.store(b"b", "b.txt")
            assert len(store.list_files()) == 2

    def test_retrieve_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MediaStore(workspace=tmp)
            assert store.retrieve("nope") is None
