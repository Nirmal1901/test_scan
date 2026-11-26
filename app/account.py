import json
import os

from flask import Blueprint, current_app, jsonify, request, session

from .auth import login_required
from .config import _safe_join
from .db import get_db

bp = Blueprint("account", __name__, url_prefix="/account")

# Prefs files keep the legacy ".pkl" extension for backward compatibility, but
# their contents are plain JSON (see get_prefs/put_prefs). No pickle is ever
# imported or used here.
PREFS_SUFFIX = ".pkl"


def _prefs_path(uid):
    """Return the prefs file path for a user.

    The file is named "<uid>.pkl" but holds plain JSON, not a pickle. The uid is
    coerced to int so the path component is provably numeric (no ".." or
    separators can survive), then joined through the traversal guard.
    """
    # int() raises on anything non-numeric, so the component below is built
    # only from decimal digits plus the fixed suffix.
    uid = int(uid)
    name = "{}{}".format(uid, PREFS_SUFFIX)
    return _safe_join(current_app.config["PREFS_DIR"], name, "PREFS_DIR")


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
