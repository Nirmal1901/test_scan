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


def test_prefs_roundtrip_nested_dict(client, login):
    login("buyer@test.local", "buyer-pass-1")
    prefs = {
        "theme": "dark",
        "notifications": {"email": True, "sms": False, "digest": {"hour": 9, "tz": "UTC"}},
        "recent": [1, 2, 3],
    }
    resp = client.put("/account/prefs", json=prefs)
    assert resp.status_code == 200
    assert resp.get_json() == prefs
    assert client.get("/account/prefs").get_json() == prefs


def test_put_prefs_returns_the_stored_document(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.put("/account/prefs", json={"lang": "en"})
    assert resp.status_code == 200
    assert resp.get_json() == {"lang": "en"}


def test_prefs_are_stored_as_plain_json(app, client, login):
    # The prefs file must be readable JSON, not a pickle blob.
    login("buyer@test.local", "buyer-pass-1")
    client.put("/account/prefs", json={"theme": "dark"})
    path = os.path.join(app.config["PREFS_DIR"], "2.pkl")
    assert os.path.isfile(path)
    with open(path, "r", encoding="utf-8") as fh:
        assert json.load(fh) == {"theme": "dark"}


def test_prefs_file_with_pickle_payload_is_not_executed(app, client, login):
    # A pre-existing pickle payload in the prefs file must never be unpickled:
    # GET returns an empty document and the payload's side effect never fires.
    login("buyer@test.local", "buyer-pass-1")
    marker = os.path.join(app.config["PREFS_DIR"], "pwned.marker")

    class _Boom:
        def __reduce__(self):
            return (open, (marker, "w"))

    path = os.path.join(app.config["PREFS_DIR"], "2.pkl")
    with open(path, "wb") as fh:
        pickle.dump(_Boom(), fh)

    resp = client.get("/account/prefs")
    assert resp.status_code == 200
    assert resp.get_json() == {}
    assert not os.path.exists(marker)


def test_prefs_path_uses_user_id_file_name(app):
    with app.app_context():
        assert _prefs_path(7) == os.path.join(app.config["PREFS_DIR"], "7.pkl")
        assert _prefs_path("7") == os.path.join(app.config["PREFS_DIR"], "7.pkl")


@pytest.mark.parametrize("bad", ["../../etc/passwd", "../7", "7/../../x", "abc", None])
def test_prefs_path_rejects_traversal_and_non_numeric_ids(app, bad):
    with app.app_context():
        with pytest.raises(ValueError):
            _prefs_path(bad)


def test_prefs_require_login(client):
    assert client.get("/account/prefs").status_code == 401
    assert client.put("/account/prefs", json={"theme": "dark"}).status_code == 401


def test_user_directory_for_admin(client, login):
    assert client.get("/account/users").status_code == 401
    login("ops@test.local", "ops-pass-1")
    resp = client.get("/account/users")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.get_json()]
    assert "buyer@test.local" in emails
