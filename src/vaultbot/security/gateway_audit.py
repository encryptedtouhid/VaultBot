"""Gateway exposure audit -- checks TLS and auth configuration.

Verifies that a gateway (HTTP endpoint) is safely exposed: TLS is
enabled, authentication is required, CORS is restrictive, and rate
limiting is active.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class GatewaySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class GatewayFinding:
    title: str
    severity: GatewaySeverity
    description: str = ""
    remediation: str = ""


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    tls_enabled: bool = False
    tls_min_version: str = ""
    auth_enabled: bool = False
    auth_type: str = ""
    cors_origins: list[str] = field(default_factory=list)
    rate_limit_enabled: bool = False
    rate_limit_rps: int = 0
    exposed_host: str = "127.0.0.1"
    exposed_port: int = 8080
    allow_http: bool = False


@dataclass(slots=True)
class GatewayAuditor:
    """Audits gateway configurations for security issues."""

    _audit_count: int = 0

    def audit(self, config: GatewayConfig) -> list[GatewayFinding]:
        """Run all gateway checks."""
        self._audit_count += 1
        findings: list[GatewayFinding] = []
        findings.extend(self._check_tls(config))
        findings.extend(self._check_auth(config))
        findings.extend(self._check_cors(config))
        findings.extend(self._check_rate_limit(config))
        findings.extend(self._check_binding(config))
        if findings:
            logger.warning(
                "gateway_audit_issues", count=len(findings),
            )
        return findings

    def is_secure(self, config: GatewayConfig) -> bool:
        """Return True only when no HIGH or CRITICAL findings."""
        findings = self.audit(config)
        return not any(
            f.severity in (
                GatewaySeverity.CRITICAL, GatewaySeverity.HIGH
            )
            for f in findings
        )

    @property
    def audit_count(self) -> int:
        return self._audit_count

    @staticmethod
    def _check_tls(
        config: GatewayConfig,
    ) -> list[GatewayFinding]:
        findings: list[GatewayFinding] = []
        if not config.tls_enabled:
            findings.append(GatewayFinding(
                title="TLS not enabled",
                severity=GatewaySeverity.CRITICAL,
                description="Gateway accepts unencrypted traffic",
                remediation="Enable TLS with a valid certificate",
            ))
        elif config.tls_min_version in (
            "1.0", "1.1", "TLSv1", "TLSv1.1"
        ):
            findings.append(GatewayFinding(
                title="Weak TLS version",
                severity=GatewaySeverity.HIGH,
                description=(
                    f"TLS minimum version "
                    f"{config.tls_min_version} is deprecated"
                ),
                remediation=(
                    "Set minimum TLS version to 1.2 or 1.3"
                ),
            ))
        return findings

    @staticmethod
    def _check_auth(
        config: GatewayConfig,
    ) -> list[GatewayFinding]:
        findings: list[GatewayFinding] = []
        if not config.auth_enabled:
            findings.append(GatewayFinding(
                title="Authentication not enabled",
                severity=GatewaySeverity.CRITICAL,
                description="Gateway has no authentication",
                remediation="Enable bearer, mTLS, or OAuth2 auth",
            ))
        elif config.auth_type == "basic":
            findings.append(GatewayFinding(
                title="Basic authentication",
                severity=GatewaySeverity.MEDIUM,
                description=(
                    "Basic auth transmits credentials in "
                    "base64 (not encrypted)"
                ),
                remediation="Use bearer tokens or mTLS instead",
            ))
        return findings

    @staticmethod
    def _check_cors(
        config: GatewayConfig,
    ) -> list[GatewayFinding]:
        if "*" in config.cors_origins:
            return [GatewayFinding(
                title="Wildcard CORS origin",
                severity=GatewaySeverity.HIGH,
                description="CORS allows any origin",
                remediation="Restrict to specific allowed origins",
            )]
        return []

    @staticmethod
    def _check_rate_limit(
        config: GatewayConfig,
    ) -> list[GatewayFinding]:
        findings: list[GatewayFinding] = []
        if not config.rate_limit_enabled:
            findings.append(GatewayFinding(
                title="No rate limiting",
                severity=GatewaySeverity.MEDIUM,
                description="Gateway has no rate limiting",
                remediation="Enable rate limiting",
            ))
        elif config.rate_limit_rps > 1000:
            findings.append(GatewayFinding(
                title="Very high rate limit",
                severity=GatewaySeverity.LOW,
                description=(
                    f"Rate limit of {config.rate_limit_rps} "
                    "rps may be too generous"
                ),
                remediation="Consider lowering the rate limit",
            ))
        return findings

    @staticmethod
    def _check_binding(
        config: GatewayConfig,
    ) -> list[GatewayFinding]:
        if config.exposed_host in ("0.0.0.0", "::"):
            return [GatewayFinding(
                title="Bound to all interfaces",
                severity=GatewaySeverity.MEDIUM,
                description=(
                    "Gateway listens on all network interfaces"
                ),
                remediation=(
                    "Bind to 127.0.0.1 or a specific interface"
                ),
            )]
        return []
