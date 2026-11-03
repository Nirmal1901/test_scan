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
