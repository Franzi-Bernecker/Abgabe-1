"""Tests für das Passwort-Hashing (PBKDF2)."""

from cardioconnect.auth import hash_password, verify_password


def test_roundtrip():
    pw_hash, salt = hash_password("geheim123")
    assert verify_password("geheim123", pw_hash, salt)


def test_wrong_password_fails():
    pw_hash, salt = hash_password("geheim123")
    assert not verify_password("falsch", pw_hash, salt)


def test_salt_makes_hashes_differ():
    hash_a, salt_a = hash_password("geheim123")
    hash_b, salt_b = hash_password("geheim123")
    assert salt_a != salt_b
    assert hash_a != hash_b


def test_same_salt_is_deterministic():
    hash_a, salt = hash_password("geheim123")
    hash_b, _ = hash_password("geheim123", salt)
    assert hash_a == hash_b
