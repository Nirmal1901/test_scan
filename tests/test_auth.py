import hashlib

import pytest

from app.db import get_db


def test_register_then_login(client):
    resp = client.post(
        "/auth/register",
        json={"email": "new@test.local", "name": "New", "password": "pw-12345"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["role"] == "customer"
    resp = client.post("/auth/login", json={"email": "new@test.local", "password": "pw-12345"})
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "new@test.local"


def test_register_duplicate_email(client):
    resp = client.post("/auth/register", json={"email": "buyer@test.local", "password": "x1"})
    assert resp.status_code == 409


def test_login_wrong_password(client):
    resp = client.post("/auth/login", json={"email": "buyer@test.local", "password": "nope"})
    assert resp.status_code == 401


def test_me_requires_login(client, login):
    assert client.get("/auth/me").status_code == 401
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "buyer@test.local"


def test_logout(client, login):
    login("buyer@test.local", "buyer-pass-1")
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401


def test_password_reset_flow(app, client):
    client.post("/auth/reset/request", json={"email": "buyer@test.local"})
    with app.app_context():
        code = get_db().execute(
            "SELECT reset_code FROM users WHERE email = ?", ("buyer@test.local",)
        ).fetchone()[0]
    resp = client.post(
        "/auth/reset/confirm",
        json={"email": "buyer@test.local", "code": code, "new_password": "fresh-pass-9"},
    )
    assert resp.status_code == 200
    resp = client.post(
        "/auth/login", json={"email": "buyer@test.local", "password": "fresh-pass-9"}
    )
    assert resp.status_code == 200


def test_reset_with_wrong_code(client):
    client.post("/auth/reset/request", json={"email": "buyer@test.local"})
    resp = client.post(
        "/auth/reset/confirm",
        json={"email": "buyer@test.local", "code": "000000", "new_password": "x-pass-1"},
    )
    assert resp.status_code == 400


def test_continue_redirects_to_local_path(client):
    resp = client.get("/auth/continue?next=/catalog/search")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/catalog/search")


def test_register_stores_pbkdf2_hash(app, client):
    resp = client.post(
        "/auth/register",
        json={"email": "hashed@test.local", "name": "Hashed", "password": "pw-hashed-1"},
    )
    assert resp.status_code == 201
    with app.app_context():
        stored = get_db().execute(
            "SELECT password FROM users WHERE email = ?", ("hashed@test.local",)
        ).fetchone()["password"]
    assert stored.startswith("pbkdf2_sha256$")
    assert "pw-hashed-1" not in stored


def test_login_accepts_legacy_md5_row(app, client):
    legacy = hashlib.md5(b"old-pass-7").hexdigest()
    with app.app_context():
        conn = get_db()
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("legacy@test.local", "Legacy", legacy, "customer"),
        )
        conn.commit()
    resp = client.post(
        "/auth/login", json={"email": "legacy@test.local", "password": "old-pass-7"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "legacy@test.local"
    assert client.get("/auth/me").get_json()["email"] == "legacy@test.local"


def test_legacy_md5_row_rejects_wrong_password(app, client):
    legacy = hashlib.md5(b"old-pass-7").hexdigest()
    with app.app_context():
        conn = get_db()
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("legacy2@test.local", "Legacy", legacy, "customer"),
        )
        conn.commit()
    resp = client.post(
        "/auth/login", json={"email": "legacy2@test.local", "password": "nope-pass"}
    )
    assert resp.status_code == 401


def test_register_normalizes_email_and_defaults_name(client):
    resp = client.post(
        "/auth/register", json={"email": "  Mixed@Test.Local  ", "password": "pw-mixed-1"}
    )
    assert resp.status_code == 201
    assert resp.get_json()["email"] == "mixed@test.local"
    resp = client.post(
        "/auth/login", json={"email": "mixed@test.local", "password": "pw-mixed-1"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "mixed"


def test_register_requires_email_and_password(client):
    assert client.post("/auth/register", json={"email": "no-pw@test.local"}).status_code == 400
    assert client.post("/auth/register", json={"password": "pw-only-1"}).status_code == 400
    assert client.post("/auth/register", json={}).status_code == 400


def test_me_returns_expected_fields(client, login):
    login("ops@test.local", "ops-pass-1")
    body = client.get("/auth/me").get_json()
    assert set(body) == {"id", "email", "name", "role"}
    assert body["email"] == "ops@test.local"
    assert body["role"] == "admin"


def test_logout_reports_ok(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/auth/me"),
        ("get", "/account/prefs"),
        ("put", "/account/prefs"),
        ("get", "/account/users"),
        ("post", "/orders"),
        ("get", "/orders/user/1"),
        ("get", "/orders/export.csv"),
        ("post", "/files/upload"),
        ("get", "/files/download?name=hello.txt"),
        ("get", "/tools/ping"),
        ("post", "/tools/calc"),
        ("get", "/tools/fetch?url=https://example.com/status"),
        ("post", "/tools/import-config"),
    ],
)
def test_login_required_gate_guards_every_caller(client, method, path):
    resp = getattr(client, method)(path)
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "login required"
