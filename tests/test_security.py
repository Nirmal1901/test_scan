import hashlib
import os

from app.security import hash_password, new_reset_code, verify_password


def _parts(stored):
    algo, iterations, salt_hex, digest_hex = stored.split("$")
    return algo, int(iterations), salt_hex, digest_hex


def test_hash_password_produces_parseable_pbkdf2_record():
    algo, iterations, salt_hex, digest_hex = _parts(hash_password("correct horse"))

    assert algo == "pbkdf2_sha256"
    assert iterations > 0
    assert len(salt_hex) == 32  # 16 random bytes
    assert len(digest_hex) == 64
    # both halves are valid hex
    assert bytes.fromhex(salt_hex)
    assert bytes.fromhex(digest_hex)


def test_hash_password_never_stores_the_plaintext():
    password = "correct horse"
    stored = hash_password(password)

    assert stored != password
    assert password not in stored
    assert stored.startswith("pbkdf2_sha256$")


def test_same_password_gets_a_unique_salt_per_record():
    first = hash_password("shared-pass-1")
    second = hash_password("shared-pass-1")

    assert first != second
    assert _parts(first)[2] != _parts(second)[2]
    assert verify_password(first, "shared-pass-1") is True
    assert verify_password(second, "shared-pass-1") is True


def test_verify_password_accepts_the_matching_secret_only():
    stored = hash_password("s3cret-Pass!")

    assert verify_password(stored, "s3cret-Pass!") is True
    assert verify_password(stored, "s3cret-pass!") is False
    assert verify_password(stored, "s3cret-Pass! ") is False
    assert verify_password(stored, "s3cret-Pass") is False


def test_verify_password_supports_unicode_secrets():
    stored = hash_password("pässwörd-🔐")

    assert verify_password(stored, "pässwörd-🔐") is True
    assert verify_password(stored, "passwort") is False


def test_verify_password_rejects_legacy_bare_digest_records():
    # 32-char bare digest (md5 of "password") is no longer an accepted record format;
    # such rows must go through the reset flow instead of matching here.
    legacy_bare_digest = "5f4dcc3b5aa765d61d8327deb882cf99"

    assert verify_password(legacy_bare_digest, "password") is False
    assert verify_password(legacy_bare_digest, "not-password") is False


def test_verify_password_rejects_empty_and_malformed_records():
    assert verify_password(None, "x") is False
    assert verify_password("", "x") is False
    assert verify_password("pbkdf2_sha256$broken", "x") is False
    assert verify_password("pbkdf2_sha256$10$not-hex$not-hex", "x") is False


def test_record_format_survives_dollar_signs_in_the_secret():
    # The record is "$"-delimited, so a secret containing "$" must not corrupt it.
    dollar = chr(36)
    password = "pa" + dollar * 2 + "word" + dollar + "with" + dollar + "dollars"
    stored = hash_password(password)

    assert stored.count(dollar) == 3
    assert _parts(stored)[0] == "pbkdf2_sha256"
    assert verify_password(stored, password) is True
    assert verify_password(stored, password[:-1]) is False


def test_verify_password_honours_the_iteration_count_stored_in_the_record():
    # Rows written with a different work factor must keep verifying.
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", b"rotate-me", salt, 1000)
    record = "pbkdf2_sha256$1000$%s$%s" % (salt.hex(), digest.hex())

    assert verify_password(record, "rotate-me") is True
    assert verify_password(record, "rotate-you") is False


def test_hash_password_handles_long_and_empty_secrets():
    long_password = "long-" * 1000
    stored = hash_password(long_password)
    assert verify_password(stored, long_password) is True
    assert verify_password(stored, long_password[:-1]) is False

    empty = hash_password("")
    assert empty.startswith("pbkdf2_sha256$")
    assert verify_password(empty, "") is True
    assert verify_password(empty, "x") is False


def test_stored_record_is_text_and_verifies_repeatedly():
    stored = hash_password("reused-across-many-requests")

    assert isinstance(stored, str)
    assert stored.count("$") == 3
    for _ in range(3):
        assert verify_password(stored, "reused-across-many-requests") is True


def test_new_reset_code_is_a_six_digit_numeric_string():
    for _ in range(20):
        code = new_reset_code()
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()
        assert 100000 <= int(code) <= 999999


def test_new_reset_code_varies_between_calls():
    assert len({new_reset_code() for _ in range(20)}) > 1
