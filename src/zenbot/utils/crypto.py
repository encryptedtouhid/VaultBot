"""Encryption helpers for credential storage fallback."""

from __future__ import annotations

import base64
import secrets

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a passphrase using Argon2id."""
    raw_key = hash_secret_raw(
        secret=passphrase.encode(),
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID,
    )
    return base64.urlsafe_b64encode(raw_key)


def generate_salt() -> bytes:
    """Generate a cryptographically secure random salt."""
    return secrets.token_bytes(16)


def encrypt(data: str, key: bytes) -> bytes:
    """Encrypt a string using Fernet symmetric encryption."""
    f = Fernet(key)
    return f.encrypt(data.encode())


def decrypt(token: bytes, key: bytes) -> str:
    """Decrypt Fernet-encrypted data back to a string."""
    f = Fernet(key)
    return f.decrypt(token).decode()
