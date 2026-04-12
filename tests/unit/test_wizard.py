"""Unit tests for setup wizard."""

from __future__ import annotations

from vaultbot.wizard.setup import SetupStep, SetupWizard


class TestSetupWizard:
    def test_initial_step(self) -> None:
        wiz = SetupWizard()
        assert wiz.current_step == SetupStep.WELCOME

    def test_select_channels(self) -> None:
        wiz = SetupWizard()
        wiz.select_channels(["telegram", "discord"])
        assert wiz.state.selected_channels == ["telegram", "discord"]
        assert wiz.current_step == SetupStep.PROVIDER_SELECT

    def test_select_provider(self) -> None:
        wiz = SetupWizard()
        wiz.select_channels(["telegram"])
        wiz.select_provider("claude")
        assert wiz.state.selected_provider == "claude"
        assert wiz.current_step == SetupStep.MODEL_SELECT

    def test_full_flow(self) -> None:
        wiz = SetupWizard()
        wiz.select_channels(["telegram"])
        wiz.select_provider("claude")
        wiz.select_model("claude-sonnet-4")
        wiz.install_plugins(["weather"])
        checks = wiz.run_health_check()
        assert checks["config_valid"] is True
        assert wiz.state.health_passed is True
        state = wiz.complete()
        assert state.completed is True

    def test_available_channels(self) -> None:
        wiz = SetupWizard()
        channels = wiz.get_available_channels()
        assert "telegram" in channels
        assert "discord" in channels

    def test_available_providers(self) -> None:
        wiz = SetupWizard()
        assert "claude" in wiz.get_available_providers()

    def test_health_check_fails(self) -> None:
        wiz = SetupWizard()
        checks = wiz.run_health_check()
        assert checks["config_valid"] is False
        assert wiz.state.health_passed is False

    def test_reset(self) -> None:
        wiz = SetupWizard()
        wiz.select_channels(["telegram"])
        wiz.reset()
        assert wiz.current_step == SetupStep.WELCOME
        assert wiz.state.selected_channels == []
