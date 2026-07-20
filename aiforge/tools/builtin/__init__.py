"""Built-in tool collection and bulk registration helper."""
from __future__ import annotations

from typing import List

from ..base import Tool
from ..registry import ToolRegistry
from .calculator import calculator
from .files import list_dir, read_file, write_file
from .utility import (
    current_datetime,
    json_parse,
    json_query,
    shell,
    summarize_text,
    word_count,
)
from .web import http_request, web_search

#: All built-in tools shipped with AIForge.
BUILTIN_TOOLS: List[Tool] = [
    calculator,
    read_file,
    write_file,
    list_dir,
    http_request,
    web_search,
    current_datetime,
    json_parse,
    json_query,
    summarize_text,
    word_count,
    shell,
]


def register_builtins(registry: ToolRegistry, include_shell: bool = True) -> List[str]:
    """Register every built-in tool into *registry*; return the names added."""
    names: List[str] = []
    for tool in BUILTIN_TOOLS:
        if tool.name == "shell" and not include_shell:
            continue
        registry.register(tool)
        names.append(tool.name)
    return names


__all__ = ["BUILTIN_TOOLS", "register_builtins"]
