"""Two-factor authentication for CRITICAL severity actions.

Implements TOTP (Time-based One-Time Password) for second-factor
verification on critical operations.
"""

from __future__ import annotations

import hashlib
import hmac
import struct
import time
from dataclasses import dataclass

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_TOTP_DIGITS = 6
_TOTP_PERIOD = 30  # seconds
_TOTP_WINDOW = 1  # Allow 1 period before/after


@dataclass(frozen=True, slots=True)
class TOTPSetup:
    """TOTP setup information for the user."""

    secret_hex: str
    provisioning_uri: str


def generate_totp_secret() -> str:
    """Generate a random TOTP secret (hex-encoded)."""
    import secrets

    return secrets.token_hex(20)


def compute_totp(secret_hex: str, timestamp: int | None = None) -> str:
    """Compute the current TOTP code."""
    if timestamp is None:
        timestamp = int(time.time())

    counter = timestamp // _TOTP_PERIOD
    secret_bytes = bytes.fromhex(secret_hex)
    counter_bytes = struct.pack(">Q", counter)

    hmac_hash = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    code = struct.unpack(">I", hmac_hash[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**_TOTP_DIGITS)).zfill(_TOTP_DIGITS)


def verify_totp(secret_hex: str, code: str, timestamp: int | None = None) -> bool:
    """Verify a TOTP code with window tolerance."""
    if timestamp is None:
        timestamp = int(time.time())

    for offset in range(-_TOTP_WINDOW, _TOTP_WINDOW + 1):
        ts = timestamp + (offset * _TOTP_PERIOD)
        expected = compute_totp(secret_hex, ts)
        if hmac.compare_digest(code, expected):
            return True
    return False


def get_provisioning_uri(
    secret_hex: str, account: str = "vaultbot", issuer: str = "VaultBot"
) -> str:
    """Generate an otpauth:// URI for authenticator apps."""
    import base64

    secret_b32 = base64.b32encode(bytes.fromhex(secret_hex)).decode("utf-8").rstrip("=")
    return f"otpauth://totp/{issuer}:{account}?secret={secret_b32}&issuer={issuer}&digits={_TOTP_DIGITS}&period={_TOTP_PERIOD}"


class TwoFactorManager:
    """Manages 2FA setup and verification."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}  # user_id -> secret_hex
        self._enabled: bool = False

    def setup(self, user_id: str) -> TOTPSetup:
        """Set up 2FA for a user. Returns setup info including QR data."""
        secret = generate_totp_secret()
        self._secrets[user_id] = secret
        self._enabled = True
        uri = get_provisioning_uri(secret, account=user_id)
        logger.info("2fa_setup", user_id=user_id)
        return TOTPSetup(secret_hex=secret, provisioning_uri=uri)

    def verify(self, user_id: str, code: str) -> bool:
        """Verify a 2FA code for a user."""
        secret = self._secrets.get(user_id)
        if not secret:
            return False
        result = verify_totp(secret, code)
        if result:
            logger.info("2fa_verified", user_id=user_id)
        else:
            logger.warning("2fa_failed", user_id=user_id)
        return result

    def is_enabled(self, user_id: str) -> bool:
        return user_id in self._secrets

    def remove(self, user_id: str) -> bool:
        if user_id in self._secrets:
            del self._secrets[user_id]
            return True
        return False

    @property
    def enabled(self) -> bool:
        return self._enabled
