import hashlib
import re

from app.db import get_db
from app.security import hash_password, new_reset_code, verify_password


def test_hash_password_is_not_a_bare_md5_digest():
    stored = hash_password("correct horse battery staple")
    assert not re.fullmatch(r"[0-9a-f]{32}", stored)
    assert stored != hashlib.md5(b"correct horse battery staple").hexdigest()


def test_hash_password_is_salted():
    # Two hashes of the same password must differ (random salt per hash).
    assert hash_password("same-pass-1") != hash_password("same-pass-1")


def test_verify_password_accepts_freshly_hashed_password():
    stored = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", stored) is True
    assert verify_password("wrong-pass", stored) is False


def test_verify_password_rejects_empty_stored_value():
    assert verify_password("anything", "") is False
    assert verify_password("anything", None) is False


def test_verify_password_accepts_legacy_md5_row():
    legacy = hashlib.md5(b"legacy-pass-1").hexdigest()
    assert verify_password("legacy-pass-1", legacy) is True
    assert verify_password("not-the-password", legacy) is False


def test_legacy_md5_user_can_still_log_in(app, client):
    # Rows created before the KDF switch must keep authenticating.
    legacy = hashlib.md5(b"old-pass-1").hexdigest()
    with app.app_context():
        conn = get_db()
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("legacy@test.local", "Legacy", legacy, "customer"),
        )
        conn.commit()
    resp = client.post("/auth/login", json={"email": "legacy@test.local", "password": "old-pass-1"})
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "legacy@test.local"
    assert client.get("/auth/me").get_json()["email"] == "legacy@test.local"


def test_new_reset_code_is_six_digits():
    for _ in range(20):
        code = new_reset_code()
        assert isinstance(code, str)
        assert re.fullmatch(r"\d{6}", code)
