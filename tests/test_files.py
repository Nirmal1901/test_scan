import io
import os

import pytest

from app.files import _safe_path


def test_upload_and_download_roundtrip(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post(
        "/files/upload",
        data={"file": (io.BytesIO(b"hi there"), "hello.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    assert resp.get_json()["size"] == 8
    resp = client.get("/files/download?name=hello.txt")
    assert resp.status_code == 200
    assert resp.data == b"hi there"


def test_upload_response_shape_and_storage(app, client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post(
        "/files/upload",
        data={"file": (io.BytesIO(b"0123456789"), "report.csv")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    assert resp.get_json() == {"name": "report.csv", "size": 10}
    assert os.path.isfile(os.path.join(app.config["UPLOAD_DIR"], "report.csv"))


def test_upload_overwrites_existing_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    for payload in (b"first", b"second-version"):
        resp = client.post(
            "/files/upload",
            data={"file": (io.BytesIO(payload), "notes.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
    assert client.get("/files/download?name=notes.txt").data == b"second-version"


def test_download_is_served_as_attachment(client, login):
    login("buyer@test.local", "buyer-pass-1")
    client.post(
        "/files/upload",
        data={"file": (io.BytesIO(b"data"), "invoice.txt")},
        content_type="multipart/form-data",
    )
    resp = client.get("/files/download?name=invoice.txt")
    assert resp.status_code == 200
    assert "attachment" in resp.headers["Content-Disposition"]
    assert "invoice.txt" in resp.headers["Content-Disposition"]


def test_download_missing_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/files/download?name=ghost.txt").status_code == 404


def test_download_without_name(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/files/download").status_code == 404


def test_download_rejects_traversal_name(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/files/download?name=../../etc/passwd").status_code == 404


def test_upload_rejects_traversal_filename(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post(
        "/files/upload",
        data={"file": (io.BytesIO(b"x"), "../../evil.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "invalid file name"}


def test_safe_path_resolves_plain_names_inside_upload_dir(app):
    with app.app_context():
        base = os.path.abspath(app.config["UPLOAD_DIR"])
        assert _safe_path("hello.txt") == os.path.join(base, "hello.txt")
        assert _safe_path("report.v2.csv") == os.path.join(base, "report.v2.csv")


@pytest.mark.parametrize("name", ["", "../evil.txt", "sub/evil.txt", "/etc/passwd"])
def test_safe_path_rejects_unsafe_names(app, name):
    with app.app_context():
        assert _safe_path(name) is None


def test_upload_requires_login(client):
    resp = client.post(
        "/files/upload",
        data={"file": (io.BytesIO(b"x"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_download_requires_login(client):
    assert client.get("/files/download?name=a.txt").status_code == 401


def test_upload_without_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.post("/files/upload", data={}).status_code == 400
