"""Sandboxed filesystem tools.

All paths are resolved *inside* the context's sandbox root (or the process CWD
if none is supplied) and traversal outside the sandbox is rejected. These tools
declare the ``fs`` permission.
"""
from __future__ import annotations

import os
from typing import Optional

from ..base import Tool, ToolResult
from ..context import ToolContext


def _resolve(context: Optional[ToolContext], path: str) -> str:
    # realpath (not abspath) resolves symlinks, so a symlink planted inside the
    # sandbox cannot be used to read/write files outside it.
    root = os.path.realpath((context.sandbox_root if context else None) or os.getcwd())
    target = os.path.realpath(os.path.join(root, path))
    if not (target == root or target.startswith(root + os.sep)):
        raise ValueError(f"Path '{path}' escapes the sandbox root")
    return target


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a UTF-8 text file from the sandbox."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    permissions = ["fs"]
    wants_context = True

    def run(self, path: str, context: Optional[ToolContext] = None) -> ToolResult:
        try:
            target = _resolve(context, path)
            with open(target, "r", encoding="utf-8") as fh:
                return ToolResult.success(fh.read())
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(str(exc))


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write UTF-8 text to a file in the sandbox (creates directories)."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    }
    permissions = ["fs"]
    wants_context = True

    def run(self, path: str, content: str, context: Optional[ToolContext] = None) -> ToolResult:
        try:
            target = _resolve(context, path)
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(content)
            return ToolResult.success({"path": target, "bytes": len(content)})
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(str(exc))


class ListDirTool(Tool):
    name = "list_dir"
    description = "List entries of a directory in the sandbox."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "default": "."}},
    }
    permissions = ["fs"]
    wants_context = True

    def run(self, path: str = ".", context: Optional[ToolContext] = None) -> ToolResult:
        try:
            target = _resolve(context, path)
            entries = [
                {"name": n, "is_dir": os.path.isdir(os.path.join(target, n))}
                for n in sorted(os.listdir(target))
            ]
            return ToolResult.success(entries)
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(str(exc))


read_file = ReadFileTool()
write_file = WriteFileTool()
list_dir = ListDirTool()
