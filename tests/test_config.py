import os

import pytest

from app import create_app
from app.config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    BASE_DIR,
    DATABASE,
    INSTANCE_DIR,
    PAYMENT_API_KEY,
    PAYMENT_API_URL,
    PREFS_DIR,
    SECRET_KEY,
    UPLOAD_DIR,
    _instance_path,
)
from app.db import get_db


def _build_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "cfg.db"),
            "UPLOAD_DIR": str(tmp_path / "cfg-uploads"),
            "PREFS_DIR": str(tmp_path / "cfg-prefs"),
        }
    )


def test_instance_paths_are_absolute_and_live_under_instance_dir():
    instance = os.path.realpath(INSTANCE_DIR)

    assert os.path.dirname(instance) == os.path.realpath(BASE_DIR)
    assert os.path.basename(instance) == "instance"
    for path in (DATABASE, UPLOAD_DIR, PREFS_DIR):
        assert os.path.isabs(path)
        assert os.path.commonpath([instance, path]) == instance


def test_state_locations_are_distinct():
    assert len({DATABASE, UPLOAD_DIR, PREFS_DIR}) == 3
    assert DATABASE.endswith(".db")


def test_instance_path_joins_nested_parts():
    expected = os.path.join(os.path.realpath(INSTANCE_DIR), "uploads", "2026")
    assert _instance_path("uploads", "2026") == expected


def test_instance_path_refuses_to_escape_the_instance_dir():
    with pytest.raises(ValueError):
        _instance_path("..", "escaped.db")


def test_instance_path_without_parts_returns_the_instance_directory():
    assert _instance_path() == os.path.realpath(INSTANCE_DIR)


def test_instance_path_backs_every_module_level_state_location():
    assert _instance_path("shopdesk.db") == DATABASE
    assert _instance_path("uploads") == UPLOAD_DIR
    assert _instance_path("prefs") == PREFS_DIR


def test_instance_path_accepts_ordinary_file_and_directory_names():
    instance = os.path.realpath(INSTANCE_DIR)

    assert _instance_path("a") == os.path.join(instance, "a")
    assert _instance_path("v1.2-notes_2026", "report.csv") == os.path.join(
        instance, "v1.2-notes_2026", "report.csv"
    )
    assert _instance_path("uploads", "2026", "01") == os.path.join(
        instance, "uploads", "2026", "01"
    )


def test_state_locations_are_normalized_without_traversal_segments():
    for path in (INSTANCE_DIR, DATABASE, UPLOAD_DIR, PREFS_DIR):
        assert os.path.isabs(path)
        assert os.path.normpath(path) == path
        assert ".." not in path.split(os.sep)


def test_app_keeps_caller_supplied_state_overrides(tmp_path):
    application = _build_app(tmp_path)

    assert application.config["DATABASE"] == str(tmp_path / "cfg.db")
    assert application.config["UPLOAD_DIR"] == str(tmp_path / "cfg-uploads")
    assert application.config["PREFS_DIR"] == str(tmp_path / "cfg-prefs")


def test_required_settings_are_populated():
    assert isinstance(SECRET_KEY, str) and SECRET_KEY
    assert "@" in ADMIN_EMAIL
    assert isinstance(ADMIN_PASSWORD, str) and ADMIN_PASSWORD
    assert PAYMENT_API_URL.startswith("https://")
    assert isinstance(PAYMENT_API_KEY, str) and PAYMENT_API_KEY


def test_app_creates_its_state_directories_and_database(tmp_path):
    application = _build_app(tmp_path)

    assert os.path.isdir(application.config["UPLOAD_DIR"])
    assert os.path.isdir(application.config["PREFS_DIR"])
    assert os.path.isfile(application.config["DATABASE"])


def test_app_seeds_the_configured_admin_account(tmp_path):
    application = _build_app(tmp_path)
    with application.app_context():
        row = get_db().execute(
            "SELECT email, role, password FROM users WHERE email = ?", (ADMIN_EMAIL,)
        ).fetchone()

    assert row is not None
    assert row["role"] == "admin"
    assert row["password"].startswith("pbkdf2_sha256$")
    assert row["password"] != ADMIN_PASSWORD


def test_seeded_admin_can_log_in(tmp_path):
    application = _build_app(tmp_path)
    client = application.test_client()

    resp = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"
