"""ToolContext — the ambient services a tool may reach for at run time.

Tools that set ``wants_context = True`` (or take a ``context`` parameter) receive
this object, giving controlled access to state, memory, events, config, and the
secrets manager without global singletons.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolContext:
    agent_name: Optional[str] = None
    execution_id: Optional[str] = None
    state: Any = None
    memory: Any = None
    events: Any = None
    config: Any = None
    secrets: Any = None
    sandbox_root: Optional[str] = None
    permissions: Any = None
    extra: Dict[str, Any] = field(default_factory=dict)
