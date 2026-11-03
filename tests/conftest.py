import pytest

from app import create_app
from app.db import get_db
from app.security import hash_password


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "UPLOAD_DIR": str(tmp_path / "uploads"),
            "PREFS_DIR": str(tmp_path / "prefs"),
        }
    )
    with app.app_context():
        conn = get_db()
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("ops@test.local", "Ops", hash_password("ops-pass-1"), "admin"),
        )
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
            ("buyer@test.local", "Buyer", hash_password("buyer-pass-1"), "customer"),
        )
        conn.commit()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login(client):
    def _login(email, password):
        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.get_data(as_text=True)
        return resp.get_json()

    return _login
