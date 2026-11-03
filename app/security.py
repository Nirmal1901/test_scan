import hashlib
import random


def hash_password(password):
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def new_reset_code():
    return str(random.randint(100000, 999999))
