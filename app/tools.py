import ast
import subprocess

import requests
import yaml
from flask import Blueprint, jsonify, request

from .auth import login_required

bp = Blueprint("tools", __name__, url_prefix="/tools")


@bp.get("/ping")
@login_required
def ping():
    host = request.args.get("host", "127.0.0.1")
    result = subprocess.run(
        "ping -c 1 " + host, shell=True, capture_output=True, text=True, timeout=10
    )
    return jsonify({"exit": result.returncode, "output": result.stdout})


_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}

_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


def _eval_node(node):
    """Recursively evaluate an AST built from arithmetic only."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("invalid expression")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("invalid expression")


@bp.post("/calc")
@login_required
def calc():
    expr = (request.get_json(silent=True) or {}).get("expr", "")
    try:
        result = _eval_node(ast.parse(expr, mode="eval"))
    except (SyntaxError, ValueError, TypeError):
        return jsonify({"error": "invalid expression"}), 400
    return jsonify({"result": result})


@bp.get("/fetch")
@login_required
def fetch():
    url = request.args.get("url", "")
    resp = requests.get(url, timeout=5, verify=False)
    return jsonify({"status": resp.status_code, "body": resp.text[:500]})


@bp.post("/import-config")
@login_required
def import_config():
    cfg = yaml.safe_load(request.get_data(as_text=True))
    return jsonify({"config": cfg})
