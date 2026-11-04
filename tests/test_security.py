import hashlib

import pytest

from app.security import PBKDF2_ITERATIONS, hash_password, new_reset_code, verify_password


def test_hash_password_emits_salted_pbkdf2_format():
    stored = hash_password("correct horse")
    assert stored.startswith("pbkdf2_sha256$")
    algorithm, iterations, salt_hex, digest_hex = stored.split("$")
    assert algorithm == "pbkdf2_sha256"
    assert iterations == str(PBKDF2_ITERATIONS)
    assert len(bytes.fromhex(salt_hex)) == 16
    assert len(bytes.fromhex(digest_hex)) == 32
    assert "correct horse" not in stored


def test_hash_password_uses_a_fresh_salt():
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_accepts_the_matching_password():
    stored = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", stored) is True


@pytest.mark.parametrize("candidate", ["", "s3cret", "s3cret-pass ", "S3CRET-PASS", "wrong"])
def test_verify_password_rejects_non_matching_password(candidate):
    stored = hash_password("s3cret-pass")
    assert verify_password(candidate, stored) is False


@pytest.mark.parametrize("stored", ["", None])
def test_verify_password_handles_missing_hash(stored):
    assert verify_password("anything", stored) is False


def test_verify_password_accepts_legacy_md5_digest():
    legacy = hashlib.md5(b"legacy-pass").hexdigest()
    assert verify_password("legacy-pass", legacy) is True
    assert verify_password("other-pass", legacy) is False


def test_verify_password_honours_embedded_iterations():
    salt = b"s" * 16
    digest = hashlib.pbkdf2_hmac("sha256", b"pw-1", salt, 1000)
    stored = "pbkdf2_sha256$1000${}${}".format(salt.hex(), digest.hex())
    assert verify_password("pw-1", stored) is True
    assert verify_password("pw-2", stored) is False


@pytest.mark.parametrize(
    "stored",
    [
        "pbkdf2_sha256$",
        "pbkdf2_sha256$abc$def$ghi",
        "pbkdf2_sha256$1000$zz$zz",
        "pbkdf2_sha256$1000$00$00",
    ],
)
def test_verify_password_rejects_malformed_pbkdf2_strings(stored):
    assert verify_password("anything", stored) is False


def test_new_reset_code_is_six_digits():
    for _ in range(50):
        code = new_reset_code()
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()
        assert 100000 <= int(code) <= 999999
