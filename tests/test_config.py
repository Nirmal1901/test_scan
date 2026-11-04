import os

import pytest

from app import config, create_app


def test_base_dir_is_the_repo_root():
    assert config.BASE_DIR == os.path.abspath(
        os.path.join(os.path.dirname(config.__file__), "..")
    )
    assert os.path.isdir(config.BASE_DIR)


def test_instance_dir_hangs_off_base_dir():
    assert config.INSTANCE_DIR == os.path.join(config.BASE_DIR, "instance")


def test_runtime_paths_are_absolute_and_inside_instance():
    instance = os.path.join(config.BASE_DIR, "instance")
    for name in ("DATABASE", "UPLOAD_DIR", "PREFS_DIR"):
        value = getattr(config, name)
        assert os.path.isabs(value), name
        assert os.path.commonpath([value, instance]) == instance, name


def test_default_paths_keep_their_documented_names():
    instance = os.path.join(config.BASE_DIR, "instance")
    assert config.DATABASE == os.path.join(instance, "shopdesk.db")
    assert config.UPLOAD_DIR == os.path.join(instance, "uploads")
    assert config.PREFS_DIR == os.path.join(instance, "prefs")


def test_secrets_and_endpoints_are_present():
    assert config.SECRET_KEY
    assert config.ADMIN_EMAIL and "@" in config.ADMIN_EMAIL
    assert config.ADMIN_PASSWORD
    assert config.PAYMENT_API_URL.startswith("https://")
    assert config.PAYMENT_API_KEY


def test_create_app_starts_from_default_config():
    app = create_app({"TESTING": True})
    assert app.config["TESTING"] is True
    assert app.config["DATABASE"] == config.DATABASE
    assert app.config["UPLOAD_DIR"] == config.UPLOAD_DIR
    assert app.config["PREFS_DIR"] == config.PREFS_DIR
    assert app.config["SECRET_KEY"] == config.SECRET_KEY
    assert app.config["ADMIN_EMAIL"] == config.ADMIN_EMAIL
    # create_app() must materialise the directories the blueprints write into
    assert os.path.isdir(app.config["UPLOAD_DIR"])
    assert os.path.isdir(app.config["PREFS_DIR"])
    assert os.path.isdir(os.path.dirname(app.config["DATABASE"]))


def test_test_config_overrides_only_given_keys(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "db.sqlite"),
            "UPLOAD_DIR": str(tmp_path / "up"),
            "PREFS_DIR": str(tmp_path / "prefs"),
        }
    )
    assert app.config["DATABASE"] == str(tmp_path / "db.sqlite")
    assert app.config["SECRET_KEY"] == config.SECRET_KEY
    assert app.config["PAYMENT_API_URL"] == config.PAYMENT_API_URL


def test_default_admin_can_log_in_with_configured_password(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "db.sqlite"),
            "UPLOAD_DIR": str(tmp_path / "up"),
            "PREFS_DIR": str(tmp_path / "prefs"),
        }
    )
    client = app.test_client()
    resp = client.post(
        "/auth/login",
        json={"email": config.ADMIN_EMAIL, "password": config.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "admin"
    assert client.get("/auth/me").get_json()["email"] == config.ADMIN_EMAIL


def test_join_under_allows_a_plain_component():
    assert config._join_under("/base", "child") == os.path.join("/base", "child")
    assert config._join_under("/base", "shopdesk.db") == "/base/shopdesk.db"


@pytest.mark.parametrize("bad", ["", ".", "..", "../escape", "a/b", "/absolute"])
def test_join_under_rejects_path_components(bad):
    with pytest.raises(ValueError):
        config._join_under("/base", bad)
