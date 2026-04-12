"""Unit tests for video generation providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultbot.media.video_generation import (
    VideoGenerationRequest,
    VideoProvider,
    VideoStatus,
)


def _mock_client(response_data: dict) -> AsyncMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=response_data)
    client = AsyncMock()
    client.post = AsyncMock(return_value=mock_resp)
    client.get = AsyncMock(return_value=mock_resp)
    return client


class TestRunwayProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.runway import RunwayProvider

        assert RunwayProvider(api_key="k").provider_name == "runway"

    def test_is_video_provider(self) -> None:
        from vaultbot.media.providers.runway import RunwayProvider

        assert isinstance(RunwayProvider(api_key="k"), VideoProvider)

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        from vaultbot.media.providers.runway import RunwayProvider

        p = RunwayProvider(api_key="k")
        p._client = _mock_client({"id": "job1"})
        result = await p.generate(VideoGenerationRequest(prompt="test"))
        assert result.job_id == "job1"
        assert result.status == VideoStatus.PENDING

    @pytest.mark.asyncio
    async def test_check_status(self) -> None:
        from vaultbot.media.providers.runway import RunwayProvider

        p = RunwayProvider(api_key="k")
        p._client = _mock_client({"status": "completed", "output_url": "http://v.mp4"})
        result = await p.check_status("job1")
        assert result.status == VideoStatus.COMPLETED
        assert result.video_url == "http://v.mp4"


class TestPikaProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.pika import PikaProvider

        assert PikaProvider(api_key="k").provider_name == "pika"

    def test_is_video_provider(self) -> None:
        from vaultbot.media.providers.pika import PikaProvider

        assert isinstance(PikaProvider(api_key="k"), VideoProvider)

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        from vaultbot.media.providers.pika import PikaProvider

        p = PikaProvider(api_key="k")
        p._client = _mock_client({"id": "job2"})
        result = await p.generate(VideoGenerationRequest(prompt="test"))
        assert result.job_id == "job2"

    @pytest.mark.asyncio
    async def test_check_status(self) -> None:
        from vaultbot.media.providers.pika import PikaProvider

        p = PikaProvider(api_key="k")
        p._client = _mock_client({"status": "failed", "video_url": ""})
        result = await p.check_status("job2")
        assert result.status == VideoStatus.FAILED


class TestKlingProvider:
    def test_provider_name(self) -> None:
        from vaultbot.media.providers.kling import KlingProvider

        assert KlingProvider(api_key="k").provider_name == "kling"

    def test_is_video_provider(self) -> None:
        from vaultbot.media.providers.kling import KlingProvider

        assert isinstance(KlingProvider(api_key="k"), VideoProvider)

    @pytest.mark.asyncio
    async def test_generate(self) -> None:
        from vaultbot.media.providers.kling import KlingProvider

        p = KlingProvider(api_key="k")
        p._client = _mock_client({"task_id": "job3"})
        result = await p.generate(VideoGenerationRequest(prompt="test"))
        assert result.job_id == "job3"

    @pytest.mark.asyncio
    async def test_check_status(self) -> None:
        from vaultbot.media.providers.kling import KlingProvider

        p = KlingProvider(api_key="k")
        p._client = _mock_client({"status": "completed", "video_url": "http://k.mp4"})
        result = await p.check_status("job3")
        assert result.status == VideoStatus.COMPLETED
