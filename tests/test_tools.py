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


def test_ping_accepts_hostname_and_passes_it_as_argv(client, login, monkeypatch):
    seen = {}

    def _run(argv, **kwargs):
        seen["argv"] = argv
        return _Done()

    monkeypatch.setattr(subprocess, "run", _run)
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/ping?host=example.com")
    assert resp.status_code == 200
    assert seen["argv"] == ["ping", "-c", "1", "example.com"]


def test_ping_defaults_to_loopback(client, login, monkeypatch):
    seen = {}

    def _run(argv, **kwargs):
        seen["argv"] = argv
        return _Done()

    monkeypatch.setattr(subprocess, "run", _run)
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/tools/ping").status_code == 200
    assert seen["argv"][-1] == "127.0.0.1"


def test_ping_requires_login(client):
    assert client.get("/tools/ping?host=127.0.0.1").status_code == 401


def test_calc_basic_math(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/calc", json={"expr": "2+3*4"})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 14


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("1+1", 2),
        ("10-4", 6),
        ("7/2", 3.5),
        ("7//2", 3),
        ("7%3", 1),
        ("2**10", 1024),
        ("-5+2", -3),
        ("(1+2)*3", 9),
        ("1.5*2", 3.0),
    ],
)
def test_calc_supports_arithmetic_operators(client, login, expr, expected):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/calc", json={"expr": expr})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == expected


def test_calc_rejects_non_numeric_input(client, login):
    login("buyer@test.local", "buyer-pass-1")
    for expr in ("", "abc", "1/0", "True", "'text'"):
        resp = client.post("/tools/calc", json={"expr": expr})
        assert resp.status_code == 400, expr
        assert resp.get_json() == {"error": "invalid expression"}


def test_calc_requires_login(client):
    assert client.post("/tools/calc", json={"expr": "1+1"}).status_code == 401


def test_fetch_returns_upstream_body(client, login, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Reply())
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/fetch?url=https://example.com/status")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": 200, "body": "hello from upstream"}


def test_fetch_requires_login(client):
    assert client.get("/tools/fetch?url=https://example.com/").status_code == 401


def test_import_config_parses_yaml(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post(
        "/tools/import-config", data="theme: dark\nsize: 12\n", content_type="text/yaml"
    )
    assert resp.status_code == 200
    assert resp.get_json()["config"] == {"theme": "dark", "size": 12}


def test_import_config_parses_nested_and_list_documents(client, login):
    login("buyer@test.local", "buyer-pass-1")
    doc = "service:\n  name: shopdesk\n  ports: [80, 443]\nflags:\n  - a\n  - b\n"
    resp = client.post("/tools/import-config", data=doc, content_type="text/yaml")
    assert resp.status_code == 200
    assert resp.get_json()["config"] == {
        "service": {"name": "shopdesk", "ports": [80, 443]},
        "flags": ["a", "b"],
    }


def test_import_config_parses_scalar_document(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/import-config", data="just a string\n", content_type="text/yaml")
    assert resp.status_code == 200
    assert resp.get_json()["config"] == "just a string"


def test_import_config_rejects_malformed_yaml(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post("/tools/import-config", data="a: [1, 2\n", content_type="text/yaml")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "invalid yaml"}


def test_import_config_requires_login(client):
    resp = client.post("/tools/import-config", data="a: 1\n", content_type="text/yaml")
    assert resp.status_code == 401


# --- Post-fix regression guards: ping argv shape + host validation ---


def test_ping_argv_is_list_ending_in_resolved_ip(client, login, monkeypatch):
    # The argv handed to subprocess.run must be a list whose last element is the
    # canonical IP, never the raw request string.
    seen = {}

    def _run(argv, **kwargs):
        seen["argv"] = argv
        seen["kwargs"] = kwargs
        return _Done()

    monkeypatch.setattr(subprocess, "run", _run)
    login("buyer@test.local", "buyer-pass-1")
    resp = client.get("/tools/ping?host=127.0.0.1")
    assert resp.status_code == 200

    argv = seen["argv"]
    assert isinstance(argv, list)
    assert argv[:3] == ["ping", "-c", "1"]
    assert argv[-1] == "127.0.0.1"
    # No shell, no raw request string anywhere in the argv.
    assert seen["kwargs"].get("shell") is not True
    assert "host=127.0.0.1" not in " ".join(argv)
    assert "/tools/ping" not in " ".join(argv)


def test_ping_argv_uses_canonical_ip_for_ipv6(client, login, monkeypatch):
    seen = {}

    def _run(argv, **kwargs):
        seen["argv"] = argv
        return _Done()

    monkeypatch.setattr(subprocess, "run", _run)
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/tools/ping?host=::1").status_code == 200
    assert seen["argv"][-1] == "::1"


def test_ping_rejects_shell_metacharacters_without_running_subprocess(
    client, login, monkeypatch
):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a) or _Done())
    login("buyer@test.local", "buyer-pass-1")
    for host in ("127.0.0.1;id", "127.0.0.1 && id", "$(id)", "`id`", "a|b", "a b"):
        resp = client.get("/tools/ping", query_string={"host": host})
        assert resp.status_code == 400, host
        assert resp.get_json() == {"error": "invalid host"}
    assert calls == []


def test_ping_accepts_plain_hostnames(client, login, monkeypatch):
    seen = {}

    def _run(argv, **kwargs):
        seen["argv"] = argv
        return _Done()

    monkeypatch.setattr(subprocess, "run", _run)
    login("buyer@test.local", "buyer-pass-1")
    for host in ("localhost", "example.com", "sub.example.co.uk"):
        assert client.get("/tools/ping", query_string={"host": host}).status_code == 200
        assert seen["argv"][:3] == ["ping", "-c", "1"]
        assert isinstance(seen["argv"][-1], str) and seen["argv"][-1]


def test_ping_returns_exit_code_and_stdout(client, login, monkeypatch):
    class _Fail:
        returncode = 1
        stdout = "1 packets transmitted, 0 received"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Fail())
    login("buyer@test.local", "buyer-pass-1")
    body = client.get("/tools/ping?host=127.0.0.1").get_json()
    assert body == {"exit": 1, "output": "1 packets transmitted, 0 received"}


def test_calc_still_handles_nested_and_unary_expressions(client, login):
    login("buyer@test.local", "buyer-pass-1")
    for expr, expected in (
        ("((2+3)*(4-1))", 15),
        ("-(2**3)", -8),
        ("+7", 7),
        ("2**3**2", 512),
        ("10 % 4 + 1", 3),
    ):
        resp = client.post("/tools/calc", json={"expr": expr})
        assert resp.status_code == 200, expr
        assert resp.get_json()["result"] == expected, expr


def test_import_config_still_parses_plain_yaml_after_fix(client, login):
    # safe_load must keep returning ordinary Python data for normal documents.
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post(
        "/tools/import-config",
        data="name: shopdesk\nversion: 2\nenabled: true\n",
        content_type="text/yaml",
    )
    assert resp.status_code == 200
    assert resp.get_json()["config"] == {"name": "shopdesk", "version": 2, "enabled": True}
