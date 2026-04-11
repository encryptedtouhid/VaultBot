"""Tests for config loading and validation — expanding test coverage."""

from __future__ import annotations

from pathlib import Path

from vaultbot.config import VaultBotConfig


class TestVaultBotConfig:
    def test_default_config(self) -> None:
        config = VaultBotConfig()
        assert config.llm.provider == "claude"
        assert config.max_history == 20
        assert config.log_level == "INFO"

    def test_platform_configs_exist(self) -> None:
        config = VaultBotConfig()
        assert config.telegram.credential_key == "telegram_bot_token"
        assert config.discord.credential_key == "discord_bot_token"
        assert config.irc.credential_key == "irc_server"
        assert config.matrix.credential_key == "matrix_access_token"
        assert config.mattermost.credential_key == "mattermost_token"
        assert config.line.credential_key == "line_channel_token"
        assert config.googlechat.credential_key == "googlechat_service_key"
        assert config.twitch.credential_key == "twitch_oauth_token"
        assert config.nostr.credential_key == "nostr_private_key"

    def test_all_platforms_disabled_by_default(self) -> None:
        config = VaultBotConfig()
        for name in [
            "telegram",
            "discord",
            "whatsapp",
            "signal",
            "slack",
            "teams",
            "imessage",
            "irc",
            "matrix",
            "mattermost",
            "line",
            "googlechat",
            "twitch",
            "nostr",
        ]:
            platform = getattr(config, name)
            assert platform.enabled is False, f"{name} should be disabled by default"

    def test_save_and_load(self, tmp_path: Path) -> None:
        config = VaultBotConfig(max_history=50, log_level="DEBUG")
        config_path = tmp_path / "config.yaml"
        config.save(config_path)

        loaded = VaultBotConfig.load(config_path)
        assert loaded.max_history == 50
        assert loaded.log_level == "DEBUG"

    def test_load_nonexistent_returns_defaults(self, tmp_path: Path) -> None:
        config = VaultBotConfig.load(tmp_path / "nonexistent.yaml")
        assert config.llm.provider == "claude"

    def test_rate_limit_config(self) -> None:
        config = VaultBotConfig()
        assert config.rate_limit.user_capacity == 10.0
        assert config.rate_limit.global_capacity == 50.0

    def test_llm_config(self) -> None:
        config = VaultBotConfig()
        assert config.llm.temperature == 0.7
        assert config.llm.max_tokens == 4096

    def test_allowlist(self) -> None:
        from vaultbot.security.auth import Role

        config = VaultBotConfig(
            allowlist=[
                {"platform": "telegram", "user_id": "123", "role": "admin"},
            ]
        )
        al = config.get_allowlist()
        assert "telegram:123" in al
        assert al["telegram:123"] == Role.ADMIN

    def test_config_file_permissions(self, tmp_path: Path) -> None:
        config = VaultBotConfig()
        config_path = tmp_path / "config.yaml"
        config.save(config_path)
        mode = config_path.stat().st_mode & 0o777
        assert mode == 0o600
