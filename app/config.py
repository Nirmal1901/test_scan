import os
import re

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_SAFE_PART = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]{0,63}")


def _instance_path(*parts):
    """Build a canonicalized path under BASE_DIR/instance and validate it stays there."""
    instance = os.path.realpath(os.path.join(os.path.realpath(BASE_DIR), "instance"))
    for part in parts:
        if not isinstance(part, str) or not _SAFE_PART.fullmatch(part):
            raise ValueError("instance path component is not allowlisted")
    candidate = os.path.realpath(os.path.join(instance, *parts))
    if os.path.commonpath([instance, candidate]) != instance:
        raise ValueError("instance path escapes instance directory")
    return candidate


SECRET_KEY = "shopdesk-prod-2024-secret"
INSTANCE_DIR = _instance_path()
DATABASE = _instance_path("shopdesk.db")
UPLOAD_DIR = _instance_path("uploads")
PREFS_DIR = _instance_path("prefs")

ADMIN_EMAIL = "admin@shopdesk.local"
ADMIN_PASSWORD = "Admin@12345"

PAYMENT_API_URL = "https://payments.example.com/v1/charge"
PAYMENT_API_KEY = "sk_live_51Hq3JdKq9fXb7T2mPzVn4wLc"

SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = None
