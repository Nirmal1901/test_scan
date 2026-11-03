import os
import pickle

from flask import Blueprint, current_app, jsonify, request, session

from .auth import login_required
from .db import get_db

bp = Blueprint("account", __name__, url_prefix="/account")


def _prefs_path(uid):
    return os.path.join(current_app.config["PREFS_DIR"], str(uid) + ".pkl")


@bp.get("/prefs")
@login_required
def get_prefs():
    path = _prefs_path(session["uid"])
    if not os.path.exists(path):
        return jsonify({})
    with open(path, "rb") as fh:
        return jsonify(pickle.load(fh))


@bp.put("/prefs")
@login_required
def put_prefs():
    prefs = request.get_json(silent=True) or {}
    with open(_prefs_path(session["uid"]), "wb") as fh:
        pickle.dump(prefs, fh)
    return jsonify(prefs)


@bp.get("/users")
@login_required
def list_users():
    rows = get_db().execute(
        "SELECT id, email, name, role, password FROM users ORDER BY id"
    ).fetchall()
    return jsonify([dict(r) for r in rows])
