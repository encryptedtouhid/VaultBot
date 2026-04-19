"""Per-channel security configuration review.

Audits individual channel configurations for security issues such as
missing encryption, disabled authentication, overly permissive access
controls, and missing rate limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class ChannelSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class ChannelFinding:
    title: str
    severity: ChannelSeverity
    channel_id: str = ""
    description: str = ""
    remediation: str = ""


@dataclass(frozen=True, slots=True)
class ChannelConfig:
    channel_id: str
    platform: str = ""
    encryption_enabled: bool = False
    auth_required: bool = False
    allowed_roles: list[str] = field(default_factory=list)
    rate_limit_enabled: bool = False
    rate_limit_rpm: int = 0
    logging_enabled: bool = True
    webhook_secret_set: bool = False
    max_message_length: int = 0


@dataclass(slots=True)
class ChannelAuditor:
    """Reviews channel configurations for security issues."""

    _audit_count: int = 0

    def audit(
        self, config: ChannelConfig,
    ) -> list[ChannelFinding]:
        """Audit a single channel configuration."""
        self._audit_count += 1
        findings: list[ChannelFinding] = []
        findings.extend(self._check_encryption(config))
        findings.extend(self._check_auth(config))
        findings.extend(self._check_access_control(config))
        findings.extend(self._check_rate_limit(config))
        findings.extend(self._check_logging(config))
        findings.extend(self._check_webhook(config))
        findings.extend(self._check_message_limit(config))
        if findings:
            logger.warning(
                "channel_audit_issues",
                channel=config.channel_id,
                count=len(findings),
            )
        return findings

    def audit_all(
        self, configs: list[ChannelConfig],
    ) -> dict[str, list[ChannelFinding]]:
        """Audit multiple channels, keyed by channel_id."""
        result: dict[str, list[ChannelFinding]] = {}
        for cfg in configs:
            findings = self.audit(cfg)
            if findings:
                result[cfg.channel_id] = findings
        return result

    def is_secure(self, config: ChannelConfig) -> bool:
        """True if no HIGH or CRITICAL findings."""
        findings = self.audit(config)
        return not any(
            f.severity in (
                ChannelSeverity.CRITICAL, ChannelSeverity.HIGH
            )
            for f in findings
        )

    @property
    def audit_count(self) -> int:
        return self._audit_count

    @staticmethod
    def _check_encryption(
        config: ChannelConfig,
    ) -> list[ChannelFinding]:
        if not config.encryption_enabled:
            return [ChannelFinding(
                title="Encryption disabled",
                severity=ChannelSeverity.HIGH,
                channel_id=config.channel_id,
                description="Channel traffic is not encrypted",
                remediation=(
                    "Enable TLS/encryption for the channel"
                ),
            )]
        return []

    @staticmethod
    def _check_auth(
        config: ChannelConfig,
    ) -> list[ChannelFinding]:
        if not config.auth_required:
            return [ChannelFinding(
                title="Authentication not required",
                severity=ChannelSeverity.CRITICAL,
                channel_id=config.channel_id,
                description=(
                    "Channel does not require authentication"
                ),
                remediation=(
                    "Enable authentication for the channel"
                ),
            )]
        return []

    @staticmethod
    def _check_access_control(
        config: ChannelConfig,
    ) -> list[ChannelFinding]:
        if not config.allowed_roles:
            return [ChannelFinding(
                title="No role restrictions",
                severity=ChannelSeverity.MEDIUM,
                channel_id=config.channel_id,
                description=(
                    "Channel has no role-based access control"
                ),
                remediation="Configure allowed roles",
            )]
        if "*" in config.allowed_roles or "any" in config.allowed_roles:
            return [ChannelFinding(
                title="Wildcard role access",
                severity=ChannelSeverity.HIGH,
                channel_id=config.channel_id,
                description="Channel allows any role",
                remediation="Restrict to specific roles",
            )]
        return []

    @staticmethod
    def _check_rate_limit(
        config: ChannelConfig,
    ) -> list[ChannelFinding]:
        if not config.rate_limit_enabled:
            return [ChannelFinding(
                title="No rate limiting",
                severity=ChannelSeverity.MEDIUM,
                channel_id=config.channel_id,
                description="Channel has no rate limiting",
                remediation="Enable rate limiting",
            )]
        if config.rate_limit_rpm > 600:
            return [ChannelFinding(
                title="High rate limit",
                severity=ChannelSeverity.LOW,
                channel_id=config.channel_id,
                description=(
                    f"Rate limit of {config.rate_limit_rpm} "
                    "RPM may be too generous"
                ),
                remediation="Consider lowering the rate limit",
            )]
        return []

    @staticmethod
    def _check_logging(
        config: ChannelConfig,
    ) -> list[ChannelFinding]:
        if not config.logging_enabled:
            return [ChannelFinding(
                title="Logging disabled",
                severity=ChannelSeverity.MEDIUM,
                channel_id=config.channel_id,
                description="Channel has logging disabled",
                remediation="Enable logging for audit trail",
            )]
        return []

    @staticmethod
    def _check_webhook(
        config: ChannelConfig,
    ) -> list[ChannelFinding]:
        if config.platform and not config.webhook_secret_set:
            return [ChannelFinding(
                title="Webhook secret not set",
                severity=ChannelSeverity.HIGH,
                channel_id=config.channel_id,
                description=(
                    "Webhook has no secret for request verification"
                ),
                remediation="Set a webhook secret",
            )]
        return []

    @staticmethod
    def _check_message_limit(
        config: ChannelConfig,
    ) -> list[ChannelFinding]:
        if config.max_message_length <= 0:
            return [ChannelFinding(
                title="No message length limit",
                severity=ChannelSeverity.LOW,
                channel_id=config.channel_id,
                description=(
                    "No maximum message length configured"
                ),
                remediation="Set a max message length",
            )]
        return []
