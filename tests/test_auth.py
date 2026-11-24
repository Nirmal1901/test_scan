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


def test_register_response_shape_and_defaults(client):
    resp = client.post(
        "/auth/register",
        json={"email": "  Mixed@Case.Local ", "password": "pw-12345"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert set(body) == {"id", "email", "role"}
    assert body["email"] == "mixed@case.local"
    assert body["role"] == "customer"
    assert isinstance(body["id"], int)


def test_register_stores_hashed_password(app, client):
    client.post("/auth/register", json={"email": "hash@test.local", "password": "pw-12345"})
    with app.app_context():
        stored = get_db().execute(
            "SELECT password FROM users WHERE email = ?", ("hash@test.local",)
        ).fetchone()[0]
    assert stored != "pw-12345"


def test_register_requires_email_and_password(client):
    assert client.post("/auth/register", json={"email": "x@test.local"}).status_code == 400
    assert client.post("/auth/register", json={"password": "pw"}).status_code == 400


def test_login_establishes_session_for_protected_routes(client):
    resp = client.post(
        "/auth/login", json={"email": "buyer@test.local", "password": "buyer-pass-1"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"id", "email", "name", "role"}
    assert body["role"] == "customer"
    # Session is what every authenticated route depends on.
    assert client.get("/auth/me").status_code == 200
    assert client.get("/account/prefs").status_code == 200
    assert client.get("/orders/export.csv").status_code == 200


def test_login_admin_role_is_exposed(client, login):
    body = login("ops@test.local", "ops-pass-1")
    assert body["role"] == "admin"
    assert client.get("/account/users").status_code == 200


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


def test_continue_defaults_to_root(client):
    resp = client.get("/auth/continue")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_continue_does_not_redirect_off_site(client):
    resp = client.get("/auth/continue?next=https://evil.example.com/steal")
    assert resp.status_code == 302
    assert "evil.example.com" not in resp.headers["Location"]
