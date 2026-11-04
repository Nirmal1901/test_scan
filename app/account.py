import json
import os
import re

from flask import Blueprint, current_app, jsonify, request, session

from .auth import login_required
from .db import get_db

bp = Blueprint("account", __name__, url_prefix="/account")

_PREFS_FILE = re.compile(r"[0-9]{1,19}\.json")


def _prefs_path(uid):
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return None
    if not 0 <= uid <= 2**63 - 1:
        return None
    name = "%d.json" % uid
    if not _PREFS_FILE.fullmatch(name):
        return None
    base = os.path.realpath(current_app.config["PREFS_DIR"])
    path = os.path.realpath(os.path.join(base, os.path.basename(name)))
    if os.path.dirname(path) != base:
        return None
    return path


@bp.get("/prefs")
@login_required
def get_prefs():
    path = _prefs_path(session["uid"])
    if path is None or not os.path.exists(path):
        return jsonify({})
    with open(path, "r", encoding="utf-8") as fh:
        return jsonify(json.load(fh))


@bp.put("/prefs")
@login_required
def put_prefs():
    prefs = request.get_json(silent=True) or {}
    path = _prefs_path(session["uid"])
    if path is None:
        return jsonify({"error": "invalid user id"}), 400
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(prefs, fh)
    return jsonify(prefs)


@bp.get("/users")
@login_required
def list_users():
    rows = get_db().execute(
        "SELECT id, email, name, role, password FROM users ORDER BY id"
    ).fetchall()
    return jsonify([dict(r) for r in rows])
