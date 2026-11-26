import json
import os
import pickle

import pytest

from app.account import _prefs_path


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


# --- Post-fix regression guards: prefs must stay plain JSON in "<uid>.pkl" ---


def test_prefs_file_is_plain_json_with_no_pickle_opcodes(app, client, login):
    # The fix swapped pickle for json while keeping the legacy ".pkl" filename.
    # Stored prefs must therefore be readable by json.load and must not contain
    # any pickle opcode bytes (a pickle stream would start with b"\x80").
    user = login("buyer@test.local", "buyer-pass-1")
    prefs = {"theme": "dark", "page_size": 25, "nested": {"a": [1, 2, 3]}}
    assert client.put("/account/prefs", json=prefs).status_code == 200

    path = os.path.join(app.config["PREFS_DIR"], "%d.pkl" % user["id"])
    with open(path, "rb") as fh:
        raw = fh.read()

    # Plain JSON, not a pickle stream.
    assert not raw.startswith(b"\x80")
    assert b"\x80" not in raw
    assert json.loads(raw.decode("utf-8")) == prefs
    # A pickle stream would not parse as JSON; prove it is not one.
    with pytest.raises(Exception):
        pickle.loads(raw)


def test_prefs_roundtrip_preserves_json_types(app, client, login):
    # Values must survive the JSON roundtrip with their types intact (ints stay
    # ints, floats stay floats, booleans stay booleans, nulls stay null).
    login("buyer@test.local", "buyer-pass-1")
    prefs = {
        "page_size": 25,
        "ratio": 0.5,
        "compact": True,
        "archived": False,
        "nickname": None,
        "tags": ["a", "b"],
    }
    assert client.put("/account/prefs", json=prefs).status_code == 200
    got = client.get("/account/prefs").get_json()
    assert got == prefs
    assert isinstance(got["page_size"], int)
    assert isinstance(got["ratio"], float)
    assert got["compact"] is True
    assert got["archived"] is False
    assert got["nickname"] is None


def test_prefs_path_is_numeric_pkl_inside_prefs_dir(app):
    # _prefs_path() must keep producing "<PREFS_DIR>/<uid>.pkl" for real uids.
    with app.app_context():
        for uid in (1, 42, 999999):
            path = _prefs_path(uid)
            assert path == os.path.join(app.config["PREFS_DIR"], "%d.pkl" % uid)
            assert os.path.dirname(path) == app.config["PREFS_DIR"]
            assert path.endswith(".pkl")


def test_prefs_path_accepts_numeric_string_uid(app):
    # Session uids may arrive as strings; int() coercion must still work.
    with app.app_context():
        assert _prefs_path("7") == os.path.join(app.config["PREFS_DIR"], "7.pkl")


def test_prefs_path_rejects_non_numeric_uid(app):
    # The uid is coerced with int(), so anything non-numeric is refused before
    # it can reach the filesystem.
    with app.app_context():
        for bad in ("../1", "1/2", "abc", "", None):
            with pytest.raises((ValueError, TypeError)):
                _prefs_path(bad)


def test_prefs_put_then_get_after_relogin(client, login):
    # Prefs are keyed by uid, so they must survive a logout/login cycle.
    login("buyer@test.local", "buyer-pass-1")
    assert client.put("/account/prefs", json={"theme": "dark"}).status_code == 200
    client.post("/auth/logout")
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/account/prefs").get_json() == {"theme": "dark"}


def test_user_directory_still_returns_seeded_rows_after_fix(client, login):
    # /account/users is on the same blueprint as the changed prefs code; it must
    # keep returning the seeded users with their roles.
    login("ops@test.local", "ops-pass-1")
    rows = client.get("/account/users").get_json()
    by_email = {u["email"]: u for u in rows}
    assert by_email["ops@test.local"]["role"] == "admin"
    assert by_email["buyer@test.local"]["role"] == "customer"
    assert by_email["buyer@test.local"]["name"] == "Buyer"
