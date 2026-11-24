import os

def _safe_join(base, name, label):
    """Join a single, literal path component onto base, refusing traversal."""
    if name in ("", ".", "..") or name != os.path.basename(name):
        raise ValueError("unsafe path component for " + label)
    base = os.path.abspath(base)
    candidate = os.path.abspath(os.path.join(base, name))
    if candidate != base and os.path.commonpath([base, candidate]) != base:
        raise ValueError("unsafe path component for " + label)
    return candidate


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTANCE_DIR = _safe_join(BASE_DIR, "instance", "INSTANCE_DIR")

SECRET_KEY = "shopdesk-prod-2024-secret"
DATABASE = _safe_join(INSTANCE_DIR, "shopdesk.db", "DATABASE")
UPLOAD_DIR = _safe_join(INSTANCE_DIR, "uploads", "UPLOAD_DIR")
PREFS_DIR = _safe_join(INSTANCE_DIR, "prefs", "PREFS_DIR")

ADMIN_EMAIL = "admin@shopdesk.local"
ADMIN_PASSWORD = "Admin@12345"

PAYMENT_API_URL = "https://payments.example.com/v1/charge"
PAYMENT_API_KEY = "sk_live_51Hq3JdKq9fXb7T2mPzVn4wLc"

SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = None
