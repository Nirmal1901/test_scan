import json
import os


def test_prefs_roundtrip(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/account/prefs").get_json() == {}
    resp = client.put("/account/prefs", json={"theme": "dark", "page_size": 25})
    assert resp.status_code == 200
    assert client.get("/account/prefs").get_json() == {"theme": "dark", "page_size": 25}


def test_prefs_put_echoes_body_and_overwrites(client, login):
    login("buyer@test.local", "buyer-pass-1")
    first = client.put("/account/prefs", json={"theme": "dark"})
    assert first.status_code == 200
    assert first.get_json() == {"theme": "dark"}
    second = client.put("/account/prefs", json={"theme": "light", "lang": "en"})
    assert second.status_code == 200
    assert second.get_json() == {"theme": "light", "lang": "en"}
    # The second PUT replaces the stored document rather than merging it.
    assert client.get("/account/prefs").get_json() == {"theme": "light", "lang": "en"}


def test_prefs_put_without_json_body_stores_empty_object(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.put("/account/prefs", data="not json", content_type="text/plain")
    assert resp.status_code == 200
    assert resp.get_json() == {}
    assert client.get("/account/prefs").get_json() == {}


def test_prefs_are_stored_as_json_under_prefs_dir(app, client, login):
    # The prefs file is plain JSON named "<uid>.pkl" inside PREFS_DIR; the
    # pickle roundtrip contract is load-bearing for stored prefs.
    user = login("buyer@test.local", "buyer-pass-1")
    client.put("/account/prefs", json={"theme": "dark"})
    path = os.path.join(app.config["PREFS_DIR"], "%d.pkl" % user["id"])
    assert os.path.isfile(path)
    with open(path, "r", encoding="utf-8") as fh:
        assert json.load(fh) == {"theme": "dark"}


def test_prefs_are_per_user(app, client, login):
    buyer = login("buyer@test.local", "buyer-pass-1")
    client.put("/account/prefs", json={"theme": "dark"})
    client.post("/auth/logout")
    ops = login("ops@test.local", "ops-pass-1")
    assert ops["id"] != buyer["id"]
    # A different user must not see the buyer's prefs.
    assert client.get("/account/prefs").get_json() == {}
    client.put("/account/prefs", json={"theme": "light"})
    client.post("/auth/logout")
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/account/prefs").get_json() == {"theme": "dark"}
    # Both users' files live side by side in PREFS_DIR.
    stored = sorted(os.listdir(app.config["PREFS_DIR"]))
    assert stored == sorted(["%d.pkl" % buyer["id"], "%d.pkl" % ops["id"]])


def test_prefs_with_unreadable_file_returns_empty_object(app, client, login):
    # A corrupt/legacy prefs file must degrade to {} instead of a 500.
    user = login("buyer@test.local", "buyer-pass-1")
    path = os.path.join(app.config["PREFS_DIR"], "%d.pkl" % user["id"])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("not: valid: json")
    resp = client.get("/account/prefs")
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_prefs_put_requires_login(client):
    assert client.put("/account/prefs", json={"theme": "dark"}).status_code == 401


def test_user_directory_lists_seeded_users_without_breaking(client, login):
    login("ops@test.local", "ops-pass-1")
    resp = client.get("/account/users")
    assert resp.status_code == 200
    rows = resp.get_json()
    emails = [u["email"] for u in rows]
    assert {"ops@test.local", "buyer@test.local"} <= set(emails)
    # Rows come back ordered by id.
    assert [u["id"] for u in rows] == sorted(u["id"] for u in rows)
    for row in rows:
        assert set(row) >= {"id", "email", "name", "role"}
        assert row["role"] in ("admin", "customer")


def test_prefs_require_login(client):
    assert client.get("/account/prefs").status_code == 401


def test_user_directory_for_admin(client, login):
    assert client.get("/account/users").status_code == 401
    login("ops@test.local", "ops-pass-1")
    resp = client.get("/account/users")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.get_json()]
    assert "buyer@test.local" in emails
