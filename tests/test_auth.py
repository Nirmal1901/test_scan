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


def test_continue_redirects_to_root_by_default(client):
    resp = client.get("/auth/continue")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_register_stores_a_hashed_password(app, client):
    resp = client.post(
        "/auth/register", json={"email": "hashed@test.local", "password": "plain-pass-7"}
    )
    assert resp.status_code == 201

    with app.app_context():
        stored = get_db().execute(
            "SELECT password FROM users WHERE email = ?", ("hashed@test.local",)
        ).fetchone()["password"]
    assert stored != "plain-pass-7"
    assert stored.startswith("pbkdf2_sha256$")

    resp = client.post(
        "/auth/login", json={"email": "hashed@test.local", "password": "plain-pass-7"}
    )
    assert resp.status_code == 200


def test_register_normalizes_email_and_defaults_name(client):
    resp = client.post(
        "/auth/register", json={"email": "  Mixed.Case@Test.Local ", "password": "pw-abc-1"}
    )
    assert resp.status_code == 201
    assert resp.get_json()["email"] == "mixed.case@test.local"

    resp = client.post(
        "/auth/login", json={"email": "mixed.case@test.local", "password": "pw-abc-1"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "mixed.case"


def test_register_requires_email_and_password(client):
    assert client.post("/auth/register", json={"password": "pw-1"}).status_code == 400
    assert client.post("/auth/register", json={"email": "no-pw@test.local"}).status_code == 400
    assert client.post("/auth/register", json={}).status_code == 400


def test_login_returns_identity_and_unlocks_protected_endpoints(client):
    resp = client.post("/auth/login", json={"email": "buyer@test.local", "password": "buyer-pass-1"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) >= {"id", "email", "name", "role"}
    assert body["role"] == "customer"
    assert client.get("/auth/me").get_json()["id"] == body["id"]
    assert client.get("/account/prefs").status_code == 200


def test_legacy_bare_digest_row_must_reset_password(app, client):
    with app.app_context():
        conn = get_db()
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, 'customer')",
            ("legacy@test.local", "Legacy", "5f4dcc3b5aa765d61d8327deb882cf99"),
        )
        conn.commit()

    resp = client.post(
        "/auth/login", json={"email": "legacy@test.local", "password": "old-pass-1"}
    )
    assert resp.status_code == 401


def test_password_reset_replaces_hash_and_clears_code(app, client):
    client.post("/auth/reset/request", json={"email": "buyer@test.local"})
    with app.app_context():
        code = get_db().execute(
            "SELECT reset_code FROM users WHERE email = ?", ("buyer@test.local",)
        ).fetchone()["reset_code"]
    assert code is not None
    assert len(code) == 6 and code.isdigit()

    resp = client.post(
        "/auth/reset/confirm",
        json={"email": "buyer@test.local", "code": code, "new_password": "brand-new-3"},
    )
    assert resp.status_code == 200

    with app.app_context():
        row = get_db().execute(
            "SELECT password, reset_code FROM users WHERE email = ?", ("buyer@test.local",)
        ).fetchone()
    assert row["reset_code"] is None
    assert row["password"].startswith("pbkdf2_sha256$")
    assert row["password"] != "brand-new-3"

    assert (
        client.post(
            "/auth/login", json={"email": "buyer@test.local", "password": "buyer-pass-1"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "buyer@test.local", "password": "brand-new-3"}
        ).status_code
        == 200
    )


def test_reset_request_for_unknown_email_does_not_error(client):
    resp = client.post("/auth/reset/request", json={"email": "ghost@test.local"})
    assert resp.status_code == 200
    assert resp.get_json() == {"sent": True}


def test_me_returns_profile_without_password(client, login):
    login("buyer@test.local", "buyer-pass-1")
    body = client.get("/auth/me").get_json()
    assert body == {
        "id": body["id"],
        "email": "buyer@test.local",
        "name": "Buyer",
        "role": "customer",
    }


def test_login_unlocks_order_and_export_flows(client, login):
    # The password check is the gate for every protected endpoint; a session it
    # establishes must still carry through catalog -> order -> CSV export.
    login("buyer@test.local", "buyer-pass-1")
    product = client.get("/catalog/search?q=Notebook").get_json()[0]

    resp = client.post("/orders", json={"product_id": product["id"], "qty": 2, "note": "gift"})
    assert resp.status_code == 201
    assert resp.get_json()["total"] == 9.0

    lines = client.get("/orders/export.csv").get_data(as_text=True).strip().splitlines()
    assert lines[0] == "id,product_id,qty,total,status,note"
    assert lines[1].endswith(",gift")


def test_logout_after_hashed_login_locks_protected_endpoints(client, login):
    login("ops@test.local", "ops-pass-1")
    assert client.get("/account/users").status_code == 200

    assert client.post("/auth/logout").get_json() == {"ok": True}
    assert client.get("/account/users").status_code == 401
    assert client.get("/account/prefs").status_code == 401


def test_register_then_login_survives_repeated_sessions(client):
    client.post(
        "/auth/register", json={"email": "repeat@test.local", "password": "repeat-pass-1"}
    )
    for _ in range(2):
        assert (
            client.post(
                "/auth/login",
                json={"email": "repeat@test.local", "password": "repeat-pass-1"},
            ).status_code
            == 200
        )
        client.post("/auth/logout")
