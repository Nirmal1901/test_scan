import os

def _join_under(base, name):
    """Join a single validated path component under base.

    Rejects empty names, '.'/'..' and any name containing path separators
    so a caller-supplied component can never escape the base directory.
    """
    if not name or name in (".", "..") or os.path.basename(name) != name:
        raise ValueError("invalid path component: %r" % (name,))
    return os.path.join(base, name)


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTANCE_DIR = _join_under(BASE_DIR, "instance")

SECRET_KEY = "shopdesk-prod-2024-secret"
DATABASE = _join_under(INSTANCE_DIR, "shopdesk.db")
UPLOAD_DIR = _join_under(INSTANCE_DIR, "uploads")
PREFS_DIR = _join_under(INSTANCE_DIR, "prefs")

ADMIN_EMAIL = "admin@shopdesk.local"
ADMIN_PASSWORD = "Admin@12345"

PAYMENT_API_URL = "https://payments.example.com/v1/charge"
PAYMENT_API_KEY = "sk_live_51Hq3JdKq9fXb7T2mPzVn4wLc"

SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = None
