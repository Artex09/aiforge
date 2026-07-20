"""Core: engine, types, errors, context, state, security, monitoring.

``Engine`` is exposed lazily (via module ``__getattr__``) to avoid an import
cycle — the engine composes agents/workflows, which in turn import ``core``.
"""
from typing import Any

from .context import ExecutionContext
from .errors import AIForgeError
from .types import LLMResponse, Message, Role, RunResult, ToolCall, Usage

__all__ = [
    "Engine",
    "ExecutionContext",
    "AIForgeError",
    "Message",
    "Role",
    "ToolCall",
    "LLMResponse",
    "RunResult",
    "Usage",
]


def __getattr__(name: str) -> Any:  # PEP 562 lazy attribute
    if name == "Engine":
        from .engine import Engine

        return Engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
