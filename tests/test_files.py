import io
import os


def _upload(client, payload, filename):
    return client.post(
        "/files/upload",
        data={"file": (io.BytesIO(payload), filename)},
        content_type="multipart/form-data",
    )


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


def test_download_missing_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/files/download?name=ghost.txt").status_code == 404


def test_upload_requires_login(client):
    resp = client.post(
        "/files/upload",
        data={"file": (io.BytesIO(b"x"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_upload_without_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.post("/files/upload", data={}).status_code == 400


def test_upload_sanitizes_names_with_spaces(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, b"quarterly", "Quarterly Report.txt")
    assert resp.status_code == 201
    name = resp.get_json()["name"]
    assert " " not in name
    assert name.startswith("Quarterly") and name.endswith(".txt")
    assert client.get("/files/download?name=" + name).data == b"quarterly"


def test_upload_keeps_traversal_filename_inside_upload_dir(app, client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, b"payload", "../evil.txt")
    assert resp.status_code == 201
    name = resp.get_json()["name"]
    assert "/" not in name and ".." not in name
    assert name == "evil.txt"
    upload_dir = app.config["UPLOAD_DIR"]
    assert os.listdir(upload_dir) == [name]
    assert os.path.isfile(os.path.join(upload_dir, name))
    assert not os.path.exists(os.path.join(os.path.dirname(upload_dir), "evil.txt"))
    assert client.get("/files/download?name=evil.txt").data == b"payload"


def test_upload_rejects_empty_filename(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, b"x", "")
    assert resp.status_code == 400


def test_download_requires_login(client):
    assert client.get("/files/download?name=hello.txt").status_code == 401


def test_download_unknown_name_is_404(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/files/download?name=").status_code == 404
    assert client.get("/files/download?name=../../app/config.py").status_code == 404


def test_download_sets_attachment_header(client, login):
    login("buyer@test.local", "buyer-pass-1")
    _upload(client, b"hi there", "hello.txt")
    resp = client.get("/files/download?name=hello.txt")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    assert disposition.startswith("attachment")
    assert "hello.txt" in disposition
