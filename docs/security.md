# Security Guide

## Authentication

VaultBot supports multiple authentication modes:
- **Token-based** — Shared secret for gateway access
- **Password** — Password-protected gateway
- **Device pairing** — Trust-verified device tokens
- **Role-based** — Admin, read, write, approvals, pairing roles

## Secrets Management

Secrets are resolved through pluggable providers:
- Environment variables
- Static configuration
- File-based secrets
- OAuth token refresh

All secret access is audited.

## Code Scanning

The built-in code scanner detects:
- Command injection patterns
- Hardcoded credentials
- Unsafe deserialization
- SSL verification bypass
- World-writable permissions

## Rate Limiting

Per-session and per-user rate limiting with configurable thresholds.

## Audit Trail

All actions are tracked through the ACP provenance system with configurable modes (off/meta/meta+receipt).
