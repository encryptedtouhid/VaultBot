"""Unit tests for daemon service management."""

from __future__ import annotations

from vaultbot.daemon.service import (
    ServiceConfig,
    ServiceManager,
    ServicePlatform,
    ServiceState,
    detect_platform,
)


class TestDetectPlatform:
    def test_detects_something(self) -> None:
        platform = detect_platform()
        assert platform in ServicePlatform


class TestServiceManager:
    def test_initial_state(self) -> None:
        mgr = ServiceManager()
        assert mgr.state == ServiceState.NOT_INSTALLED

    def test_install(self) -> None:
        mgr = ServiceManager()
        assert mgr.install() is True
        assert mgr.state == ServiceState.INSTALLED

    def test_start(self) -> None:
        mgr = ServiceManager()
        mgr.install()
        assert mgr.start() is True
        assert mgr.state == ServiceState.RUNNING

    def test_stop(self) -> None:
        mgr = ServiceManager()
        mgr.install()
        mgr.start()
        assert mgr.stop() is True
        assert mgr.state == ServiceState.STOPPED

    def test_restart(self) -> None:
        mgr = ServiceManager()
        mgr.install()
        mgr.start()
        assert mgr.restart() is True
        assert mgr.state == ServiceState.RUNNING

    def test_uninstall(self) -> None:
        mgr = ServiceManager()
        mgr.install()
        assert mgr.uninstall() is True
        assert mgr.state == ServiceState.NOT_INSTALLED

    def test_uninstall_not_installed(self) -> None:
        mgr = ServiceManager()
        assert mgr.uninstall() is False

    def test_generate_launchd(self) -> None:
        mgr = ServiceManager(ServiceConfig(name="test"))
        plist = mgr.generate_launchd_plist()
        assert "com.vaultbot.test" in plist

    def test_generate_systemd(self) -> None:
        mgr = ServiceManager(ServiceConfig(description="Test Service"))
        unit = mgr.generate_systemd_unit()
        assert "Test Service" in unit
        assert "[Service]" in unit
