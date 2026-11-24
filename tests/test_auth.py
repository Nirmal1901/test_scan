import hashlib

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


def test_register_normalizes_email_and_defaults_name(client):
    resp = client.post(
        "/auth/register",
        json={"email": "  Mixed.Case@Test.Local ", "password": "pw-12345"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["email"] == "mixed.case@test.local"
    # Name defaults to the local part of the (normalized) email.
    assert client.post(
        "/auth/login", json={"email": "mixed.case@test.local", "password": "pw-12345"}
    ).status_code == 200
    assert client.get("/auth/me").get_json()["name"] == "mixed.case"


def test_register_stores_a_hashed_password(client, app):
    client.post("/auth/register", json={"email": "hash@test.local", "password": "pw-12345"})
    with app.app_context():
        stored = get_db().execute(
            "SELECT password FROM users WHERE email = ?", ("hash@test.local",)
        ).fetchone()[0]
    assert stored != "pw-12345"
    assert "pw-12345" not in stored


def test_register_requires_email_and_password(client):
    assert client.post("/auth/register", json={"email": "a@test.local"}).status_code == 400
    assert client.post("/auth/register", json={"password": "pw-12345"}).status_code == 400


def test_login_returns_profile_and_sets_session(client, login):
    body = login("buyer@test.local", "buyer-pass-1")
    assert body["email"] == "buyer@test.local"
    assert body["name"] == "Buyer"
    assert body["role"] == "customer"
    assert isinstance(body["id"], int)
    # Session established by login is what /auth/me reads back.
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.get_json() == {
        "id": body["id"],
        "email": "buyer@test.local",
        "name": "Buyer",
        "role": "customer",
    }


def test_login_does_not_leak_password_hash(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert "password" not in client.get("/auth/me").get_json()


def test_login_accepts_legacy_md5_row(app, client):
    # Rows created before the hashing change still hold a bare MD5 digest and
    # must keep logging in.
    legacy = hashlib.md5(b"legacy-pass-1").hexdigest()
    with app.app_context():
        conn = get_db()
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("legacy@test.local", "Legacy", legacy, "customer"),
        )
        conn.commit()
    resp = client.post(
        "/auth/login", json={"email": "legacy@test.local", "password": "legacy-pass-1"}
    )
    assert resp.status_code == 200
    assert client.get("/auth/me").get_json()["email"] == "legacy@test.local"


def test_login_unknown_email(client):
    resp = client.post("/auth/login", json={"email": "ghost@test.local", "password": "x"})
    assert resp.status_code == 401


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
