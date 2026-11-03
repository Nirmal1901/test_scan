import sqlite3

from flask import current_app, g

from .security import hash_password

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer',
    reset_code TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price REAL NOT NULL,
    category TEXT NOT NULL DEFAULT 'general'
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty INTEGER NOT NULL DEFAULT 1,
    total REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

PRODUCTS = [
    ("Notebook A5", "Dotted paper, 120 pages", 4.50, "stationery"),
    ("Desk Lamp", "LED lamp with dimmer", 24.00, "home"),
    ("USB-C Cable", "1 m braided cable", 9.90, "electronics"),
    ("Mechanical Keyboard", "Tenkeyless, brown switches", 79.00, "electronics"),
    ("Water Bottle", "750 ml steel bottle", 12.50, "home"),
    ("Wireless Mouse", "Ergonomic, 2.4 GHz", 19.90, "electronics"),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO products (name, description, price, category) VALUES (?, ?, ?, ?)",
            PRODUCTS,
        )
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (email, name, password, role) VALUES (?, ?, ?, 'admin')",
            (
                current_app.config["ADMIN_EMAIL"],
                "Administrator",
                hash_password(current_app.config["ADMIN_PASSWORD"]),
            ),
        )
    conn.commit()
