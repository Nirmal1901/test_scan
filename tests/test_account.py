import json
import os

import pytest

from app.account import _prefs_path


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


def test_prefs_preserve_nested_values(client, login):
    login("buyer@test.local", "buyer-pass-1")
    prefs = {
        "theme": "dark",
        "page_size": 25,
        "filters": {"tags": ["gift", "home"], "min_price": 4.5},
        "notify": True,
        "note": None,
    }
    resp = client.put("/account/prefs", json=prefs)
    assert resp.status_code == 200
    assert resp.get_json() == prefs
    assert client.get("/account/prefs").get_json() == prefs


def test_prefs_are_per_user(client, login):
    login("buyer@test.local", "buyer-pass-1")
    client.put("/account/prefs", json={"theme": "dark"})
    client.post("/auth/logout")
    login("ops@test.local", "ops-pass-1")
    assert client.get("/account/prefs").get_json() == {}
    client.post("/auth/logout")
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/account/prefs").get_json() == {"theme": "dark"}


def test_prefs_are_persisted_as_json_in_prefs_dir(app, client, login):
    user = login("buyer@test.local", "buyer-pass-1")
    prefs = {"theme": "dark", "page_size": 25}
    client.put("/account/prefs", json=prefs)
    stored = os.listdir(app.config["PREFS_DIR"])
    assert len(stored) == 1
    with open(os.path.join(app.config["PREFS_DIR"], stored[0])) as fh:
        # json.load succeeds only because prefs are written as JSON, not pickle
        assert json.load(fh) == prefs
    assert str(user["id"]) in stored[0]


def test_put_prefs_without_body_stores_empty_dict(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.put("/account/prefs")
    assert resp.status_code == 200
    assert resp.get_json() == {}
    assert client.get("/account/prefs").get_json() == {}


def test_prefs_path_stays_inside_prefs_dir(app):
    with app.test_request_context():
        path = _prefs_path(7)
        assert os.path.basename(path).startswith("7.")
        assert os.path.dirname(path) == app.config["PREFS_DIR"]
        for bad in ("../evil", "..", "3/4", "abc", ""):
            with pytest.raises(ValueError):
                _prefs_path(bad)
