"""Ed25519 plugin signing and verification.

Plugins must be signed to be loaded. This module handles:
- Generating signing keypairs
- Signing plugin packages
- Verifying plugin signatures against a trust store
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)

_TRUST_STORE_DIR = Path.home() / ".vaultbot" / "trust_store"
_SIGNATURE_FILENAME = "vaultbot_plugin.sig"


@dataclass(frozen=True, slots=True)
class PluginSignature:
    """A plugin's cryptographic signature."""

    plugin_name: str
    plugin_version: str
    content_hash: str  # SHA-256 of plugin contents
    signature: bytes  # Ed25519 signature
    signer_public_key: bytes  # Public key that created this signature

    def to_dict(self) -> dict[str, str]:
        return {
            "plugin_name": self.plugin_name,
            "plugin_version": self.plugin_version,
            "content_hash": self.content_hash,
            "signature": self.signature.hex(),
            "signer_public_key": self.signer_public_key.hex(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> PluginSignature:
        return cls(
            plugin_name=data["plugin_name"],
            plugin_version=data["plugin_version"],
            content_hash=data["content_hash"],
            signature=bytes.fromhex(data["signature"]),
            signer_public_key=bytes.fromhex(data["signer_public_key"]),
        )


class PluginSigner:
    """Signs plugins with an Ed25519 private key."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def generate(cls) -> PluginSigner:
        """Generate a new signing keypair."""
        private_key = Ed25519PrivateKey.generate()
        return cls(private_key)

    @classmethod
    def from_key_bytes(cls, private_key_bytes: bytes) -> PluginSigner:
        """Load a signer from raw private key bytes."""
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        private_key = load_pem_private_key(private_key_bytes, password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError("Key is not an Ed25519 private key")
        return cls(private_key)

    @property
    def public_key_bytes(self) -> bytes:
        """Get the public key in raw bytes format."""
        return self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

    @property
    def private_key_pem(self) -> bytes:
        """Get the private key in PEM format for storage."""
        return self._private_key.private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )

    def sign_plugin(
        self,
        plugin_name: str,
        plugin_version: str,
        plugin_dir: Path,
    ) -> PluginSignature:
        """Sign a plugin directory.

        Computes SHA-256 over all Python files in the directory,
        then signs the hash with Ed25519.
        """
        content_hash = _hash_plugin_directory(plugin_dir)
        sign_data = _build_sign_data(plugin_name, plugin_version, content_hash)
        signature = self._private_key.sign(sign_data)

        sig = PluginSignature(
            plugin_name=plugin_name,
            plugin_version=plugin_version,
            content_hash=content_hash,
            signature=signature,
            signer_public_key=self.public_key_bytes,
        )

        # Write signature file
        sig_path = plugin_dir / _SIGNATURE_FILENAME
        sig_path.write_text(json.dumps(sig.to_dict(), indent=2))
        sig_path.chmod(0o644)

        logger.info(
            "plugin_signed",
            plugin=plugin_name,
            version=plugin_version,
        )
        return sig


class PluginVerifier:
    """Verifies plugin signatures against a trust store of public keys."""

    def __init__(self, trust_store_dir: Path | None = None) -> None:
        self._trust_store_dir = trust_store_dir or _TRUST_STORE_DIR
        self._trusted_keys: set[bytes] = set()
        self._load_trust_store()

    def _load_trust_store(self) -> None:
        """Load trusted public keys from the trust store directory."""
        if not self._trust_store_dir.exists():
            self._trust_store_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            return

        for key_file in self._trust_store_dir.glob("*.pub"):
            try:
                key_bytes = bytes.fromhex(key_file.read_text().strip())
                self._trusted_keys.add(key_bytes)
                logger.info("trusted_key_loaded", file=key_file.name)
            except (ValueError, OSError) as e:
                logger.warning("invalid_trust_store_key", file=key_file.name, error=str(e))

    def add_trusted_key(self, public_key_bytes: bytes, name: str = "") -> None:
        """Add a public key to the trust store."""
        self._trusted_keys.add(public_key_bytes)
        if name:
            key_file = self._trust_store_dir / f"{name}.pub"
            key_file.write_text(public_key_bytes.hex())
            key_file.chmod(0o644)
            logger.info("trusted_key_added", name=name)

    def is_trusted(self, public_key_bytes: bytes) -> bool:
        """Check if a public key is in the trust store."""
        return public_key_bytes in self._trusted_keys

    def verify_plugin(self, plugin_dir: Path) -> PluginSignature | None:
        """Verify a plugin's signature.

        Returns the signature if valid and trusted, None otherwise.
        """
        sig_path = plugin_dir / _SIGNATURE_FILENAME
        if not sig_path.exists():
            logger.warning("plugin_unsigned", path=str(plugin_dir))
            return None

        try:
            sig_data = json.loads(sig_path.read_text())
            sig = PluginSignature.from_dict(sig_data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("invalid_signature_file", path=str(sig_path), error=str(e))
            return None

        # Check if the signer is trusted
        if not self.is_trusted(sig.signer_public_key):
            logger.warning(
                "untrusted_signer",
                plugin=sig.plugin_name,
                signer_key=sig.signer_public_key.hex()[:16] + "...",
            )
            return None

        # Verify content hash matches current files
        current_hash = _hash_plugin_directory(plugin_dir)
        if current_hash != sig.content_hash:
            logger.warning(
                "plugin_tampered",
                plugin=sig.plugin_name,
                expected_hash=sig.content_hash[:16] + "...",
                actual_hash=current_hash[:16] + "...",
            )
            return None

        # Verify the cryptographic signature
        try:
            public_key = Ed25519PublicKey.from_public_bytes(sig.signer_public_key)
            sign_data = _build_sign_data(
                sig.plugin_name, sig.plugin_version, sig.content_hash
            )
            public_key.verify(sig.signature, sign_data)
        except InvalidSignature:
            logger.warning("invalid_signature", plugin=sig.plugin_name)
            return None

        logger.info(
            "plugin_verified",
            plugin=sig.plugin_name,
            version=sig.plugin_version,
        )
        return sig


def _hash_plugin_directory(plugin_dir: Path) -> str:
    """Compute SHA-256 hash over all Python files in a plugin directory."""
    hasher = hashlib.sha256()

    # Sort files for deterministic hashing
    py_files = sorted(plugin_dir.rglob("*.py"))
    for py_file in py_files:
        # Skip __pycache__
        if "__pycache__" in str(py_file):
            continue
        hasher.update(py_file.name.encode())
        hasher.update(py_file.read_bytes())

    return hasher.hexdigest()


def _build_sign_data(name: str, version: str, content_hash: str) -> bytes:
    """Build the data blob that gets signed."""
    return f"vaultbot-plugin:{name}:{version}:{content_hash}".encode()
