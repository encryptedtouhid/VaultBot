"""Unit tests for music generation providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.music_generation import (
    MusicGenerationRequest,
    MusicProvider,
)


def _mock_client(content: bytes = b"audio_data") -> AsyncMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = content
    client = AsyncMock()
    client.post = AsyncMock(return_value=mock_resp)
    return client


class TestSunoProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.suno import SunoProvider

        assert SunoProvider(api_key="k").provider_name == "suno"

    def test_is_music_provider(self) -> None:
        from vaultbot.media.providers.suno import SunoProvider

        assert isinstance(SunoProvider(api_key="k"), MusicProvider)

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        from vaultbot.media.providers.suno import SunoProvider

        p = SunoProvider(api_key="k")
        p._client = _mock_client(b"suno_audio")
        result = await p.generate(MusicGenerationRequest(prompt="chill lo-fi"))
        assert result.audio_data == b"suno_audio"
        assert result.provider == "suno"


class TestUdioProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.udio import UdioProvider

        assert UdioProvider(api_key="k").provider_name == "udio"

    def test_is_music_provider(self) -> None:
        from vaultbot.media.providers.udio import UdioProvider

        assert isinstance(UdioProvider(api_key="k"), MusicProvider)

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        from vaultbot.media.providers.udio import UdioProvider

        p = UdioProvider(api_key="k")
        p._client = _mock_client(b"udio_audio")
        result = await p.generate(MusicGenerationRequest(prompt="rock anthem"))
        assert result.audio_data == b"udio_audio"
        assert result.provider == "udio"


class TestMubertProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.mubert import MubertProvider

        assert MubertProvider(api_key="k").provider_name == "mubert"

    def test_is_music_provider(self) -> None:
        from vaultbot.media.providers.mubert import MubertProvider

        assert isinstance(MubertProvider(api_key="k"), MusicProvider)

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        from vaultbot.media.providers.mubert import MubertProvider

        p = MubertProvider(api_key="k")
        p._client = _mock_client(b"mubert_audio")
        result = await p.generate(MusicGenerationRequest(prompt="ambient"))
        assert result.audio_data == b"mubert_audio"
        assert result.provider == "mubert"
