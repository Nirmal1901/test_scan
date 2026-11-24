import os
import re

_SAFE_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

def _safe_join(base, name, label):
    """Join a single, literal path component onto base, refusing traversal."""
    # Allow-list gate: reject empty names, "." / "..", absolute paths and any
    # component containing a path separator or other unexpected character.
    if not _SAFE_COMPONENT_RE.fullmatch(name or ""):
        raise ValueError("unsafe path component for " + label)
    # Second gate: the name must be a bare basename (no separators, no "..").
    if name != os.path.basename(name):
        raise ValueError("unsafe path component for " + label)
    base = os.path.abspath(base)
    # Canonicalize (resolving symlinks) before the containment check so a
    # symlink inside base cannot be used to escape it.
    candidate = os.path.realpath(os.path.join(base, name))
    try:
        contained = os.path.commonpath([candidate, base]) == base
    except ValueError:
        contained = False
    if not contained:
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
