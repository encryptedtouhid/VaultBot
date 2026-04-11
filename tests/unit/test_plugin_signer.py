"""Tests for plugin signing and verification."""

import json
import tempfile
from pathlib import Path

import pytest

from vaultbot.plugins.signer import PluginSigner, PluginVerifier, _hash_plugin_directory


@pytest.fixture
def signer() -> PluginSigner:
    return PluginSigner.generate()


@pytest.fixture
def plugin_dir() -> Path:
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir) / "test-plugin"
        d.mkdir()
        (d / "plugin.py").write_text("print('hello')")
        (d / "vaultbot_plugin.json").write_text(
            json.dumps(
                {
                    "name": "test-plugin",
                    "version": "1.0.0",
                    "description": "A test plugin",
                    "author": "tester",
                }
            )
        )
        yield d


def test_generate_keypair() -> None:
    signer = PluginSigner.generate()
    assert len(signer.public_key_bytes) == 32
    assert signer.private_key_pem.startswith(b"-----BEGIN PRIVATE KEY-----")


def test_sign_and_verify(signer: PluginSigner, plugin_dir: Path) -> None:
    # Sign
    sig = signer.sign_plugin("test-plugin", "1.0.0", plugin_dir)
    assert sig.plugin_name == "test-plugin"
    assert sig.plugin_version == "1.0.0"
    assert len(sig.signature) > 0

    # Verify with trusted key
    with tempfile.TemporaryDirectory() as trust_dir:
        verifier = PluginVerifier(trust_store_dir=Path(trust_dir))
        verifier.add_trusted_key(signer.public_key_bytes, "test-signer")

        result = verifier.verify_plugin(plugin_dir)
        assert result is not None
        assert result.plugin_name == "test-plugin"


def test_reject_unsigned_plugin(plugin_dir: Path) -> None:
    with tempfile.TemporaryDirectory() as trust_dir:
        verifier = PluginVerifier(trust_store_dir=Path(trust_dir))
        result = verifier.verify_plugin(plugin_dir)
        assert result is None


def test_reject_untrusted_signer(signer: PluginSigner, plugin_dir: Path) -> None:
    signer.sign_plugin("test-plugin", "1.0.0", plugin_dir)

    # Verify with empty trust store (key not trusted)
    with tempfile.TemporaryDirectory() as trust_dir:
        verifier = PluginVerifier(trust_store_dir=Path(trust_dir))
        result = verifier.verify_plugin(plugin_dir)
        assert result is None


def test_reject_tampered_plugin(signer: PluginSigner, plugin_dir: Path) -> None:
    signer.sign_plugin("test-plugin", "1.0.0", plugin_dir)

    # Tamper with the plugin after signing
    (plugin_dir / "plugin.py").write_text("print('EVIL CODE')")

    with tempfile.TemporaryDirectory() as trust_dir:
        verifier = PluginVerifier(trust_store_dir=Path(trust_dir))
        verifier.add_trusted_key(signer.public_key_bytes, "test-signer")
        result = verifier.verify_plugin(plugin_dir)
        assert result is None  # Tampered = rejected


def test_hash_is_deterministic(plugin_dir: Path) -> None:
    hash1 = _hash_plugin_directory(plugin_dir)
    hash2 = _hash_plugin_directory(plugin_dir)
    assert hash1 == hash2


def test_hash_changes_with_content(plugin_dir: Path) -> None:
    hash1 = _hash_plugin_directory(plugin_dir)
    (plugin_dir / "plugin.py").write_text("print('changed')")
    hash2 = _hash_plugin_directory(plugin_dir)
    assert hash1 != hash2


def test_signer_from_key_bytes(signer: PluginSigner) -> None:
    pem = signer.private_key_pem
    restored = PluginSigner.from_key_bytes(pem)
    assert restored.public_key_bytes == signer.public_key_bytes


def test_signature_serialization(signer: PluginSigner, plugin_dir: Path) -> None:
    sig = signer.sign_plugin("test-plugin", "1.0.0", plugin_dir)
    from vaultbot.plugins.signer import PluginSignature

    data = sig.to_dict()
    restored = PluginSignature.from_dict(data)
    assert restored.plugin_name == sig.plugin_name
    assert restored.signature == sig.signature
    assert restored.content_hash == sig.content_hash
