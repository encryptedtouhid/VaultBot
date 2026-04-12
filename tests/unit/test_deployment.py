"""Unit tests for deployment helpers."""

from __future__ import annotations

from vaultbot.deploy.fly_io import FlyConfig, FlyDeployer
from vaultbot.deploy.nix import NixDeployer
from vaultbot.deploy.podman import PodmanConfig, PodmanDeployer


class TestPodmanDeployer:
    def test_generate_run_command(self) -> None:
        d = PodmanDeployer()
        cmd = d.generate_run_command()
        assert "podman run" in cmd
        assert "--name=vaultbot" in cmd

    def test_generate_compose(self) -> None:
        d = PodmanDeployer()
        compose = d.generate_compose()
        assert "services" in compose
        assert "vaultbot" in compose["services"]

    def test_custom_config(self) -> None:
        config = PodmanConfig(image="custom:v1", container_name="mybot")
        d = PodmanDeployer(config)
        cmd = d.generate_run_command()
        assert "custom:v1" in cmd
        assert "--name=mybot" in cmd


class TestFlyDeployer:
    def test_generate_fly_toml(self) -> None:
        d = FlyDeployer()
        toml = d.generate_fly_toml()
        assert 'app = "vaultbot"' in toml
        assert "internal_port = 8080" in toml

    def test_with_env_vars(self) -> None:
        config = FlyConfig(env_vars={"LOG_LEVEL": "DEBUG"})
        d = FlyDeployer(config)
        toml = d.generate_fly_toml()
        assert "LOG_LEVEL" in toml

    def test_deploy_command(self) -> None:
        d = FlyDeployer()
        cmd = d.generate_deploy_command()
        assert "fly deploy" in cmd


class TestNixDeployer:
    def test_generate_flake(self) -> None:
        d = NixDeployer()
        flake = d.generate_flake_nix()
        assert "vaultbot" in flake
        assert "python311" in flake

    def test_generate_shell(self) -> None:
        d = NixDeployer()
        shell = d.generate_shell_nix()
        assert "mkShell" in shell
