"""Safe arithmetic calculator using an AST allowlist (no ``eval``)."""
from __future__ import annotations

import ast
import math
import operator
from typing import Any

from ..base import ToolResult, tool

#: Reject results with more digits than this to avoid multi-second/GB exponents
#: (e.g. ``9**9**9``), which would otherwise hang the process.
_MAX_RESULT_DIGITS = 1000


def _safe_pow(base: Any, exp: Any) -> Any:
    if isinstance(base, (int, float)) and isinstance(exp, (int, float)) and exp > 0:
        magnitude = abs(base)
        if magnitude > 1:
            digits = float(exp) * math.log10(magnitude)
            if digits > _MAX_RESULT_DIGITS:
                raise ValueError("exponent too large")
    return operator.pow(base, exp)


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: _safe_pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "exp": math.exp,
    "min": min,
    "max": max,
}
_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("only numeric constants are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"function '{node.func.id}' is not permitted")
        return fn(*[_eval(a) for a in node.args])
    raise ValueError(f"unsupported expression: {ast.dump(node)}")


@tool(description="Evaluate a mathematical expression safely (e.g. '2 * (3 + 4)').")
def calculator(expression: str) -> ToolResult:
    try:
        tree = ast.parse(expression, mode="eval")
        return ToolResult.success(_eval(tree))
    except Exception as exc:  # noqa: BLE001 - report calc errors as tool failures
        return ToolResult.failure(f"Could not evaluate '{expression}': {exc}")
