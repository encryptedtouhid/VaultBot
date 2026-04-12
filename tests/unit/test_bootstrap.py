"""Unit tests for bootstrap."""

from __future__ import annotations

from vaultbot.bootstrap.startup import find_ca_certs, run_startup, setup_tls_environment


class TestBootstrap:
    def test_setup_tls(self) -> None:
        assert setup_tls_environment() is True

    def test_find_ca_certs(self) -> None:
        # May or may not find certs depending on platform
        result = find_ca_certs()
        assert isinstance(result, str)

    def test_run_startup(self) -> None:
        result = run_startup()
        assert result.python_version != ""
        assert result.platform != ""
        assert result.tls_configured is True
