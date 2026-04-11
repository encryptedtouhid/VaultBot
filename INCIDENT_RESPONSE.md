# Incident Response Plan

## Severity Classification

| Severity | Description | Response Time |
|---|---|---|
| **Critical** | Auth bypass, RCE, credential exposure | < 4 hours |
| **High** | Sandbox escape, prompt injection bypass | < 24 hours |
| **Medium** | Information disclosure, DoS | < 72 hours |
| **Low** | Minor security hardening | Next release |

## Response Procedure

1. **Detection**: Via security report, automated scanning, or user report.
2. **Triage**: Classify severity, assign responder.
3. **Containment**: If Critical/High, prepare hotfix immediately.
4. **Fix**: Develop and test patch.
5. **Release**: Push patched version.
6. **Disclosure**: Coordinate disclosure with reporter (90-day window).
7. **Review**: Post-incident review and hardening.

## Reporting

Report security vulnerabilities to: security@vaultbot.dev

Or via GitHub Security Advisories on the repository.

Do **not** open public issues for security vulnerabilities.
