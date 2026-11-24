import hashlib
import hmac
import random

from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, stored):
    if not stored:
        return False
    if stored.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, password)
    # Legacy rows created before the switch to a salted KDF.
    legacy = hashlib.md5(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


def new_reset_code():
    return str(random.randint(100000, 999999))
