"""Startup initialization sequence with TLS and CA cert setup."""

from __future__ import annotations

import os
import ssl
import sys
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class StartupResult:
    tls_configured: bool = False
    ca_certs_found: bool = False
    python_version: str = ""
    platform: str = ""
    errors: list[str] = field(default_factory=list)


def setup_tls_environment() -> bool:
    """Configure TLS environment for HTTPS clients."""
    try:
        ctx = ssl.create_default_context()
        return ctx.check_hostname
    except Exception:
        return False


def find_ca_certs() -> str:
    """Find CA certificates path for the current platform."""
    paths = [
        "/etc/ssl/certs/ca-certificates.crt",  # Debian/Ubuntu
        "/etc/pki/tls/certs/ca-bundle.crt",  # RHEL/CentOS
        "/usr/local/etc/openssl/cert.pem",  # macOS Homebrew
        "/etc/ssl/cert.pem",  # macOS
    ]
    env_path = os.environ.get("SSL_CERT_FILE", "")
    if env_path and os.path.exists(env_path):
        return env_path
    for path in paths:
        if os.path.exists(path):
            return path
    return ""


def run_startup() -> StartupResult:
    """Run full startup initialization."""
    errors: list[str] = []
    tls_ok = setup_tls_environment()
    if not tls_ok:
        errors.append("TLS configuration failed")

    ca_path = find_ca_certs()
    return StartupResult(
        tls_configured=tls_ok,
        ca_certs_found=bool(ca_path),
        python_version=sys.version.split()[0],
        platform=sys.platform,
        errors=errors,
    )
