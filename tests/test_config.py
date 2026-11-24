import io
import os

import pytest

from app import config, create_app


def test_base_and_instance_dirs_are_absolute_paths():
    assert os.path.isabs(config.BASE_DIR)
    assert os.path.isabs(config.INSTANCE_DIR)
    # BASE_DIR is the repo root (the directory that contains the app package).
    assert os.path.isdir(os.path.join(config.BASE_DIR, "app"))
    assert config.INSTANCE_DIR == os.path.join(config.BASE_DIR, "instance")


def test_default_paths_are_joined_onto_instance_dir():
    assert config.DATABASE == os.path.join(config.INSTANCE_DIR, "shopdesk.db")
    assert config.UPLOAD_DIR == os.path.join(config.INSTANCE_DIR, "uploads")
    assert config.PREFS_DIR == os.path.join(config.INSTANCE_DIR, "prefs")
    for path in (config.DATABASE, config.UPLOAD_DIR, config.PREFS_DIR):
        assert os.path.isabs(path)
        assert os.path.commonpath([path, config.INSTANCE_DIR]) == config.INSTANCE_DIR


def test_default_paths_are_normalized():
    for path in (config.INSTANCE_DIR, config.DATABASE, config.UPLOAD_DIR, config.PREFS_DIR):
        assert path == os.path.normpath(path)
        assert ".." not in path.split(os.sep)
        assert path == os.path.abspath(path)


def test_safe_join_accepts_plain_component():
    base = os.path.abspath(os.path.join(os.sep, "srv", "shopdesk", "instance"))
    assert config._safe_join(base, "shopdesk.db", "DATABASE") == os.path.join(base, "shopdesk.db")
    assert config._safe_join(base, "uploads", "UPLOAD_DIR") == os.path.join(base, "uploads")
    assert config._safe_join(base, "prefs", "PREFS_DIR") == os.path.join(base, "prefs")


def test_safe_join_accepts_normal_file_and_dir_names(tmp_path):
    base = str(tmp_path)
    for name in ("uploads", "shopdesk.db", "report.v2.csv", "hello world.txt", "user-42.pkl"):
        joined = config._safe_join(base, name, "TEST")
        assert joined == os.path.join(base, name)
        assert os.path.dirname(joined) == base


def test_safe_join_accepts_numeric_prefs_filename(tmp_path):
    # account.py builds "<uid>.pkl" from an int-coerced session uid.
    base = str(tmp_path)
    for uid in (1, 42, 999999):
        name = "%d.pkl" % uid
        assert config._safe_join(base, name, "PREFS_DIR") == os.path.join(base, name)


def test_safe_join_accepts_uploaded_filename_with_spaces(tmp_path):
    base = str(tmp_path)
    joined = config._safe_join(base, "q3 report.v2.csv", "UPLOAD_DIR")
    assert joined == os.path.join(base, "q3 report.v2.csv")
    assert os.path.dirname(joined) == base


def test_safe_join_accepts_name_that_does_not_exist_yet(tmp_path):
    # Uploads and prefs are written to paths that do not exist at join time.
    base = str(tmp_path)
    joined = config._safe_join(base, "brand-new.txt", "UPLOAD_DIR")
    assert not os.path.exists(joined)
    assert joined == os.path.join(base, "brand-new.txt")


def test_safe_join_accepts_existing_file_inside_base(tmp_path):
    base = str(tmp_path)
    existing = os.path.join(base, "already.txt")
    with open(existing, "w", encoding="utf-8") as fh:
        fh.write("x")
    assert config._safe_join(base, "already.txt", "UPLOAD_DIR") == existing


def test_safe_join_accepts_symlinked_base(tmp_path):
    # macOS /var -> /private/var style bases must still work: containment is
    # checked against the canonicalized base.
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    os.symlink(str(real), str(link))
    joined = config._safe_join(str(link), "shopdesk.db", "DATABASE")
    assert os.path.basename(joined) == "shopdesk.db"
    assert os.path.realpath(os.path.dirname(joined)) == os.path.realpath(str(real))


