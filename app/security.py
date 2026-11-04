import hashlib
import hmac
import os
import secrets

_PBKDF2_ITERATIONS = 260000


def hash_password(password):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(stored, password):
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _algo, iterations, salt_hex, hash_hex = stored.split("$", 3)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
            )
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(dk.hex(), hash_hex)
    # Anything that is not a pbkdf2 record (e.g. a bare legacy digest) is rejected;
    # such rows are recovered through the password reset flow.
    return False


def new_reset_code():
    return str(secrets.randbelow(900000) + 100000)
