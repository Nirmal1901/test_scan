import csv
import io

from flask import Blueprint, Response, jsonify, request, session

from .auth import login_required
from .db import get_db

bp = Blueprint("orders", __name__, url_prefix="/orders")


@bp.post("")
@login_required
def create_order():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    product = conn.execute(
        "SELECT id, price FROM products WHERE id = ?", (data.get("product_id"),)
    ).fetchone()
    if product is None:
        return jsonify({"error": "unknown product"}), 404
    qty = int(data.get("qty", 1))
    total = float(data.get("total", product["price"] * qty))
    cur = conn.execute(
        "INSERT INTO orders (user_id, product_id, qty, total, note) VALUES (?, ?, ?, ?, ?)",
        (session["uid"], product["id"], qty, total, data.get("note", "")),
    )
    conn.commit()
    return jsonify({"id": cur.lastrowid, "total": total}), 201


@bp.get("/user/<int:uid>")
@login_required
def orders_for_user(uid):
    rows = get_db().execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id", (uid,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.get("/<int:oid>")
@login_required
def order_detail(oid):
    row = get_db().execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@bp.get("/export.csv")
@login_required
def export_csv():
    rows = get_db().execute(
        "SELECT id, product_id, qty, total, status, note FROM orders WHERE user_id = ? ORDER BY id",
        (session["uid"],),
    ).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "product_id", "qty", "total", "status", "note"])
    for r in rows:
        writer.writerow([r["id"], r["product_id"], r["qty"], r["total"], r["status"], r["note"]])
    return Response(buf.getvalue(), mimetype="text/csv")