def test_safe_join_normalizes_relative_base(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs(os.path.join(str(tmp_path), "instance"))
    joined = config._safe_join("instance", "shopdesk.db", "DATABASE")
    assert joined == os.path.join(str(tmp_path), "instance", "shopdesk.db")


@pytest.mark.parametrize("name", ["", ".", "..", "../etc/passwd", "/etc/passwd", "../../tmp"])
def test_safe_join_rejects_unsafe_component(name):
    with pytest.raises(ValueError) as excinfo:
        config._safe_join(os.path.join(os.sep, "srv", "instance"), name, "DATABASE")
    assert "unsafe path component for DATABASE" in str(excinfo.value)


def test_safe_join_result_is_usable_for_directory_creation(tmp_path):
    # create_app() calls os.makedirs() on these values, so the joined paths
    # must be writable locations, not just syntactic strings.
    upload_dir = config._safe_join(str(tmp_path), "uploads", "UPLOAD_DIR")
    os.makedirs(upload_dir, exist_ok=True)
    assert os.path.isdir(upload_dir)

    stored = os.path.join(upload_dir, "hello.txt")
    with open(stored, "wb") as fh:
        fh.write(b"hi there")
    assert os.path.getsize(stored) == 8


def test_required_settings_are_present_and_typed():
    assert isinstance(config.SECRET_KEY, str) and config.SECRET_KEY
    assert isinstance(config.ADMIN_EMAIL, str) and "@" in config.ADMIN_EMAIL
    assert isinstance(config.ADMIN_PASSWORD, str) and config.ADMIN_PASSWORD
    assert isinstance(config.PAYMENT_API_URL, str) and config.PAYMENT_API_URL.startswith("http")
    assert isinstance(config.PAYMENT_API_KEY, str) and config.PAYMENT_API_KEY
    for key in ("SESSION_COOKIE_HTTPONLY", "SESSION_COOKIE_SECURE"):
        assert isinstance(getattr(config, key), bool)


def test_settings_flow_into_app_config(tmp_path):
    # The settings are read through Flask's config, so they must survive
    # from_object() with their values intact.
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "settings.db"),
            "UPLOAD_DIR": str(tmp_path / "settings-uploads"),
            "PREFS_DIR": str(tmp_path / "settings-prefs"),
        }
    )
    assert app.config["SECRET_KEY"] == config.SECRET_KEY
    assert app.config["ADMIN_EMAIL"] == config.ADMIN_EMAIL
    assert app.config["ADMIN_PASSWORD"] == config.ADMIN_PASSWORD
    assert app.config["PAYMENT_API_URL"] == config.PAYMENT_API_URL
    assert app.config["PAYMENT_API_KEY"] == config.PAYMENT_API_KEY


def test_create_app_boots_with_module_default_paths(tmp_path, monkeypatch):
    # Patch only the path settings so the defaults still flow through
    # create_app() -> Flask config without writing into the repo's instance dir.
    db_path = str(tmp_path / "instance" / "shopdesk.db")
    monkeypatch.setattr(config, "INSTANCE_DIR", str(tmp_path / "instance"))
    monkeypatch.setattr(config, "DATABASE", db_path)
    monkeypatch.setattr(config, "UPLOAD_DIR", str(tmp_path / "instance" / "uploads"))
    monkeypatch.setattr(config, "PREFS_DIR", str(tmp_path / "instance" / "prefs"))

    app = create_app()
    assert app.config["DATABASE"] == db_path
    assert app.config["UPLOAD_DIR"] == str(tmp_path / "instance" / "uploads")
    assert app.config["PREFS_DIR"] == str(tmp_path / "instance" / "prefs")
    assert app.config["SECRET_KEY"] == config.SECRET_KEY

    # create_app() must have created the configured directories and the database.
    assert os.path.isdir(app.config["UPLOAD_DIR"])
    assert os.path.isdir(app.config["PREFS_DIR"])
    assert os.path.isfile(db_path)

    client = app.test_client()
    assert client.get("/").get_json() == {"service": "shopdesk", "status": "ok"}
    # Public catalog flow is seeded from the fresh database.
    assert len(client.get("/catalog/search").get_json()) == 6

    # Admin account comes from config.ADMIN_EMAIL / config.ADMIN_PASSWORD.
    resp = client.post(
        "/auth/login",
        json={"email": config.ADMIN_EMAIL, "password": config.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "admin"
    assert client.get("/auth/me").get_json()["email"] == config.ADMIN_EMAIL


def test_upload_and_prefs_use_configured_directories(app, client, login):
    login("buyer@test.local", "buyer-pass-1")
    resp = client.post(
        "/files/upload",
        data={"file": (io.BytesIO(b"hi there"), "hello.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    stored = os.path.join(app.config["UPLOAD_DIR"], "hello.txt")
    assert os.path.isfile(stored)
    assert os.path.getsize(stored) == 8

    assert client.put("/account/prefs", json={"theme": "dark"}).status_code == 200
    pkls = [n for n in os.listdir(app.config["PREFS_DIR"]) if n.endswith(".pkl")]
    assert len(pkls) == 1
    assert client.get("/account/prefs").get_json() == {"theme": "dark"}


def test_test_config_overrides_defaults_but_keeps_the_rest(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "override.db"),
            "UPLOAD_DIR": str(tmp_path / "override-uploads"),
            "PREFS_DIR": str(tmp_path / "override-prefs"),
        }
    )
    assert app.config["DATABASE"] == str(tmp_path / "override.db")
    assert app.config["UPLOAD_DIR"] == str(tmp_path / "override-uploads")
    assert app.config["PREFS_DIR"] == str(tmp_path / "override-prefs")
    assert os.path.isfile(str(tmp_path / "override.db"))
    # Settings not overridden still come from the config module.
    assert app.config["SECRET_KEY"] == config.SECRET_KEY
    assert app.config["ADMIN_EMAIL"] == config.ADMIN_EMAIL
