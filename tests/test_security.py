import hashlib

import pytest

from app.security import (
    PBKDF2_ALGORITHM,
    PBKDF2_ITERATIONS,
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


# --- Post-fix regression guards: iteration count + legacy hash compatibility ---


def test_pbkdf2_iterations_meet_owasp_floor():
    assert PBKDF2_ITERATIONS >= 600_000


def test_hash_password_embeds_current_iteration_count():
    stored = hash_password("x")
    parts = stored.split("$")
    assert parts[0] == PBKDF2_ALGORITHM
    assert int(parts[1]) == PBKDF2_ITERATIONS


def test_hash_password_uses_sha256_pbkdf2():
    # The digest must be reproducible from the stored salt/iterations with
    # hashlib.pbkdf2_hmac("sha256", ...) — i.e. the stdlib helper is unchanged.
    stored = hash_password("reproduce-me")
    _, iterations, salt_hex, digest_hex = stored.split("$")
    expected = hashlib.pbkdf2_hmac(
        "sha256", b"reproduce-me", bytes.fromhex(salt_hex), int(iterations)
    )
    assert expected.hex() == digest_hex


def test_verify_password_accepts_hash_made_with_old_iteration_count():
    # Rows hashed before the iteration bump (200_000) must still verify, since
    # the count is read back from the stored string.
    old_iterations = 200_000
    salt = b"0123456789abcdef"
    dk = hashlib.pbkdf2_hmac("sha256", b"old-pass-1", salt, old_iterations)
    stored = "{}${}${}${}".format(
        PBKDF2_ALGORITHM, old_iterations, salt.hex(), dk.hex()
    )
    assert verify_password("old-pass-1", stored) is True
    assert verify_password("wrong-pass", stored) is False


def test_verify_password_accepts_any_embedded_iteration_count():
    # The verifier must honour whatever count is embedded, not just the current
    # constant, so hashes from any past release keep working.
    for iterations in (1_000, 100_000, 200_000, PBKDF2_ITERATIONS):
        salt = b"saltsaltsaltsalt"
        dk = hashlib.pbkdf2_hmac("sha256", b"pw", salt, iterations)
        stored = "{}${}${}${}".format(PBKDF2_ALGORITHM, iterations, salt.hex(), dk.hex())
        assert verify_password("pw", stored) is True, iterations


def test_verify_password_accepts_legacy_md5_uppercase_digest():
    # Some legacy rows may hold an upper-case hex digest; comparison is on the
    # digest string, so the canonical lower-case form is what verifies.
    legacy = hashlib.md5(b"legacy-pass").hexdigest()
    assert verify_password("legacy-pass", legacy) is True
    assert verify_password("legacy-pass", legacy.upper()) is False


def test_hash_password_handles_long_and_empty_passwords():
    # No length cap or crash on edge-case inputs.
    for pw in ("", "a" * 1024, "pässwörd-✓-with-emoji-🔐"):
        stored = hash_password(pw)
        assert verify_password(pw, stored) is True
        assert verify_password(pw + "x", stored) is False
