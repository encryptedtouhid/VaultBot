"""Docker / container sandbox configuration auditing.

Validates that container configurations follow security best practices:
no privileged mode, no host network, limited capabilities, restricted
volume mounts, and read-only root filesystem where possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class SandboxSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class SandboxFinding:
    title: str
    severity: SandboxSeverity
    description: str = ""
    remediation: str = ""


_DANGEROUS_CAPABILITIES: frozenset[str] = frozenset({
    "SYS_ADMIN", "SYS_PTRACE", "NET_ADMIN", "NET_RAW",
    "SYS_MODULE", "DAC_OVERRIDE", "SYS_RAWIO", "MKNOD",
})

_SENSITIVE_MOUNTS: frozenset[str] = frozenset({
    "/var/run/docker.sock", "/proc", "/sys", "/dev",
    "/etc/shadow", "/etc/passwd", "/root",
})


@dataclass(slots=True)
class SandboxValidator:
    """Audits container / sandbox configurations for security issues."""

    _audit_count: int = 0

    def validate(self, config: dict[str, object]) -> list[SandboxFinding]:
        """Run all sandbox checks against a config dict."""
        self._audit_count += 1
        findings: list[SandboxFinding] = []
        findings.extend(self._check_privileged(config))
        findings.extend(self._check_network(config))
        findings.extend(self._check_capabilities(config))
        findings.extend(self._check_volumes(config))
        findings.extend(self._check_readonly(config))
        findings.extend(self._check_user(config))
        findings.extend(self._check_pid_mode(config))
        findings.extend(self._check_security_opt(config))
        if findings:
            logger.warning("sandbox_issues_found", count=len(findings))
        return findings

    @property
    def audit_count(self) -> int:
        return self._audit_count

    def is_secure(self, config: dict[str, object]) -> bool:
        """Return True only when no HIGH or CRITICAL findings."""
        findings = self.validate(config)
        return not any(
            f.severity in (
                SandboxSeverity.CRITICAL, SandboxSeverity.HIGH
            )
            for f in findings
        )

    @staticmethod
    def _check_privileged(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        if config.get("privileged"):
            return [SandboxFinding(
                title="Privileged container",
                severity=SandboxSeverity.CRITICAL,
                description="Container runs with full host privileges",
                remediation="Remove --privileged flag",
            )]
        return []

    @staticmethod
    def _check_network(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        if config.get("network_mode") == "host":
            return [SandboxFinding(
                title="Host network mode",
                severity=SandboxSeverity.HIGH,
                description=(
                    "Container shares the host network namespace"
                ),
                remediation="Use bridge or custom network",
            )]
        return []

    @staticmethod
    def _check_capabilities(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        findings: list[SandboxFinding] = []
        cap_add = config.get("cap_add", [])
        if not isinstance(cap_add, list):
            cap_add = []
        for cap in cap_add:
            cap_upper = str(cap).upper()
            if cap_upper in _DANGEROUS_CAPABILITIES:
                findings.append(SandboxFinding(
                    title=f"Dangerous capability: {cap_upper}",
                    severity=SandboxSeverity.HIGH,
                    description=(
                        f"Capability {cap_upper} grants excessive "
                        "host-level access"
                    ),
                    remediation=f"Remove {cap_upper} from cap_add",
                ))
        return findings

    @staticmethod
    def _check_volumes(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        findings: list[SandboxFinding] = []
        volumes = config.get("volumes", [])
        if not isinstance(volumes, list):
            volumes = []
        for vol in volumes:
            vol_str = str(vol)
            host_path = (
                vol_str.split(":")[0] if ":" in vol_str else vol_str
            )
            for sensitive in _SENSITIVE_MOUNTS:
                if host_path == sensitive or host_path.startswith(
                    sensitive + "/"
                ):
                    is_ro = vol_str.endswith(":ro")
                    sev = (
                        SandboxSeverity.MEDIUM
                        if is_ro
                        else SandboxSeverity.HIGH
                    )
                    findings.append(SandboxFinding(
                        title=f"Sensitive mount: {host_path}",
                        severity=sev,
                        description=(
                            f"Mounting {host_path} exposes host data"
                        ),
                        remediation="Remove or mount read-only",
                    ))
        return findings

    @staticmethod
    def _check_readonly(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        if not config.get("read_only", False):
            return [SandboxFinding(
                title="Writable root filesystem",
                severity=SandboxSeverity.LOW,
                description="Root filesystem is not read-only",
                remediation="Set --read-only flag",
            )]
        return []

    @staticmethod
    def _check_user(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        user = str(config.get("user", ""))
        if not user or user == "root" or user == "0":
            return [SandboxFinding(
                title="Running as root",
                severity=SandboxSeverity.MEDIUM,
                description="Container runs as root user",
                remediation="Set --user to a non-root UID",
            )]
        return []

    @staticmethod
    def _check_pid_mode(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        if config.get("pid_mode") == "host":
            return [SandboxFinding(
                title="Host PID namespace",
                severity=SandboxSeverity.HIGH,
                description="Container shares host PID namespace",
                remediation="Remove --pid=host",
            )]
        return []

    @staticmethod
    def _check_security_opt(
        config: dict[str, object],
    ) -> list[SandboxFinding]:
        findings: list[SandboxFinding] = []
        opts = config.get("security_opt", [])
        if not isinstance(opts, list):
            opts = []
        for opt in opts:
            opt_str = str(opt).lower()
            if "apparmor=unconfined" in opt_str:
                findings.append(SandboxFinding(
                    title="AppArmor disabled",
                    severity=SandboxSeverity.HIGH,
                    description="AppArmor profile is unconfined",
                    remediation="Use a restrictive AppArmor profile",
                ))
            if "seccomp=unconfined" in opt_str:
                findings.append(SandboxFinding(
                    title="Seccomp disabled",
                    severity=SandboxSeverity.HIGH,
                    description="Seccomp filtering is disabled",
                    remediation=(
                        "Use default or custom seccomp profile"
                    ),
                ))
        return findings
