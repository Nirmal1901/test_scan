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
