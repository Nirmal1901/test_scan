from flask import Blueprint, jsonify, render_template_string, request, session

from .auth import login_required
from .db import get_db

bp = Blueprint("catalog", __name__, url_prefix="/catalog")


@bp.get("/search")
def search():
    q = request.args.get("q", "")
    category = request.args.get("category", "")
    sql = f"SELECT id, name, price, category FROM products WHERE name LIKE '%{q}%'"
    if category:
        sql += f" AND category = '{category}'"
    sql += " ORDER BY name"
    rows = get_db().execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.get("/products/<int:pid>")
def product(pid):
    row = get_db().execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@bp.get("/products/<int:pid>/card")
def product_card(pid):
    row = get_db().execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    ref = request.args.get("ref", "direct")
    return render_template_string(
        '<div class="card"><h2>'
        + row["name"]
        + "</h2><p>"
        + row["description"]
        + "</p><small>via "
        + ref
        + "</small></div>"
    )


@bp.post("/products")
@login_required
def create_product():
    if session.get("role") != "admin":
        return jsonify({"error": "admin only"}), 403
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    price = data.get("price")
    if not name or price is None:
        return jsonify({"error": "name and price are required"}), 400
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, description, price, category) VALUES (?, ?, ?, ?)",
        (name, data.get("description", ""), float(price), data.get("category", "general")),
    )
    conn.commit()
    return jsonify({"id": cur.lastrowid}), 201
