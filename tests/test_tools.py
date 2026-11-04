import os
import subprocess

import pytest
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


def test_ping_defaults_to_loopback(client, login, monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        return _Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/ping")
    assert resp.status_code == 200
    assert "127.0.0.1" in str(calls["cmd"])
    assert resp.get_json() == {"exit": 0, "output": "1 packets transmitted"}


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2+3*4", 14),
        ("10/4", 2.5),
        ("7-9", -2),
        ("2**10", 1024),
        ("9//2", 4),
        ("7%3", 1),
        ("-(3+4)", -7),
        ("+5", 5),
        ("1.5*2", 3.0),
        ("(1+2)*(3+4)", 21),
    ],
)
def test_calc_supports_arithmetic(client, login, expr, expected):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/calc", json={"expr": expr})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["result"] == pytest.approx(expected)


@pytest.mark.parametrize(
    "expr",
    [
        "",
        "hello",
        "1+",
        "os.system('id')",
        "__import__('os').popen('id').read()",
        "print(1)",
        "[1, 2]",
        "True",
    ],
)
def test_calc_rejects_non_arithmetic_input(client, login, expr):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/calc", json={"expr": expr})
    assert resp.status_code == 400, expr
    assert "result" not in resp.get_json()


def test_calc_without_expr_is_rejected(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.post("/tools/calc", json={}).status_code == 400


def test_import_config_handles_nested_yaml(client, login):
    body = "service:\n  name: shopdesk\n  debug: false\n  ports:\n    - 5000\n    - 5001\n"
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/import-config", data=body, content_type="text/yaml")
    assert resp.status_code == 200
    assert resp.get_json()["config"] == {
        "service": {"name": "shopdesk", "debug": False, "ports": [5000, 5001]}
    }


def test_import_config_empty_body_returns_null(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/import-config", data="", content_type="text/yaml")
    assert resp.status_code == 200
    assert resp.get_json()["config"] is None


def test_import_config_rejects_python_object_tags(client, login, tmp_path):
    marker = tmp_path / "pwned.txt"
    body = "!!python/object/apply:os.system ['touch %s']\n" % marker
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/import-config", data=body, content_type="text/yaml")
    assert resp.status_code >= 400
    assert "config" not in (resp.get_json() or {})
    assert not os.path.exists(marker)


def test_import_config_requires_login(client):
    assert client.post("/tools/import-config", data="a: 1\n").status_code == 401
