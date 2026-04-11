"""Keyring-backed credential store with encrypted file fallback.

Never stores credentials in plain text. Uses the OS-native credential store
(macOS Keychain, Windows Credential Locker, GNOME Keyring) via the `keyring`
library. Falls back to Fernet-encrypted file storage when no desktop keyring
is available (e.g., headless servers).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import keyring
from keyring.errors import NoKeyringError

from vaultbot.utils.crypto import decrypt, derive_key, encrypt, generate_salt
from vaultbot.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

SERVICE_NAME = "vaultbot"
_ENCRYPTED_STORE_DIR = Path.home() / ".vaultbot" / "credentials"


class CredentialStore:
    """Secure credential storage with OS keychain and encrypted file fallback."""

    def __init__(self) -> None:
        self._use_keyring = self._check_keyring_available()
        self._encryption_key: bytes | None = None
        self._salt_path = _ENCRYPTED_STORE_DIR / ".salt"
        self._store_path = _ENCRYPTED_STORE_DIR / "vault.enc"

        if not self._use_keyring:
            logger.info(
                "os_keyring_unavailable",
                msg="Using encrypted file fallback for credential storage",
            )

    @staticmethod
    def _check_keyring_available() -> bool:
        """Check if a usable OS keyring backend is available."""
        try:
            keyring.get_keyring()
            # Try a no-op to verify the backend actually works
            keyring.get_password(SERVICE_NAME, "__zenbot_probe__")
            return True
        except (NoKeyringError, RuntimeError):
            return False

    def _ensure_encryption_key(self, passphrase: str | None = None) -> bytes:
        """Get or derive the encryption key for file-based fallback."""
        if self._encryption_key is not None:
            return self._encryption_key

        if passphrase is None:
            raise ValueError(
                "Passphrase required for encrypted file storage. "
                "Set VAULTBOT_VAULT_PASSPHRASE or use `vaultbot credentials unlock`."
            )

        _ENCRYPTED_STORE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

        if self._salt_path.exists():
            salt = self._salt_path.read_bytes()
        else:
            salt = generate_salt()
            self._salt_path.write_bytes(salt)
            self._salt_path.chmod(0o600)

        self._encryption_key = derive_key(passphrase, salt)
        return self._encryption_key

    def _load_file_store(self) -> dict[str, str]:
        """Load the encrypted credential file."""
        if not self._store_path.exists():
            return {}
        key = self._ensure_encryption_key()
        raw = self._store_path.read_bytes()
        return json.loads(decrypt(raw, key))  # type: ignore[arg-type]

    def _save_file_store(self, data: dict[str, str]) -> None:
        """Save credentials to the encrypted file."""
        key = self._ensure_encryption_key()
        encrypted = encrypt(json.dumps(data), key)
        self._store_path.write_bytes(encrypted)
        self._store_path.chmod(0o600)

    def unlock(self, passphrase: str) -> None:
        """Unlock the encrypted file store with a passphrase.

        Only needed when OS keyring is unavailable.
        """
        self._ensure_encryption_key(passphrase)
        logger.info("credential_store_unlocked")

    def get(self, key: str) -> str | None:
        """Retrieve a credential by key.

        Lookup order:
        1. Environment variable VAULTBOT_{KEY} (uppercase, for Docker)
        2. OS keychain (if available)
        3. Encrypted file store
        """
        import os

        env_key = f"VAULTBOT_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val

        if self._use_keyring:
            return keyring.get_password(SERVICE_NAME, key)
        return self._load_file_store().get(key)

    def set(self, key: str, value: str) -> None:
        """Store a credential securely."""
        if self._use_keyring:
            keyring.set_password(SERVICE_NAME, key, value)
            logger.info("credential_stored", key=key, backend="keyring")
        else:
            store = self._load_file_store()
            store[key] = value
            self._save_file_store(store)
            logger.info("credential_stored", key=key, backend="encrypted_file")

    def delete(self, key: str) -> None:
        """Remove a credential."""
        if self._use_keyring:
            try:
                keyring.delete_password(SERVICE_NAME, key)
            except keyring.errors.PasswordDeleteError:
                pass
            logger.info("credential_deleted", key=key, backend="keyring")
        else:
            store = self._load_file_store()
            store.pop(key, None)
            self._save_file_store(store)
            logger.info("credential_deleted", key=key, backend="encrypted_file")

    def exists(self, key: str) -> bool:
        """Check if a credential exists."""
        return self.get(key) is not None

    @staticmethod
    def check_for_plaintext_leaks() -> list[str]:
        """Scan for any plain-text credential files that should not exist.

        Returns a list of problematic file paths found.
        """
        suspicious_paths = [
            Path.home() / ".vaultbot" / "credentials.json",
            Path.home() / ".vaultbot" / "credentials.yaml",
            Path.home() / ".vaultbot" / "secrets.json",
            Path.home() / ".vaultbot" / ".env",
            # OpenClaw legacy paths
            Path.home() / ".clawdbot",
            Path.home() / ".moltbot",
        ]
        return [str(p) for p in suspicious_paths if p.exists()]
