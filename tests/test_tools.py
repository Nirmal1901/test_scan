import subprocess

import pytest
import requests

from app.tools import safe_eval


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


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2+3*4", 14),
        ("(2+3)*4", 20),
        ("10/4", 2.5),
        ("10//4", 2),
        ("10%3", 1),
        ("2**10", 1024),
        ("-5+2", -3),
        ("+7", 7),
        ("1.5*2", 3.0),
    ],
)
def test_calc_arithmetic_operators(client, login, expr, expected):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/calc", json={"expr": expr})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == expected


def test_calc_rejects_non_arithmetic_input(client, login):
    login("buyer@test.local", "buyer-pass-1")
    for expr in ("", "abc", "1/0", "True", "'text'"):
        resp = client.post("/tools/calc", json={"expr": expr})
        assert resp.status_code == 400, expr
        assert resp.get_json() == {"error": "invalid expression"}


def test_safe_eval_returns_numbers():
    assert safe_eval("2+3*4") == 14
    assert safe_eval("(1+2)*(3+4)") == 21


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


def test_import_config_parses_nested_yaml(client, login):
    login("buyer@test.local", "buyer-pass-1")
    body = (
        "service: shopdesk\n"
        "features:\n"
        "  - catalog\n"
        "  - orders\n"
        "limits:\n"
        "  page_size: 25\n"
        "  enabled: true\n"
    )
    resp = client.post("/tools/import-config", data=body, content_type="text/yaml")
    assert resp.status_code == 200
    assert resp.get_json()["config"] == {
        "service": "shopdesk",
        "features": ["catalog", "orders"],
        "limits": {"page_size": 25, "enabled": True},
    }


def test_import_config_requires_login(client):
    assert client.post("/tools/import-config", data="a: 1\n").status_code == 401
