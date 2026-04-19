"""Detect leaked credentials in logs, output, and text.

Scans arbitrary text for patterns that look like API keys, tokens,
private keys, and other sensitive material. Each match is reported
with its type and redacted value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CredentialMatch:
    credential_type: str
    matched_value: str
    line_number: int = 0
    confidence: float = 0.9


@dataclass(frozen=True, slots=True)
class ScanResult:
    text_length: int
    matches: tuple[CredentialMatch, ...] = ()

    @property
    def has_leaks(self) -> bool:
        return len(self.matches) > 0

    @property
    def leak_count(self) -> int:
        return len(self.matches)

    @property
    def high_confidence_leaks(self) -> list[CredentialMatch]:
        return [m for m in self.matches if m.confidence >= 0.8]


_CREDENTIAL_PATTERNS: list[tuple[str, str, float]] = [
    (
        r"(?:sk|pk)[-_](?:live|test)[-_][A-Za-z0-9]{20,}",
        "stripe_key",
        0.95,
    ),
    (r"AIza[0-9A-Za-z_-]{35}", "google_api_key", 0.95),
    (r"ghp_[A-Za-z0-9]{36}", "github_pat", 0.95),
    (r"gho_[A-Za-z0-9]{36}", "github_oauth", 0.95),
    (r"glpat-[A-Za-z0-9_-]{20,}", "gitlab_pat", 0.95),
    (r"xox[bporas]-[A-Za-z0-9-]{10,}", "slack_token", 0.90),
    (
        r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----",
        "private_key",
        0.99,
    ),
    (r"AKIA[0-9A-Z]{16}", "aws_access_key", 0.95),
    (
        r"(?i)(?:password|passwd|pwd)\s*[:=]\s*[\x27\x22]?"
        r"[^\s\x27\x22]{8,}",
        "password",
        0.75,
    ),
    (
        r"(?i)(?:api_key|apikey|api[-_]secret)\s*[:=]\s*[\x27\x22]?"
        r"[^\s\x27\x22]{10,}",
        "api_key_assignment",
        0.80,
    ),
    (
        r"(?i)bearer\s+[A-Za-z0-9_.~+/=-]{20,}",
        "bearer_token",
        0.85,
    ),
    (
        r"(?i)basic\s+[A-Za-z0-9+/=]{20,}",
        "basic_auth",
        0.80,
    ),
    (
        r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"
        r"\.[A-Za-z0-9_-]+",
        "jwt_token",
        0.90,
    ),
]


@dataclass(slots=True)
class CredentialScanner:
    """Scans text for leaked credentials."""

    _scan_count: int = 0
    _custom_patterns: list[tuple[str, str, float]] = field(
        default_factory=list,
    )

    def scan(self, text: str) -> ScanResult:
        """Scan text for credential leaks."""
        self._scan_count += 1
        matches: list[CredentialMatch] = []
        lines = text.split("\n")
        all_patterns = _CREDENTIAL_PATTERNS + self._custom_patterns
        for line_no, line in enumerate(lines, 1):
            for pattern, cred_type, confidence in all_patterns:
                for m in re.finditer(pattern, line):
                    raw = m.group(0)
                    redacted = _redact(raw)
                    matches.append(CredentialMatch(
                        credential_type=cred_type,
                        matched_value=redacted,
                        line_number=line_no,
                        confidence=confidence,
                    ))
        if matches:
            logger.warning(
                "credentials_detected",
                count=len(matches),
                types=list({m.credential_type for m in matches}),
            )
        return ScanResult(
            text_length=len(text), matches=tuple(matches),
        )

    def scan_lines(self, lines: list[str]) -> ScanResult:
        """Scan a list of lines for credential leaks."""
        return self.scan("\n".join(lines))

    def add_pattern(
        self,
        pattern: str,
        credential_type: str,
        confidence: float = 0.8,
    ) -> None:
        """Register a custom credential pattern."""
        self._custom_patterns.append(
            (pattern, credential_type, confidence),
        )

    def has_leaks(self, text: str) -> bool:
        """Quick check: does the text contain credential leaks?"""
        return self.scan(text).has_leaks

    @property
    def scan_count(self) -> int:
        return self._scan_count


def _redact(value: str) -> str:
    """Redact a credential value, keeping first and last 4 chars."""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]
