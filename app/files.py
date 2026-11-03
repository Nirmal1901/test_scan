import os

from flask import Blueprint, current_app, jsonify, request, send_file

from .auth import login_required

bp = Blueprint("files", __name__, url_prefix="/files")


@bp.post("/upload")
@login_required
def upload():
    f = request.files.get("file")
    if f is None or not f.filename:
        return jsonify({"error": "no file"}), 400
    dest = os.path.join(current_app.config["UPLOAD_DIR"], f.filename)
    f.save(dest)
    return jsonify({"name": f.filename, "size": os.path.getsize(dest)}), 201


@bp.get("/download")
@login_required
def download():
    name = request.args.get("name", "")
    path = os.path.join(current_app.config["UPLOAD_DIR"], name)
    if not os.path.isfile(path):
        return jsonify({"error": "not found"}), 404
    return send_file(path, as_attachment=True)
