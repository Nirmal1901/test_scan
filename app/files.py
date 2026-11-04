import os
import re

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from .auth import login_required

bp = Blueprint("files", __name__, url_prefix="/files")

# Allowlist for a stored file name: must start alphanumeric, then only
# alphanumerics, dot, underscore, dash. Rejects ".", "..", and any separator.
_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}")


def _upload_path(name):
    name = secure_filename(name or "")
    if not name or not _SAFE_NAME.fullmatch(name):
        return None
    component = os.path.basename(name)
    if not _SAFE_NAME.fullmatch(component):
        return None
    base = os.path.realpath(current_app.config["UPLOAD_DIR"])
    path = os.path.realpath(os.path.join(base, component))
    return path if os.path.dirname(path) == base else None


@bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "no file"}), 400
    dest = _upload_path(f.filename)
    if dest is None:
        return jsonify({"error": "bad filename"}), 400
    f.save(dest)
    return jsonify({"name": os.path.basename(dest), "size": os.path.getsize(dest)}), 201


@bp.get("/download")
@login_required
def download():
    path = _upload_path(request.args.get("name", ""))
    if path is None or not os.path.isfile(path):
        return jsonify({"error": "not found"}), 404
    return send_file(path, as_attachment=True)
