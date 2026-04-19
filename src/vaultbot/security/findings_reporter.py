"""Structured security findings reporter with severity and CVE refs.

Collects findings from multiple scanners and produces a unified report
in a structured format suitable for humans and machines.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


@dataclass(frozen=True, slots=True)
class SecurityFindingRecord:
    finding_id: str
    title: str
    severity: FindingSeverity
    description: str = ""
    source: str = ""
    cve_ids: tuple[str, ...] = ()
    remediation: str = ""
    file_path: str = ""
    line_number: int = 0
    status: FindingStatus = FindingStatus.OPEN
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class SecurityReport:
    report_id: str
    generated_at: float
    findings: tuple[SecurityFindingRecord, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.severity == FindingSeverity.CRITICAL
        )

    @property
    def high_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.severity == FindingSeverity.HIGH
        )

    @property
    def passed(self) -> bool:
        """True if no critical or high findings are open."""
        return not any(
            f.severity in (
                FindingSeverity.CRITICAL, FindingSeverity.HIGH
            )
            and f.status == FindingStatus.OPEN
            for f in self.findings
        )

    def by_severity(
        self, severity: FindingSeverity,
    ) -> list[SecurityFindingRecord]:
        return [f for f in self.findings if f.severity == severity]


@dataclass(slots=True)
class FindingsReporter:
    """Collects and reports security findings."""

    _findings: list[SecurityFindingRecord] = field(
        default_factory=list,
    )
    _next_id: int = 1
    _source: str = "vaultbot"

    def add(
        self,
        title: str,
        severity: FindingSeverity,
        description: str = "",
        cve_ids: list[str] | None = None,
        remediation: str = "",
        file_path: str = "",
        line_number: int = 0,
    ) -> SecurityFindingRecord:
        """Add a finding and return the record."""
        finding = SecurityFindingRecord(
            finding_id=f"{self._source}-{self._next_id:04d}",
            title=title,
            severity=severity,
            description=description,
            source=self._source,
            cve_ids=tuple(cve_ids or []),
            remediation=remediation,
            file_path=file_path,
            line_number=line_number,
        )
        self._findings.append(finding)
        self._next_id += 1
        logger.info(
            "finding_recorded",
            finding_id=finding.finding_id,
            severity=severity.value,
            title=title,
        )
        return finding

    def generate_report(
        self,
        report_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SecurityReport:
        """Generate a structured report."""
        rid = report_id or f"report-{int(time.time())}"
        report = SecurityReport(
            report_id=rid,
            generated_at=time.time(),
            findings=tuple(self._findings),
            metadata=metadata or {},
        )
        logger.info(
            "report_generated",
            report_id=rid,
            total=report.total,
            critical=report.critical_count,
        )
        return report

    def summary(self) -> dict[str, int]:
        """Return counts by severity."""
        counts: dict[str, int] = {}
        for f in self._findings:
            key = f.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def clear(self) -> None:
        """Discard all collected findings."""
        self._findings.clear()
        self._next_id = 1

    @property
    def finding_count(self) -> int:
        return len(self._findings)

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Serialise findings to a list of dicts."""
        return [
            {
                "id": f.finding_id,
                "title": f.title,
                "severity": f.severity.value,
                "description": f.description,
                "source": f.source,
                "cve_ids": list(f.cve_ids),
                "remediation": f.remediation,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "status": f.status.value,
                "timestamp": f.timestamp,
            }
            for f in self._findings
        ]
