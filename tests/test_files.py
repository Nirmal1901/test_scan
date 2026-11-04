import io
import os

from app.files import _upload_path


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


def _upload(client, name, payload):
    return client.post(
        "/files/upload",
        data={"file": (io.BytesIO(payload), name)},
        content_type="multipart/form-data",
    )


def _download(client, name):
    return client.get("/files/download", query_string={"name": name})


def test_upload_keeps_only_the_basename_of_a_client_supplied_path(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "reports/2026/q1.txt", b"quarter one")
    assert resp.status_code == 201

    name = resp.get_json()["name"]
    assert "/" not in name
    assert name.endswith("q1.txt")
    assert _download(client, name).data == b"quarter one"


def test_upload_overwrites_existing_file_and_reports_size(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert _upload(client, "note.txt", b"first").get_json()["size"] == 5

    resp = _upload(client, "note.txt", b"second version")
    assert resp.status_code == 201
    assert resp.get_json()["size"] == len(b"second version")
    assert resp.get_json()["name"] == "note.txt"
    assert _download(client, "note.txt").data == b"second version"


def test_upload_and_download_binary_payload(client, login):
    login("buyer@test.local", "buyer-pass-1")
    payload = bytes(range(256))
    assert _upload(client, "blob.bin", payload).get_json()["size"] == 256
    assert _download(client, "blob.bin").data == payload


def test_upload_and_download_empty_file(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "empty.txt", b"")
    assert resp.status_code == 201
    assert resp.get_json()["size"] == 0
    assert _download(client, "empty.txt").data == b""


def test_download_is_served_as_an_attachment(client, login):
    login("buyer@test.local", "buyer-pass-1")
    _upload(client, "report.csv", b"a,b\n1,2\n")
    resp = _download(client, "report.csv")
    assert resp.status_code == 200
    disposition = resp.headers["Content-Disposition"]
    assert "attachment" in disposition
    assert "report.csv" in disposition


def test_download_requires_login(client):
    assert client.get("/files/download", query_string={"name": "hello.txt"}).status_code == 401


def test_upload_path_helper_resolves_inside_upload_dir(app):
    with app.app_context():
        path = _upload_path("photo.png")
        assert os.path.basename(path) == "photo.png"
        assert os.path.dirname(path) == os.path.realpath(app.config["UPLOAD_DIR"])
        assert _upload_path("") is None
        assert _upload_path(None) is None


def test_upload_sanitizes_spaces_and_still_roundtrips(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "my quarterly report.txt", b"q1 numbers")
    assert resp.status_code == 201

    name = resp.get_json()["name"]
    assert " " not in name
    assert name.endswith("report.txt")
    assert _download(client, name).data == b"q1 numbers"


def test_upload_keeps_dots_dashes_and_underscores_in_names(client, login):
    login("buyer@test.local", "buyer-pass-1")
    name = "v1.2_final-report.txt"

    resp = _upload(client, name, b"payload")
    assert resp.status_code == 201
    assert resp.get_json()["name"] == name
    assert _download(client, name).data == b"payload"


def test_upload_stores_the_file_inside_the_upload_dir(app, client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert _upload(client, "photo.png", b"png-bytes").status_code == 201

    with app.app_context():
        assert "photo.png" in os.listdir(app.config["UPLOAD_DIR"])


def test_upload_and_download_of_a_non_ascii_name_roundtrips(client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = _upload(client, "räksmörgås.txt", b"smorgas")
    assert resp.status_code == 201

    name = resp.get_json()["name"]
    assert name  # normalized to a storable name, but never dropped
    assert name.isascii()
    assert _download(client, name).data == b"smorgas"


def test_download_of_a_name_that_cannot_be_resolved(client, login):
    login("buyer@test.local", "buyer-pass-1")
    assert _download(client, "").status_code == 404
    assert _download(client, "!!!").status_code == 404


def test_upload_path_helper_preserves_ordinary_names(app):
    with app.app_context():
        base = os.path.realpath(app.config["UPLOAD_DIR"])
        for name in ("a.txt", "v1.2_final-report.csv", "REPORT-2026.TXT", "photo.png"):
            assert _upload_path(name) == os.path.join(base, name)


def test_upload_path_helper_rejects_names_with_nothing_left_to_store(app):
    with app.app_context():
        assert _upload_path("!!!") is None
        assert _upload_path("   ") is None
        assert _upload_path("..") is None
