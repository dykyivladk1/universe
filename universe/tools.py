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


