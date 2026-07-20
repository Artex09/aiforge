"""ExecutionContext — the run-scoped bundle threaded through agents, workflows,
steps, and tools.

Holds temporary variables, a reference to shared state, memory, the event bus,
config, security services, and usage accounting. Child contexts inherit from a
parent for nested workflows.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .types import Usage, new_id


@dataclass
class ExecutionContext:
    id: str = field(default_factory=lambda: new_id("exec"))
    name: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)
    step_count: int = 0
    tool_calls: int = 0
    started_at: float = field(default_factory=time.time)
    parent: Optional["ExecutionContext"] = None

    # Injected services (set by the engine when a run starts).
    state: Any = None
    memory: Any = None
    events: Any = None
    config: Any = None
    secrets: Any = None
    limits: Any = None

    # -------------------------------------------------------------- variables
    def get(self, key: str, default: Any = None) -> Any:
        if key in self.variables:
            return self.variables[key]
        if self.parent is not None:
            return self.parent.get(key, default)
        return default

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def update(self, values: Dict[str, Any]) -> None:
        self.variables.update(values)

    # --------------------------------------------------------------- accounting
    def add_usage(self, usage: Usage) -> None:
        self.usage = self.usage + usage
        if self.parent is not None:
            self.parent.add_usage(usage)

    def tick_step(self) -> int:
        self.step_count += 1
        return self.step_count

    def tick_tool_call(self) -> int:
        self.tool_calls += 1
        return self.tool_calls

    # ------------------------------------------------------------------ nesting
    def child(self, name: str = "") -> "ExecutionContext":
        return ExecutionContext(
            name=name or self.name,
            parent=self,
            metadata=dict(self.metadata),  # carry engine/agents/tools resolvers
            state=self.state,
            memory=self.memory,
            events=self.events,
            config=self.config,
            secrets=self.secrets,
            limits=self.limits,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "variables": self.variables,
            "usage": self.usage.to_dict(),
            "step_count": self.step_count,
            "tool_calls": self.tool_calls,
            "duration": time.time() - self.started_at,
        }
