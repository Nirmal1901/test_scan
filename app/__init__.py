import os
import traceback

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from . import config, db


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config)
    if test_config:
        app.config.update(test_config)

    for key in ("UPLOAD_DIR", "PREFS_DIR"):
        os.makedirs(app.config[key], exist_ok=True)
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.init_db()

    from . import account, auth, catalog, files, orders, tools

    for bp in (auth.bp, catalog.bp, orders.bp, files.bp, tools.bp, account.bp):
        app.register_blueprint(bp)

    @app.get("/")
    def index():
        return jsonify({"service": "shopdesk", "status": "ok"})

    @app.errorhandler(Exception)
    def on_error(exc):
        if isinstance(exc, HTTPException):
            return exc
        return jsonify({"error": str(exc), "trace": traceback.format_exc()}), 500

    return app
