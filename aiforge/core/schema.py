"""Minimal JSON-Schema validation for structured LLM outputs.

Supports the subset that matters for function-calling / structured output:
``type`` (object/array/string/number/integer/boolean/null), ``properties``,
``required``, ``items``, and ``enum``. Dependency-free.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .errors import ValidationError

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate_against_schema(data: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    """Return a list of problems ([] means valid)."""
    problems: List[str] = []
    expected = schema.get("type")

    if expected:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_TYPE_CHECKS.get(t, lambda _v: True)(data) for t in types):
            problems.append(f"{path}: expected {expected}, got {type(data).__name__}")
            return problems  # type mismatch -> deeper checks are meaningless

    if "enum" in schema and data not in schema["enum"]:
        problems.append(f"{path}: {data!r} not in enum {schema['enum']}")

    if expected == "object" or (isinstance(data, dict) and "properties" in schema):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in data:
                problems.append(f"{path}: missing required '{key}'")
        for key, sub in props.items():
            if key in data:
                problems.extend(validate_against_schema(data[key], sub, f"{path}.{key}"))

    if expected == "array" and "items" in schema and isinstance(data, list):
        for i, item in enumerate(data):
            problems.extend(validate_against_schema(item, schema["items"], f"{path}[{i}]"))

    return problems


def ensure_valid(data: Any, schema: Dict[str, Any]) -> Any:
    problems = validate_against_schema(data, schema)
    if problems:
        raise ValidationError("Structured output failed schema validation", details={"problems": problems})
    return data
