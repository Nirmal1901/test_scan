import os

from flask import Blueprint, current_app, jsonify, request, send_file

from .auth import login_required
from .config import _safe_join

bp = Blueprint("files", __name__, url_prefix="/files")


@bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "no file"}), 400
    try:
        dest = _safe_join(
            current_app.config["UPLOAD_DIR"], os.path.basename(f.filename), "UPLOAD_DIR"
        )
    except ValueError:
        return jsonify({"error": "invalid filename"}), 400
    f.save(dest)
    return jsonify({"name": f.filename, "size": os.path.getsize(dest)}), 201


@bp.get("/download")
@login_required
def download():
    name = request.args.get("name", "")
    try:
        path = _safe_join(current_app.config["UPLOAD_DIR"], name, "UPLOAD_DIR")
    except ValueError:
        return jsonify({"error": "not found"}), 404
    if not os.path.isfile(path):
        return jsonify({"error": "not found"}), 404
    return send_file(path, as_attachment=True)
