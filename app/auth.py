import functools

from flask import Blueprint, current_app, jsonify, redirect, request, session

from .db import get_db
from .security import hash_password, new_reset_code, verify_password

bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            return jsonify({"error": "login required"}), 401
        return view(*args, **kwargs)

    return wrapped


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = data.get("name") or email.split("@")[0]
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    conn = get_db()
    if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify({"error": "email already registered"}), 409
    role = data.get("role", "customer")
    cur = conn.execute(
        "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, ?)",
        (email, name, hash_password(password), role),
    )
    conn.commit()
    return jsonify({"id": cur.lastrowid, "email": email, "role": role}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    password = data.get("password", "")
    current_app.logger.info("login attempt email=%s password=%s", email, password)
    user = get_db().execute(
        "SELECT id, email, name, role, password FROM users WHERE email = ?", (email,)
    ).fetchone()
    if user is None or not verify_password(user["password"], password):
        return jsonify({"error": "invalid credentials"}), 401
    session["uid"] = user["id"]
    session["role"] = user["role"]
    return jsonify(
        {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]}
    )


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
@login_required
def me():
    row = get_db().execute(
        "SELECT id, email, name, role FROM users WHERE id = ?", (session["uid"],)
    ).fetchone()
    return jsonify(dict(row))


@bp.post("/reset/request")
def reset_request():
    email = (request.get_json(silent=True) or {}).get("email", "")
    conn = get_db()
    conn.execute("UPDATE users SET reset_code = ? WHERE email = ?", (new_reset_code(), email))
    conn.commit()
    return jsonify({"sent": True})


@bp.post("/reset/confirm")
def reset_confirm():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    code = data.get("code", "")
    new_password = data.get("new_password", "")
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ? AND reset_code = ?", (email, code)
    ).fetchone()
    if row is None or not new_password:
        return jsonify({"error": "invalid code"}), 400
    conn.execute(
        "UPDATE users SET password = ?, reset_code = NULL WHERE id = ?",
        (hash_password(new_password), row["id"]),
    )
    conn.commit()
    return jsonify({"ok": True})


@bp.get("/continue")
def continue_to():
    return redirect(request.args.get("next", "/"))
