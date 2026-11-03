def _notebook(client):
    return client.get("/catalog/search?q=Notebook").get_json()[0]


def test_create_order_computes_total(client, login):
    user = login("buyer@test.local", "buyer-pass-1")
    product = _notebook(client)
    resp = client.post("/orders", json={"product_id": product["id"], "qty": 2, "note": "gift"})
    assert resp.status_code == 201
    assert resp.get_json()["total"] == 9.0
    rows = client.get(f"/orders/user/{user['id']}").get_json()
    assert len(rows) == 1
    assert rows[0]["qty"] == 2


def test_order_requires_login(client):
    assert client.post("/orders", json={"product_id": 1}).status_code == 401


def test_order_unknown_product(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.post("/orders", json={"product_id": 9999}).status_code == 404


def test_order_detail(client, login):
    login("buyer@test.local", "buyer-pass-1")
    product = _notebook(client)
    oid = client.post("/orders", json={"product_id": product["id"]}).get_json()["id"]
    resp = client.get(f"/orders/{oid}")
    assert resp.status_code == 200
    assert resp.get_json()["product_id"] == product["id"]
    assert client.get("/orders/9999").status_code == 404


def test_export_csv(client, login):
    login("buyer@test.local", "buyer-pass-1")
    product = _notebook(client)
    client.post("/orders", json={"product_id": product["id"], "qty": 3})
    resp = client.get("/orders/export.csv")
    assert resp.status_code == 200
    lines = resp.get_data(as_text=True).strip().splitlines()
    assert lines[0] == "id,product_id,qty,total,status,note"
    assert len(lines) == 2
