import os

from flask import Blueprint, current_app, jsonify, request, send_file

from .auth import login_required
from .config import _safe_join

bp = Blueprint("files", __name__, url_prefix="/files")


def _upload_name(filename):
    """Reduce a client-supplied upload filename to a single safe component.

    Only the basename is kept (so "a/b.txt" and "..\\b.txt" become "b.txt"),
    and empty / "." / ".." results are rejected outright. The result is still
    passed through _safe_join, which re-validates it against an allow-list.
    """
    name = os.path.basename(filename or "")
    if not name or name in (".", ".."):
        raise ValueError("invalid filename")
    # Reject any residual separator (e.g. a Windows-style "..\\x" basename on
    # POSIX) before the name is handed to the path join.
    if os.sep in name or (os.altsep and os.altsep in name):
        raise ValueError("invalid filename")
    return name


@bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "no file"}), 400
    try:
        dest = _safe_join(
            current_app.config["UPLOAD_DIR"], _upload_name(f.filename), "UPLOAD_DIR"
        )
    except ValueError:
        return jsonify({"error": "invalid filename"}), 400
    f.save(dest)
    # Report the sanitized component that was actually written, not the raw
    # client-supplied filename (which may still contain a directory part).
    return jsonify({"name": os.path.basename(dest), "size": os.path.getsize(dest)}), 201


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
