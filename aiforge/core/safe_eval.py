"""Safe expression evaluation for workflow conditions.

This exists to close an RCE class of bug: workflow conditions used to be run
through :func:`eval`, and stripping ``__builtins__`` does **not** make ``eval``
safe (the evaluated objects can reach builtins back through their attributes).

Instead we parse the expression to an AST and interpret only an explicit
allow-list of node types: literals, names (resolved from a supplied variable
mapping), comparisons, boolean/unary logic, membership, subscripting, and simple
arithmetic. There is **no** function-call, attribute-access, comprehension, or
name resolution outside the provided variables — so there is no path to any
object, module, or builtin.
"""
from __future__ import annotations

import ast
import operator
from typing import Any, Dict

from .errors import ValidationError

_CMP = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}
_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Not: operator.not_,
}

_MISSING = object()


def safe_eval(expression: str, variables: Dict[str, Any]) -> Any:
    """Evaluate *expression* against *variables* with no access to code.

    Raises :class:`ValidationError` for anything outside the allow-list or for an
    undefined variable reference.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValidationError(f"Invalid expression '{expression}': {exc}") from exc
    return _eval(tree.body, variables)


def _eval(node: ast.AST, vars: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        value = vars.get(node.id, _MISSING)
        if value is _MISSING:
            raise ValidationError(f"Unknown variable '{node.id}' in condition")
        return value

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result: Any = True
            for value in node.values:
                result = _eval(value, vars)
                if not result:
                    return result
            return result
        # Or
        result = False
        for value in node.values:
            result = _eval(value, vars)
            if result:
                return result
        return result

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand, vars))

    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_eval(node.left, vars), _eval(node.right, vars))

    if isinstance(node, ast.Compare):
        left = _eval(node.left, vars)
        for op, comparator in zip(node.ops, node.comparators):
            handler = _CMP.get(type(op))
            if handler is None:
                raise ValidationError(f"Comparison '{type(op).__name__}' is not allowed")
            right = _eval(comparator, vars)
            if not handler(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Subscript):
        container = _eval(node.value, vars)
        key = _eval(node.slice, vars)
        try:
            return container[key]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValidationError(f"Subscript failed: {exc}") from exc

    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(el, vars) for el in node.elts]

    raise ValidationError(
        f"Expression element '{type(node).__name__}' is not permitted in conditions"
    )
