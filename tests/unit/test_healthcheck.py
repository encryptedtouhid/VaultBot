"""Tests for healthcheck status tracking."""

from zenbot.core.healthcheck import HealthStatus


def test_healthy_when_platform_connected() -> None:
    status = HealthStatus()
    status.platforms_connected["telegram"] = True
    assert status.is_healthy is True


def test_unhealthy_when_no_platforms() -> None:
    status = HealthStatus()
    assert status.is_healthy is False


def test_unhealthy_when_all_disconnected() -> None:
    status = HealthStatus()
    status.platforms_connected["telegram"] = False
    assert status.is_healthy is False


def test_ready_requires_healthy_and_llm() -> None:
    status = HealthStatus()
    status.platforms_connected["telegram"] = True
    status.llm_available = True
    assert status.is_ready is True


def test_not_ready_without_llm() -> None:
    status = HealthStatus()
    status.platforms_connected["telegram"] = True
    status.llm_available = False
    assert status.is_ready is False


def test_not_ready_without_platform() -> None:
    status = HealthStatus()
    status.llm_available = True
    assert status.is_ready is False


def test_uptime() -> None:
    status = HealthStatus()
    assert status.uptime_seconds >= 0


def test_to_dict() -> None:
    status = HealthStatus()
    status.platforms_connected["telegram"] = True
    status.llm_available = True
    d = status.to_dict()
    assert d["healthy"] is True
    assert d["ready"] is True
    assert "uptime_seconds" in d
    assert d["platforms"] == {"telegram": True}
