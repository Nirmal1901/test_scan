import hashlib

import pytest

from app.security import (
    PBKDF2_ALGORITHM,
    hash_password,
    new_reset_code,
    verify_password,
)


def test_hash_password_roundtrips():
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored) is True


def test_hash_password_is_salted():
    # Two hashes of the same password must differ (random salt per call)...
    first = hash_password("same-pass")
    second = hash_password("same-pass")
    assert first != second
    # ...and both must still verify.
    assert verify_password("same-pass", first) is True
    assert verify_password("same-pass", second) is True


def test_hash_password_never_stores_plaintext():
    stored = hash_password("plain-text-pass")
    assert "plain-text-pass" not in stored
    assert stored.startswith(PBKDF2_ALGORITHM + "$")


def test_hash_password_format_is_algorithm_iterations_salt_digest():
    stored = hash_password("x")
    parts = stored.split("$")
    assert len(parts) == 4
    assert parts[0] == PBKDF2_ALGORITHM
    assert int(parts[1]) > 0
    bytes.fromhex(parts[2])
    bytes.fromhex(parts[3])


def test_verify_password_rejects_wrong_password():
    stored = hash_password("right-pass")
    assert verify_password("wrong-pass", stored) is False
    assert verify_password("", stored) is False


def test_verify_password_accepts_legacy_md5_digest():
    legacy = hashlib.md5(b"legacy-pass").hexdigest()
    assert verify_password("legacy-pass", legacy) is True
    assert verify_password("other-pass", legacy) is False


@pytest.mark.parametrize("stored", ["", None, "not-a-hash", "pbkdf2_sha256$bad$zz$zz", "deadbeef"])
def test_verify_password_rejects_malformed_stored_values(stored):
    assert verify_password("anything", stored) is False


def test_verify_password_rejects_non_string_stored_values():
    assert verify_password("anything", 12345) is False
    assert verify_password("anything", b"deadbeef") is False


def test_verify_password_handles_unicode_passwords():
    stored = hash_password("pässwörd-✓")
    assert verify_password("pässwörd-✓", stored) is True
    assert verify_password("passwörd-✓", stored) is False


def test_new_reset_code_is_six_digit_numeric_string():
    for _ in range(20):
        code = new_reset_code()
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()
        assert 100000 <= int(code) <= 999999
