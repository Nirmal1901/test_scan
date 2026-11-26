import io
import os


def _upload(client, name, payload=b"hi there"):
    return client.post(
        "/files/upload",
        data={"file": (io.BytesIO(payload), name)},
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


def test_upload_response_reports_name_and_size(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "notes.txt", b"0123456789")
    assert resp.status_code == 201
    assert resp.get_json() == {"name": "notes.txt", "size": 10}


def test_upload_writes_into_upload_dir(app, client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert _upload(client, "report.csv", b"a,b\n1,2\n").status_code == 201
    stored = os.path.join(app.config["UPLOAD_DIR"], "report.csv")
    assert os.path.isfile(stored)
    with open(stored, "rb") as fh:
        assert fh.read() == b"a,b\n1,2\n"


def test_upload_accepts_names_with_spaces_and_dots(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert _upload(client, "q3 report.v2.csv", b"x").status_code == 201
    resp = client.get("/files/download?name=q3 report.v2.csv")
    assert resp.status_code == 200
    assert resp.data == b"x"


def test_upload_overwrites_existing_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert _upload(client, "same.txt", b"first").status_code == 201
    assert _upload(client, "same.txt", b"second").status_code == 201
    assert client.get("/files/download?name=same.txt").data == b"second"


def test_download_is_an_attachment(client, login):
    login("buyer@test.local", "buyer-pass-1")
    _upload(client, "hello.txt")
    resp = client.get("/files/download?name=hello.txt")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("Content-Disposition", "")


def test_download_missing_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/files/download?name=ghost.txt").status_code == 404


def test_download_without_name(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert client.get("/files/download").status_code == 404


def test_download_requires_login(client):
    assert client.get("/files/download?name=hello.txt").status_code == 401


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


# --- Post-fix regression guards: upload/download contract must be unchanged ---


def test_upload_of_path_prefixed_name_lands_as_basename(app, client, login):
    # A client that sends a directory part in the filename must still get its
    # file stored, just under the bare basename inside UPLOAD_DIR.
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "../../evil.txt", b"payload")
    assert resp.status_code == 201
    assert resp.get_json() == {"name": "evil.txt", "size": 7}

    stored = os.path.join(app.config["UPLOAD_DIR"], "evil.txt")
    assert os.path.isfile(stored)
    with open(stored, "rb") as fh:
        assert fh.read() == b"payload"
    # Nothing escaped the upload dir.
    assert not os.path.exists(os.path.join(app.config["UPLOAD_DIR"], "..", "evil.txt"))
    assert sorted(os.listdir(app.config["UPLOAD_DIR"])) == ["evil.txt"]


def test_upload_of_nested_relative_name_lands_as_basename(app, client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "docs/2024/report.csv", b"a,b\n")
    assert resp.status_code == 201
    assert resp.get_json()["name"] == "report.csv"
    assert os.path.isfile(os.path.join(app.config["UPLOAD_DIR"], "report.csv"))


def test_download_of_traversal_name_returns_404(client, login):
    # The database lives next to UPLOAD_DIR; a traversal attempt must 404, not
    # serve it.
    login("buyer@test.local", "buyer-pass-1")
    for name in ("../shopdesk.db", "../test.db", "../../etc/passwd", "..", "/etc/passwd"):
        resp = client.get("/files/download", query_string={"name": name})
        assert resp.status_code == 404, name
        assert resp.get_json() == {"error": "not found"}


def test_download_roundtrip_after_upload_of_sanitized_name(client, login):
    # The name reported by upload is the name download accepts.
    login("buyer@test.local", "buyer-pass-1")
    uploaded = _upload(client, "../../evil.txt", b"payload").get_json()
    resp = client.get("/files/download", query_string={"name": uploaded["name"]})
    assert resp.status_code == 200
    assert resp.data == b"payload"


def test_upload_and_download_binary_payload(client, login):
    login("buyer@test.local", "buyer-pass-1")
    payload = bytes(range(256))
    assert _upload(client, "blob.bin", payload).status_code == 201
    resp = client.get("/files/download?name=blob.bin")
    assert resp.status_code == 200
    assert resp.data == payload


def test_upload_empty_file_is_accepted(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "empty.txt", b"")
    assert resp.status_code == 201
    assert resp.get_json() == {"name": "empty.txt", "size": 0}
    assert client.get("/files/download?name=empty.txt").data == b""


def test_upload_rejects_name_that_sanitizes_to_nothing(client, login):
    # A filename that reduces to "." / ".." has no usable basename.
    login("buyer@test.local", "buyer-pass-1")
    for name in ("..", "."):
        resp = _upload(client, name, b"x")
        assert resp.status_code == 400, name
        assert resp.get_json() == {"error": "invalid filename"}
