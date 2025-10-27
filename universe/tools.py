"""Built-in tools agents can pick from.

To add a new one: write a function with @tool and put it in TOOLS.
The docstring matters, the model reads it to decide when to call the tool.
"""
import ast
import operator
import re
import urllib.request
from datetime import datetime

from langchain_core.tools import tool

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("only basic math is allowed")


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression like '12 * (3 + 4) / 2'. Use it for any arithmetic."""
    try:
        # not using eval() on purpose, the model could send anything here
        result = _eval(ast.parse(expression, mode="eval").body)
        return str(result)
    except Exception as e:
        return f"Could not calculate: {e}"


@tool
def current_datetime() -> str:
    """Get the current local date and time."""
    return datetime.now().strftime("%A, %Y-%m-%d %H:%M")


@tool
