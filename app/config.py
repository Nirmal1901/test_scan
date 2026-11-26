import os
import re

# Allow-list of characters permitted in a single path component. Spaces are
# allowed (uploaded filenames may contain them); path separators, NUL bytes and
# control characters are not.
_SAFE_COMPONENT_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._\- ]*\Z")

def _safe_join(base, name, label):
    """Join a single, literal path component onto base, refusing traversal."""
    name = name or ""
    # Explicit separator rejection: a literal check, not just implied by the
    # allow-list regex below.
    if os.sep in name or (os.altsep and os.altsep in name):
        raise ValueError("unsafe path component for " + label)
    # Allow-list gate: reject empty names, "." / "..", absolute paths and any
    # component containing a path separator or other unexpected character.
    if not _SAFE_COMPONENT_RE.fullmatch(name):
        raise ValueError("unsafe path component for " + label)
    # Second gate: the name must be a bare basename (no separators, no "..").
    if name != os.path.basename(name):
        raise ValueError("unsafe path component for " + label)
    # Reduce to a single literal component before joining, so the join below
    # can never be influenced by anything but a bare filename.
    name = os.path.basename(name)
    if not name or name in (".", ".."):
        raise ValueError("unsafe path component for " + label)
    base = os.path.abspath(base)
    # Canonicalize (resolving symlinks) before the containment check so a
    # symlink inside base cannot be used to escape it. Compare against the
    # canonicalized base too, otherwise a symlinked base (e.g. macOS /var ->
    # /private/var) would fail the containment check for every name.
    real_base = os.path.realpath(base)
    candidate = os.path.realpath(os.path.join(base, name))
    try:
        contained = os.path.commonpath([candidate, real_base]) == real_base
    except ValueError:
        contained = False
    if not contained:
        raise ValueError("unsafe path component for " + label)
    # Return the plain (non-symlink-resolved) join so callers get the path they
    # asked for; containment was already proven above. The component is rebuilt
    # from its basename here so the join can only ever append a bare filename.
    return os.path.join(base, os.path.basename(name))


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
