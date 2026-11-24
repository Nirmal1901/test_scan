import os

from flask import Blueprint, current_app, jsonify, request, send_file

from .auth import login_required

bp = Blueprint("files", __name__, url_prefix="/files")


def _safe_path(name):
    """Resolve a user-supplied file name inside UPLOAD_DIR.

    Returns the absolute path, or None if the name is empty, contains
    directory components, or would resolve outside UPLOAD_DIR.
    """
    if not name:
        return None
    if os.path.basename(name) != name:
        return None
    base = os.path.abspath(current_app.config["UPLOAD_DIR"])
    joined = os.path.abspath(os.path.join(base, name))
    if os.path.commonpath([base, joined]) != base:
        return None
    return joined


@bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "no file"}), 400
    dest = _safe_path(f.filename)
    if dest is None:
        return jsonify({"error": "invalid file name"}), 400
    f.save(dest)
    return jsonify({"name": f.filename, "size": os.path.getsize(dest)}), 201


@bp.get("/download")
@login_required
def download():
    name = request.args.get("name", "")
    path = _safe_path(name)
    if path is None or not os.path.isfile(path):
        return jsonify({"error": "not found"}), 404
    return send_file(path, as_attachment=True)
