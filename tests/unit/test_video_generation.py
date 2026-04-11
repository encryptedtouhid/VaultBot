"""Unit tests for video generation engine."""

from __future__ import annotations

import pytest

from vaultbot.media.video_generation import (
    VideoAspectRatio,
    VideoGenerationEngine,
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoProvider,
    VideoStatus,
)


class MockVideoProvider:
    def __init__(self, name: str = "mock_video") -> None:
        self._name = name
        self._jobs: dict[str, VideoGenerationResult] = {}

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        result = VideoGenerationResult(
            job_id=f"job_{self._name}_1",
            status=VideoStatus.COMPLETED,
            video_url=f"https://{self._name}.com/video.mp4",
            provider=self._name,
            duration_seconds=request.duration_seconds,
        )
        self._jobs[result.job_id] = result
        return result

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        return self._jobs.get(
            job_id,
            VideoGenerationResult(job_id=job_id, status=VideoStatus.PENDING, provider=self._name),
        )


class TestVideoBaseTypes:
    def test_video_status_enum(self) -> None:
        assert VideoStatus.COMPLETED.value == "completed"

    def test_aspect_ratio_enum(self) -> None:
        assert VideoAspectRatio.LANDSCAPE.value == "16:9"
        assert VideoAspectRatio.PORTRAIT.value == "9:16"

    def test_request_defaults(self) -> None:
        req = VideoGenerationRequest(prompt="a cat")
        assert req.aspect_ratio == VideoAspectRatio.LANDSCAPE
        assert req.duration_seconds == 5
        assert req.image_url == ""

    def test_result_dataclass(self) -> None:
        r = VideoGenerationResult(job_id="j1", status=VideoStatus.PENDING, provider="test")
        assert r.video_url == ""

    def test_mock_is_video_provider(self) -> None:
        assert isinstance(MockVideoProvider(), VideoProvider)


class TestVideoGenerationEngine:
    def test_register_and_list(self) -> None:
        engine = VideoGenerationEngine()
        engine.register_provider(MockVideoProvider("runway"))
        assert "runway" in engine.list_providers()

    @pytest.mark.asyncio
    async def test_generate_success(self) -> None:
        engine = VideoGenerationEngine()
        engine.register_provider(MockVideoProvider("runway"))
        result = await engine.generate("a sunset timelapse")
        assert result.status == VideoStatus.COMPLETED
        assert "runway" in result.video_url
        assert engine.generation_count == 1

    @pytest.mark.asyncio
    async def test_generate_with_options(self) -> None:
        engine = VideoGenerationEngine()
        engine.register_provider(MockVideoProvider("test"))
        result = await engine.generate(
            "a dog", aspect_ratio=VideoAspectRatio.PORTRAIT, duration_seconds=10
        )
        assert result.duration_seconds == 10

    @pytest.mark.asyncio
    async def test_generate_unknown_raises(self) -> None:
        engine = VideoGenerationEngine()
        with pytest.raises(ValueError, match="Unknown video provider"):
            await engine.generate("test")

    @pytest.mark.asyncio
    async def test_check_status(self) -> None:
        engine = VideoGenerationEngine()
        provider = MockVideoProvider("test")
        engine.register_provider(provider)
        gen = await engine.generate("test")
        status = await engine.check_status(gen.job_id)
        assert status.status == VideoStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_check_status_unknown_job(self) -> None:
        engine = VideoGenerationEngine()
        engine.register_provider(MockVideoProvider("test"))
        status = await engine.check_status("nonexistent_job")
        assert status.status == VideoStatus.PENDING

    @pytest.mark.asyncio
    async def test_multi_provider(self) -> None:
        engine = VideoGenerationEngine()
        engine.register_provider(MockVideoProvider("a"))
        engine.register_provider(MockVideoProvider("b"))
        r1 = await engine.generate("test", provider="a")
        r2 = await engine.generate("test", provider="b")
        assert r1.provider == "a"
        assert r2.provider == "b"
        assert engine.generation_count == 2
