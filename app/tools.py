import ast
import subprocess

import requests
import yaml
from flask import Blueprint, jsonify, request

from .auth import login_required

bp = Blueprint("tools", __name__, url_prefix="/tools")


class _ArithmeticEvaluator(ast.NodeVisitor):
    """Evaluate a purely numeric expression, rejecting any other syntax."""

    def evaluate(self, expr):
        return self.visit(ast.parse(expr, mode="eval"))

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("non-numeric constant")
        return node.value

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            if abs(right) > 1000:
                raise ValueError("exponent too large")
            return left ** right
        raise ValueError("operator not allowed")

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError("operator not allowed")

    def generic_visit(self, node):
        raise ValueError("disallowed expression")


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
        result = _ArithmeticEvaluator().evaluate(expr)
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError):
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
    try:
        cfg = yaml.safe_load(request.get_data(as_text=True))
    except yaml.YAMLError:
        return jsonify({"error": "invalid config"}), 400
    return jsonify({"config": cfg})
