import os

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from .auth import login_required

bp = Blueprint("files", __name__, url_prefix="/files")


@bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "no file"}), 400
    safe_name = secure_filename(f.filename)
    if not safe_name:
        return jsonify({"error": "invalid file name"}), 400
    dest = os.path.join(current_app.config["UPLOAD_DIR"], safe_name)
    f.save(dest)
    return jsonify({"name": safe_name, "size": os.path.getsize(dest)}), 201


@bp.get("/download")
@login_required
def download():
    name = secure_filename(request.args.get("name", ""))
    if not name:
        return jsonify({"error": "not found"}), 404
    upload_root = os.path.realpath(current_app.config["UPLOAD_DIR"])
    path = os.path.realpath(os.path.join(upload_root, name))
    try:
        inside = os.path.commonpath([path, upload_root]) == upload_root
    except ValueError:
        inside = False
    if not inside or not os.path.isfile(path):
        return jsonify({"error": "not found"}), 404
    return send_file(path, as_attachment=True)
