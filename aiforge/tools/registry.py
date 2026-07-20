"""Tool registry: registration, discovery, validation, permission enforcement,
and instrumented execution.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from ..core.errors import ToolError, ToolNotFoundError, ToolPermissionError
from ..events.bus import EventBus, EventType
from .base import FunctionTool, Tool, ToolResult
from .context import ToolContext


class ToolRegistry:
    def __init__(self, events: Optional[EventBus] = None):
        self._tools: Dict[str, Tool] = {}
        self._events = events
        self._lock = threading.RLock()

    # -------------------------------------------------------------- register
    def register(self, tool: Tool) -> Tool:
        if not tool.name:
            raise ToolError("Tool must have a name")
        with self._lock:
            self._tools[tool.name] = tool
        return tool

    def register_function(self, func: Callable[..., Any], **kwargs: Any) -> Tool:
        if isinstance(func, Tool):
            return self.register(func)
        return self.register(FunctionTool(func, **kwargs))

    def unregister(self, name: str) -> None:
        with self._lock:
            self._tools.pop(name, None)

    # ------------------------------------------------------------------ query
    def get(self, name: str) -> Tool:
        with self._lock:
            if name not in self._tools:
                raise ToolNotFoundError(f"Tool '{name}' is not registered")
            return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> List[Tool]:
        with self._lock:
            return list(self._tools.values())

    def names(self) -> List[str]:
        with self._lock:
            return list(self._tools)

    def schemas(self, names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """OpenAI-style tool schemas for the given tools (or all)."""
        tools = [self.get(n) for n in names] if names else self.list()
        return [t.schema.to_openai() for t in tools]

    # --------------------------------------------------------------- discover
    def discover(self, package: str) -> List[str]:
        """Import *package* recursively and register any ``Tool`` instances or
        ``@tool``-decorated callables found at module top level."""
        found: List[str] = []
        pkg = importlib.import_module(package)
        modules = [package]
        if hasattr(pkg, "__path__"):
            for info in pkgutil.walk_packages(pkg.__path__, prefix=f"{package}."):
                modules.append(info.name)
        for mod_name in modules:
            module = importlib.import_module(mod_name)
            for _, obj in inspect.getmembers(module):
                if isinstance(obj, Tool) and obj.name and not self.has(obj.name):
                    self.register(obj)
                    found.append(obj.name)
        return found

    # ---------------------------------------------------------------- execute
    def execute(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        *,
        context: Optional[ToolContext] = None,
        allowed: Optional[List[str]] = None,
    ) -> ToolResult:
        """Validate permissions + arguments, then run the tool with events."""
        tool = self.get(name)
        arguments = arguments or {}

        self._check_permissions(tool, allowed, context)
        validated = tool.validate(arguments)

        self._emit(EventType.TOOL_START, name, {"arguments": validated})
        started = time.time()
        try:
            if tool.wants_context or self._takes_context(tool):
                result = tool.run(context=context, **validated)
            else:
                result = tool.run(**validated)
            if not isinstance(result, ToolResult):
                result = ToolResult.success(result)
        except Exception as exc:  # noqa: BLE001 - normalise to ToolResult + event
            self._emit(EventType.TOOL_ERROR, name, {"error": str(exc)})
            return ToolResult.failure(str(exc), tool=name)
        finally:
            elapsed = time.time() - started

        self._emit(
            EventType.TOOL_END,
            name,
            {"ok": result.ok, "duration": elapsed, "output": _truncate(result.output)},
        )
        result.metadata.setdefault("duration", elapsed)
        return result

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _takes_context(tool: Tool) -> bool:
        try:
            params = inspect.signature(tool.run).parameters
        except (TypeError, ValueError):
            return False
        return "context" in params

    def _check_permissions(
        self, tool: Tool, allowed: Optional[List[str]], context: Optional[ToolContext]
    ) -> None:
        # Tool-level required permissions checked against the caller's grants.
        if context is not None and context.permissions is not None:
            for perm in tool.permissions:
                if not context.permissions.has(perm):
                    raise ToolPermissionError(
                        f"Tool '{tool.name}' requires permission '{perm}'"
                    )
        # Caller allowlist of tool names (agent scoping).
        if allowed is not None and tool.name not in allowed:
            raise ToolPermissionError(
                f"Tool '{tool.name}' is not in the caller's allowed tools"
            )

    def _emit(self, etype: EventType, name: str, data: Dict[str, Any]) -> None:
        if self._events is not None:
            self._events.emit(etype, {"tool": name, **data}, source=f"tool:{name}")


def _truncate(value: Any, limit: int = 500) -> Any:
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= limit else text[:limit] + "…"
