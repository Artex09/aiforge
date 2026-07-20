"""Utility tools: datetime, JSON handling, text ops, and a guarded shell."""
from __future__ import annotations

import datetime as _dt
import json
import shlex
import subprocess
from typing import Any, Optional

from ..base import Tool, ToolResult, tool
from ..context import ToolContext


@tool(name="current_datetime", description="Return the current UTC date and time (ISO 8601).")
def current_datetime(fmt: str = "iso") -> ToolResult:
    now = _dt.datetime.now(_dt.timezone.utc)
    if fmt == "iso":
        return ToolResult.success(now.isoformat())
    if fmt == "unix":
        return ToolResult.success(now.timestamp())
    return ToolResult.success(now.strftime(fmt))


@tool(name="json_parse", description="Parse a JSON string into an object.")
def json_parse(text: str) -> ToolResult:
    try:
        return ToolResult.success(json.loads(text))
    except json.JSONDecodeError as exc:
        return ToolResult.failure(f"Invalid JSON: {exc}")


@tool(name="json_query", description="Extract a value from JSON by dotted path (e.g. 'a.b.0').")
def json_query(text: str, path: str) -> ToolResult:
    try:
        data: Any = json.loads(text) if isinstance(text, str) else text
    except json.JSONDecodeError as exc:
        return ToolResult.failure(f"Invalid JSON: {exc}")
    cursor = data
    for part in path.split("."):
        if not part:
            continue
        try:
            if isinstance(cursor, list):
                cursor = cursor[int(part)]
            else:
                cursor = cursor[part]
        except (KeyError, IndexError, ValueError, TypeError):
            return ToolResult.failure(f"Path '{path}' not found at segment '{part}'")
    return ToolResult.success(cursor)


@tool(name="summarize_text", description="Naive extractive summary: first N sentences.")
def summarize_text(text: str, sentences: int = 3) -> ToolResult:
    parts = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    summary = ". ".join(parts[: max(1, sentences)])
    if summary and not summary.endswith("."):
        summary += "."
    return ToolResult.success(summary)


@tool(name="word_count", description="Count words and characters in a text.")
def word_count(text: str) -> ToolResult:
    return ToolResult.success({"words": len(text.split()), "chars": len(text)})


class ShellTool(Tool):
    """Run a shell command — disabled unless ``security.allow_shell`` is true."""

    name = "shell"
    description = "Execute a shell command (disabled by default for safety)."
    parameters = {
        "type": "object",
        "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 30}},
        "required": ["command"],
    }
    permissions = ["shell"]
    wants_context = True

    def run(
        self, command: str, timeout: int = 30, context: Optional[ToolContext] = None
    ) -> ToolResult:
        allow = bool(context and context.config and context.config.get("security.allow_shell"))
        if not allow:
            return ToolResult.failure(
                "Shell execution is disabled. Set security.allow_shell=true to enable."
            )
        cwd = (context.sandbox_root if context else None) or None
        try:
            proc = subprocess.run(  # noqa: S603 - explicitly opted in via config
                shlex.split(command),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return ToolResult.success(
                {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
            )
        except subprocess.TimeoutExpired:
            return ToolResult.failure(f"Command timed out after {timeout}s")
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(str(exc))


shell = ShellTool()
