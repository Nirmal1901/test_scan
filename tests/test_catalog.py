def test_search_by_name(client):
    resp = client.get("/catalog/search?q=lamp")
    names = [p["name"] for p in resp.get_json()]
    assert names == ["Desk Lamp"]


def test_search_by_category(client):
    resp = client.get("/catalog/search?category=electronics")
    assert len(resp.get_json()) == 3


def test_search_without_filters_returns_all(client):
    assert len(client.get("/catalog/search").get_json()) == 6


def test_product_detail_and_missing(client):
    pid = client.get("/catalog/search?q=Notebook").get_json()[0]["id"]
    resp = client.get(f"/catalog/products/{pid}")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Notebook A5"
    assert client.get("/catalog/products/9999").status_code == 404


def test_product_card_contains_name(client):
    pid = client.get("/catalog/search?q=Lamp").get_json()[0]["id"]
    resp = client.get(f"/catalog/products/{pid}/card")
    assert resp.status_code == 200
    assert "Desk Lamp" in resp.get_data(as_text=True)


def test_create_product_admin_only(client, login):
    body = {"name": "Stapler", "price": 6.25, "category": "stationery"}
    assert client.post("/catalog/products", json=body).status_code == 401
    login("buyer@test.local", "buyer-pass-1")
    assert client.post("/catalog/products", json=body).status_code == 403
    client.post("/auth/logout")
    login("ops@test.local", "ops-pass-1")
    resp = client.post("/catalog/products", json=body)
    assert resp.status_code == 201
    assert len(client.get("/catalog/search?q=Stapler").get_json()) == 1
