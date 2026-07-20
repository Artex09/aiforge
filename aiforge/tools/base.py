"""Tool primitives: schema, result, base Tool, and the ``@tool`` decorator.

Tools are the framework's "Tool-first" unit of action. A tool declares a JSON
schema (auto-derived from a function signature when using ``@tool``), a set of
required permissions, and a ``run`` implementation. Arguments are validated
against the schema before execution.
"""
from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, get_args, get_origin

from ..core.errors import ToolValidationError

_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}

# Handles string annotations produced by ``from __future__ import annotations``.
_NAME_TO_JSON = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "List": "array",
    "dict": "object",
    "Dict": "object",
}


@dataclass
class ToolResult:
    ok: bool = True
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "output": self.output, "error": self.error, "metadata": self.metadata}

    @classmethod
    def success(cls, output: Any, **meta: Any) -> "ToolResult":
        return cls(ok=True, output=output, metadata=meta)

    @classmethod
    def failure(cls, error: str, **meta: Any) -> "ToolResult":
        return cls(ok=False, error=error, metadata=meta)


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_openai(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class Tool:
    """Base class for all tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}
    permissions: List[str] = []
    #: When True, ``run`` receives a ``context`` keyword with the ToolContext.
    wants_context: bool = False

    def __init__(self, name: str = "", description: str = "", permissions: Optional[List[str]] = None):
        if name:
            self.name = name
        if description:
            self.description = description
        if permissions is not None:
            self.permissions = permissions

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(self.name, self.description, self.parameters)

    def validate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate/coerce *arguments* against the parameter schema."""
        return validate_arguments(self.parameters, arguments, self.name)

    def run(self, **kwargs: Any) -> ToolResult:  # pragma: no cover - abstract
        raise NotImplementedError(f"Tool '{self.name}' does not implement run()")

    def __call__(self, **kwargs: Any) -> ToolResult:
        return self.run(**kwargs)


class FunctionTool(Tool):
    """A Tool backed by a plain Python callable."""

    def __init__(
        self,
        func: Callable[..., Any],
        name: str = "",
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        permissions: Optional[List[str]] = None,
        wants_context: bool = False,
    ):
        super().__init__(
            name=name or func.__name__,
            description=description or (inspect.getdoc(func) or "").strip(),
            permissions=permissions or [],
        )
        self._func = func
        self.parameters = parameters or derive_schema(func)
        self.wants_context = wants_context

    def run(self, **kwargs: Any) -> ToolResult:
        result = self._func(**kwargs)
        if isinstance(result, ToolResult):
            return result
        return ToolResult.success(result)


def derive_schema(func: Callable[..., Any]) -> Dict[str, Any]:
    """Build a JSON schema from a function signature and annotations.

    Resolves string annotations (from ``from __future__ import annotations``)
    back into real types where possible.
    """
    sig = inspect.signature(func)
    try:
        hints = typing.get_type_hints(func)
    except Exception:  # noqa: BLE001 - unresolved forward refs fall back to raw
        hints = {}
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for pname, param in sig.parameters.items():
        if pname in {"self", "context", "ctx"}:
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        annotation = hints.get(pname, param.annotation)
        properties[pname] = _annotation_to_schema(annotation)
        if param.default is inspect.Parameter.empty:
            required.append(pname)
        else:
            properties[pname]["default"] = param.default
    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _annotation_to_schema(annotation: Any) -> Dict[str, Any]:
    if annotation is inspect.Parameter.empty:
        return {"type": "string"}
    if isinstance(annotation, str):
        # Unresolved string annotation (e.g. "int", "List[str]").
        base = annotation.split("[", 1)[0]
        if base in ("list", "List"):
            return {"type": "array", "items": {"type": "string"}}
        return {"type": _NAME_TO_JSON.get(base, "string")}
    origin = get_origin(annotation)
    if origin in (list, List):
        args = get_args(annotation)
        item = _annotation_to_schema(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item}
    if origin in (dict, Dict):
        return {"type": "object"}
    return {"type": _PY_TO_JSON.get(annotation, "string")}


def validate_arguments(
    schema: Dict[str, Any], arguments: Dict[str, Any], tool_name: str = ""
) -> Dict[str, Any]:
    """Lightweight JSON-schema-ish validation with type coercion."""
    props = schema.get("properties", {})
    required = schema.get("required", [])
    result: Dict[str, Any] = {}

    for key in required:
        if key not in arguments:
            raise ToolValidationError(
                f"Missing required argument '{key}' for tool '{tool_name}'"
            )

    for key, value in arguments.items():
        spec = props.get(key)
        if spec is None:
            result[key] = value  # tolerate extras
            continue
        result[key] = _coerce_value(value, spec, key, tool_name)

    # fill defaults
    for key, spec in props.items():
        if key not in result and "default" in spec:
            result[key] = spec["default"]
    return result


def _coerce_value(value: Any, spec: Dict[str, Any], key: str, tool: str) -> Any:
    expected = spec.get("type")
    try:
        if expected == "integer" and not isinstance(value, bool):
            return int(value)
        if expected == "number" and not isinstance(value, bool):
            return float(value)
        if expected == "boolean":
            if isinstance(value, str):
                return value.strip().lower() in {"true", "1", "yes"}
            return bool(value)
        if expected == "string":
            return value if isinstance(value, str) else str(value)
    except (TypeError, ValueError) as exc:
        raise ToolValidationError(
            f"Argument '{key}' for tool '{tool}' expected {expected}: {exc}"
        ) from exc
    return value


def tool(
    name: str = "",
    description: str = "",
    permissions: Optional[List[str]] = None,
    wants_context: bool = False,
) -> Callable[[Callable[..., Any]], FunctionTool]:
    """Decorator turning a function into a :class:`FunctionTool`.

    Example::

        @tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b
    """

    def _decorator(func: Callable[..., Any]) -> FunctionTool:
        return FunctionTool(
            func,
            name=name,
            description=description,
            permissions=permissions,
            wants_context=wants_context,
        )

    return _decorator
