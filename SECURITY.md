# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in VaultBot, please report it responsibly.

**DO NOT** open a public GitHub issue for security vulnerabilities.

### How to Report

1. Email: Send details to **security@vaultbot.app** (placeholder — update with real contact)
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Assessment**: Within 7 days we will confirm the vulnerability and its severity
- **Fix**: Critical vulnerabilities will be patched within 14 days
- **Disclosure**: We will coordinate public disclosure with you after a fix is available

### Scope

The following are in scope:
- VaultBot core application code
- Security module (credentials, auth, audit, rate limiting, policy)
- Platform adapters
- LLM adapters
- Plugin sandbox and signing system
- CLI commands

The following are out of scope:
- Third-party dependencies (report to them directly)
- Social engineering attacks
- Denial of service attacks against test/demo instances

## Security Design Principles

VaultBot is built with a security-first architecture:

1. **Zero-trust by default**: All users must be explicitly allowlisted
2. **Encrypted credential storage**: OS keychain or Fernet-encrypted fallback; never plain text
3. **Immutable security defaults**: Core security settings cannot be disabled
4. **Plugin sandboxing**: Ed25519 signing + subprocess isolation + manifest-declared permissions
5. **Action approval flows**: Destructive or sensitive actions require explicit user confirmation
6. **Audit logging**: All security events are logged and append-only
7. **Rate limiting**: Per-user and global rate limits enabled by default

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
