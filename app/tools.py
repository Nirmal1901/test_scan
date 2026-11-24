import ast
import operator
import subprocess

import requests
import yaml
from flask import Blueprint, jsonify, request

from .auth import login_required

bp = Blueprint("tools", __name__, url_prefix="/tools")

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("unsupported constant")
        return node.value
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError("unsupported operator")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError("unsupported operator")
        return op(_eval_node(node.operand))
    raise ValueError("unsupported expression")


def safe_eval(expr):
    """Evaluate a pure arithmetic expression without executing arbitrary code."""
    if not isinstance(expr, str):
        raise ValueError("expression must be a string")
    return _eval_node(ast.parse(expr, mode="eval"))


@bp.get("/ping")
@login_required
def ping():
    host = request.args.get("host", "127.0.0.1")
    result = subprocess.run(
        "ping -c 1 " + host, shell=True, capture_output=True, text=True, timeout=10
    )
    return jsonify({"exit": result.returncode, "output": result.stdout})


@bp.post("/calc")
@login_required
def calc():
    expr = (request.get_json(silent=True) or {}).get("expr", "")
    try:
        result = safe_eval(expr)
    except (ValueError, SyntaxError, TypeError, ZeroDivisionError, OverflowError):
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
