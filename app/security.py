import hashlib
import hmac
import os
import random

PBKDF2_ITERATIONS = 200000


def hash_password(password):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS, salt.hex(), dk.hex()
    )


def verify_password(password, stored):
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt_hex, dk_hex = stored.split("$", 3)
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(dk, bytes.fromhex(dk_hex))
    # Legacy unsalted MD5 rows (pre-migration).
    legacy = hashlib.md5(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


def new_reset_code():
    return str(random.randint(100000, 999999))
