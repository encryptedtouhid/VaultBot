"""Tests for the credential store."""

from zenbot.utils.crypto import decrypt, derive_key, encrypt, generate_salt


def test_encrypt_decrypt_roundtrip() -> None:
    salt = generate_salt()
    key = derive_key("test-passphrase", salt)
    original = "my-secret-api-key-12345"
    encrypted = encrypt(original, key)
    decrypted = decrypt(encrypted, key)
    assert decrypted == original


def test_different_passphrases_produce_different_keys() -> None:
    salt = generate_salt()
    key1 = derive_key("passphrase-one", salt)
    key2 = derive_key("passphrase-two", salt)
    assert key1 != key2


def test_different_salts_produce_different_keys() -> None:
    salt1 = generate_salt()
    salt2 = generate_salt()
    key1 = derive_key("same-passphrase", salt1)
    key2 = derive_key("same-passphrase", salt2)
    assert key1 != key2


def test_salt_is_16_bytes() -> None:
    salt = generate_salt()
    assert len(salt) == 16
