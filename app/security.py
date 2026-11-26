import hashlib
import hmac
import secrets

PBKDF2_ALGORITHM = "pbkdf2_sha256"  # SHA-256, not SHA-1/MD5
PBKDF2_ITERATIONS = 600_000  # OWASP 2023 guidance for PBKDF2-HMAC-SHA256
PBKDF2_SALT_BYTES = 16


def hash_password(password):
    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "{}${}${}${}".format(PBKDF2_ALGORITHM, PBKDF2_ITERATIONS, salt.hex(), dk.hex())


def verify_password(password, stored):
    if not isinstance(stored, str) or not stored:
        return False
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == PBKDF2_ALGORITHM:
        try:
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected = bytes.fromhex(parts[3])
        except ValueError:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    # Legacy unsalted MD5 digests (32 hex chars) still verify so existing rows log in.
    if len(stored) == 32:
        legacy = hashlib.md5(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored)
    return False


def new_reset_code():
    return str(secrets.randbelow(900000) + 100000)
