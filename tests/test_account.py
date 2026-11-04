import json
import os

from app.account import _prefs_path
from app.config import ADMIN_EMAIL


def test_prefs_roundtrip(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/account/prefs").get_json() == {}
    resp = client.put("/account/prefs", json={"theme": "dark", "page_size": 25})
    assert resp.status_code == 200
    assert client.get("/account/prefs").get_json() == {"theme": "dark", "page_size": 25}


def test_prefs_require_login(client):
    assert client.get("/account/prefs").status_code == 401


def test_user_directory_for_admin(client, login):
    assert client.get("/account/users").status_code == 401
    login("ops@test.local", "ops-pass-1")
    resp = client.get("/account/users")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.get_json()]
    assert "buyer@test.local" in emails


def test_prefs_isolated_between_users(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.put("/account/prefs", json={"theme": "dark"}).status_code == 200
    client.post("/auth/logout")

    login("ops@test.local", "ops-pass-1")
    assert client.get("/account/prefs").get_json() == {}
    assert client.put("/account/prefs", json={"theme": "light"}).status_code == 200
    assert client.get("/account/prefs").get_json() == {"theme": "light"}
    client.post("/auth/logout")

    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/account/prefs").get_json() == {"theme": "dark"}


def test_prefs_put_replaces_previous_document(client, login):
    login("buyer@test.local", "buyer-pass-1")
    client.put("/account/prefs", json={"theme": "dark", "page_size": 25})
    resp = client.put("/account/prefs", json={"theme": "light"})
    assert resp.status_code == 200
    assert resp.get_json() == {"theme": "light"}
    assert client.get("/account/prefs").get_json() == {"theme": "light"}


def test_prefs_supports_nested_json_values(client, login):
    login("buyer@test.local", "buyer-pass-1")
    prefs = {
        "theme": "dark",
        "columns": ["id", "total"],
        "filters": {"min": 1.5, "vip": True, "note": None},
        "page_size": 25,
    }
    assert client.put("/account/prefs", json=prefs).get_json() == prefs
    assert client.get("/account/prefs").get_json() == prefs


def test_prefs_survive_logout_and_login(client, login):
    login("buyer@test.local", "buyer-pass-1")
    client.put("/account/prefs", json={"page_size": 50})
    client.post("/auth/logout")
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/account/prefs").get_json() == {"page_size": 50}


def test_prefs_write_requires_login(client):
    assert client.put("/account/prefs", json={"theme": "dark"}).status_code == 401


def test_prefs_are_persisted_as_plain_json(app, client, login):
    user = login("buyer@test.local", "buyer-pass-1")
    prefs = {"theme": "dark", "page_size": 25}
    assert client.put("/account/prefs", json=prefs).status_code == 200

    with app.app_context():
        path = _prefs_path(user["id"])
        assert os.path.dirname(path) == os.path.realpath(app.config["PREFS_DIR"])
        with open(path, "r", encoding="utf-8") as fh:
            assert json.load(fh) == prefs


def test_prefs_serves_json_document_written_outside_the_endpoint(app, client, login):
    user = login("buyer@test.local", "buyer-pass-1")
    with app.app_context():
        path = _prefs_path(user["id"])
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"theme": "solarized", "page_size": 100}, fh)

    resp = client.get("/account/prefs")
    assert resp.status_code == 200
    assert resp.get_json() == {"theme": "solarized", "page_size": 100}


def test_prefs_path_requires_numeric_user_id(app):
    with app.app_context():
        assert _prefs_path(7).endswith(".json")
        assert _prefs_path(None) is None
        assert _prefs_path("not-a-number") is None


def test_prefs_defaults_to_an_empty_document_for_a_fresh_account(client, login):
    login("ops@test.local", "ops-pass-1")

    resp = client.get("/account/prefs")
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_prefs_put_without_a_body_stores_an_empty_document(client, login):
    login("buyer@test.local", "buyer-pass-1")

    resp = client.put("/account/prefs")
    assert resp.status_code == 200
    assert resp.get_json() == {}
    assert client.get("/account/prefs").get_json() == {}


def test_prefs_file_is_named_after_the_user_id(app, client, login):
    user = login("buyer@test.local", "buyer-pass-1")
    assert client.put("/account/prefs", json={"theme": "dark"}).status_code == 200

    with app.app_context():
        expected = os.path.join(
            os.path.realpath(app.config["PREFS_DIR"]), "%d.json" % user["id"]
        )
        assert _prefs_path(user["id"]) == expected
    assert os.path.isfile(expected)


def test_prefs_path_accepts_numeric_strings_and_large_ids(app):
    with app.app_context():
        base = os.path.realpath(app.config["PREFS_DIR"])
        assert _prefs_path("7") == _prefs_path(7) == os.path.join(base, "7.json")
        assert _prefs_path(2**63 - 1) == os.path.join(base, "%d.json" % (2**63 - 1))


def test_prefs_served_per_user_without_leaking_other_documents(client, login):
    user = login("buyer@test.local", "buyer-pass-1")
    client.put("/account/prefs", json={"theme": "dark"})

    ops = login("ops@test.local", "ops-pass-1")
    assert ops["id"] != user["id"]
    assert client.get("/account/prefs").get_json() == {}


def test_user_directory_exposes_profile_fields_for_admin(client, login):
    login("ops@test.local", "ops-pass-1")
    rows = client.get("/account/users").get_json()

    by_email = {row["email"]: row for row in rows}
    buyer = by_email["buyer@test.local"]
    assert buyer["name"] == "Buyer"
    assert buyer["role"] == "customer"
    assert isinstance(buyer["id"], int)
    assert [row["id"] for row in rows] == sorted(row["id"] for row in rows)


def test_user_directory_includes_the_seeded_admin(client, login):
    login("ops@test.local", "ops-pass-1")
    roles = {row["role"] for row in client.get("/account/users").get_json()}
    assert "admin" in roles


def test_user_directory_still_lists_every_account_with_profile_fields(client, login):
    login("ops@test.local", "ops-pass-1")
    rows = client.get("/account/users").get_json()

    emails = {row["email"] for row in rows}
    assert {"ops@test.local", "buyer@test.local", ADMIN_EMAIL} <= emails
    for row in rows:
        assert {"id", "email", "name", "role"} <= set(row)
        assert isinstance(row["id"], int)
        assert isinstance(row["name"], str) and row["name"]
