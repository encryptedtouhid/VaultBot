"""Unit tests for deep CLI commands."""

from __future__ import annotations

from vaultbot.cli_commands.backup_cmds import BackupCommands
from vaultbot.cli_commands.cron_cmds import CronCommands
from vaultbot.cli_commands.doctor import CheckStatus, DoctorCommands
from vaultbot.cli_commands.gateway_cmds import GatewayCommands
from vaultbot.cli_commands.secret_cmds import SecretCommands


class TestGatewayCommands:
    def test_connect_disconnect(self) -> None:
        cmds = GatewayCommands()
        assert cmds.connect("ws://localhost:8765") is True
        assert cmds.is_connected is True
        assert cmds.disconnect() is True
        assert cmds.is_connected is False

    def test_status(self) -> None:
        cmds = GatewayCommands()
        cmds.connect("ws://localhost:8765")
        status = cmds.status()
        assert status.connected is True


class TestDoctorCommands:
    def test_check_python(self) -> None:
        doctor = DoctorCommands()
        check = doctor.check_python()
        assert check.status == CheckStatus.OK

    def test_run_all(self) -> None:
        doctor = DoctorCommands()
        checks = doctor.run_all()
        assert len(checks) >= 3

    def test_format_report(self) -> None:
        doctor = DoctorCommands()
        checks = doctor.run_all()
        report = doctor.format_report(checks)
        assert "Health Report" in report


class TestCronCommands:
    def test_create_and_list(self) -> None:
        cmds = CronCommands()
        cmds.create("daily", "0 0 * * *", "send_report")
        assert len(cmds.list_jobs()) == 1

    def test_delete(self) -> None:
        cmds = CronCommands()
        job = cmds.create("test", "*/5 * * * *", "noop")
        assert cmds.delete(job.job_id) is True
        assert len(cmds.list_jobs()) == 0


class TestSecretCommands:
    def test_set_and_get(self) -> None:
        cmds = SecretCommands()
        cmds.set_secret("api_key", "env")
        info = cmds.get_secret("api_key")
        assert info is not None
        assert info.masked_value == "****"

    def test_list_and_delete(self) -> None:
        cmds = SecretCommands()
        cmds.set_secret("key1")
        cmds.set_secret("key2")
        assert len(cmds.list_secrets()) == 2
        assert cmds.delete_secret("key1") is True

    def test_rotate(self) -> None:
        cmds = SecretCommands()
        cmds.set_secret("key")
        assert cmds.rotate("key") is True
        assert cmds.rotate("nope") is False


class TestBackupCommands:
    def test_create_and_list(self) -> None:
        cmds = BackupCommands()
        cmds.create("daily_backup")
        assert len(cmds.list_backups()) == 1

    def test_restore(self) -> None:
        cmds = BackupCommands()
        bak = cmds.create("test")
        assert cmds.restore(bak.backup_id) is True
        assert cmds.restore("nope") is False

    def test_delete(self) -> None:
        cmds = BackupCommands()
        bak = cmds.create("test")
        assert cmds.delete(bak.backup_id) is True
