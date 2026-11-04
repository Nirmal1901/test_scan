import subprocess

import requests


class _Done:
    returncode = 0
    stdout = "1 packets transmitted"


class _Reply:
    status_code = 200
    text = "hello from upstream"


def test_ping_returns_output(client, login, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Done())
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/ping?host=127.0.0.1")
    assert resp.status_code == 200
    assert resp.get_json()["exit"] == 0


def test_calc_basic_math(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/calc", json={"expr": "2+3*4"})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 14


def test_calc_requires_login(client):
    assert client.post("/tools/calc", json={"expr": "1+1"}).status_code == 401


def test_fetch_returns_upstream_body(client, login, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Reply())
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/fetch?url=https://example.com/status")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": 200, "body": "hello from upstream"}


def test_import_config_parses_yaml(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post(
        "/tools/import-config", data="theme: dark\nsize: 12\n", content_type="text/yaml"
    )
    assert resp.status_code == 200
    assert resp.get_json()["config"] == {"theme": "dark", "size": 12}


def test_calc_supports_arithmetic_operators(client, login):
    login("buyer@test.local", "buyer-pass-1")
    cases = [
        ("1+1", 2),
        ("-(2+3)*4", -20),
        ("(1+2)*(3+4)", 21),
        ("7//2", 3),
        ("7%3", 1),
        ("2**10", 1024),
        ("7/2", 3.5),
        ("1.5+2.25", 3.75),
        ("  5 - 8  ", -3),
    ]
    for expr, expected in cases:
        resp = client.post("/tools/calc", json={"expr": expr})
        assert resp.status_code == 200, expr
        assert resp.get_json()["result"] == expected, expr


def test_calc_reports_bad_input_as_400(client, login):
    login("buyer@test.local", "buyer-pass-1")
    for body in ({"expr": "hello"}, {"expr": "1+"}, {"expr": "1/0"}, {"expr": ""}, {}, {"expr": True}):
        assert client.post("/tools/calc", json=body).status_code == 400, body


def test_import_config_preserves_nested_structure(client, login):
    login("buyer@test.local", "buyer-pass-1")
    body = "service:\n  name: shopdesk\n  replicas: 3\nfeatures:\n  - export\n  - upload\n"
    resp = client.post("/tools/import-config", data=body, content_type="text/yaml")
    assert resp.status_code == 200
    assert resp.get_json()["config"] == {
        "service": {"name": "shopdesk", "replicas": 3},
        "features": ["export", "upload"],
    }


def test_import_config_accepts_empty_document(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/import-config", data="", content_type="text/yaml")
    assert resp.status_code == 200
    assert resp.get_json()["config"] is None


def test_import_config_requires_login(client):
    assert client.post("/tools/import-config", data="a: 1\n").status_code == 401


def test_ping_uses_default_host_and_returns_output(client, login, monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return _Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/ping")
    assert resp.status_code == 200
    assert seen["cmd"] == "ping -c 1 127.0.0.1"
    assert seen["kwargs"]["timeout"] == 10
    assert resp.get_json() == {"exit": 0, "output": "1 packets transmitted"}


def test_fetch_calls_the_requested_url(client, login, monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        seen["kwargs"] = kwargs
        return _Reply()

    monkeypatch.setattr(requests, "get", fake_get)
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/fetch", query_string={"url": "https://example.com/health"})
    assert resp.status_code == 200
    assert seen["url"] == "https://example.com/health"
    assert resp.get_json()["body"] == "hello from upstream"
