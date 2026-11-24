import json
import os

from flask import Blueprint, current_app, jsonify, request, session

from .auth import login_required
from .db import get_db

bp = Blueprint("account", __name__, url_prefix="/account")


def _prefs_path(uid):
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        raise ValueError("invalid user id")
    base = os.path.abspath(current_app.config["PREFS_DIR"])
    path = os.path.abspath(os.path.join(base, str(uid) + ".pkl"))
    if os.path.commonpath([base, path]) != base:
        raise ValueError("invalid user id")
    return path


@bp.get("/prefs")
@login_required
def get_prefs():
    path = _prefs_path(session["uid"])
    if not os.path.exists(path):
        return jsonify({})
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return jsonify(json.load(fh))
        except (ValueError, OSError):
            return jsonify({})


@bp.put("/prefs")
@login_required
def put_prefs():
    prefs = request.get_json(silent=True) or {}
    with open(_prefs_path(session["uid"]), "w", encoding="utf-8") as fh:
        json.dump(prefs, fh)
    return jsonify(prefs)


@bp.get("/users")
@login_required
def list_users():
    rows = get_db().execute(
        "SELECT id, email, name, role, password FROM users ORDER BY id"
    ).fetchall()
    return jsonify([dict(r) for r in rows])
