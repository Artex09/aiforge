"""Tool chaining — pipe the output of one tool into the input of the next."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import ToolResult
from .context import ToolContext
from .registry import ToolRegistry


@dataclass
class ChainStep:
    tool: str
    #: Static arguments merged with the mapped input.
    arguments: Dict[str, Any] = field(default_factory=dict)
    #: Maps the previous step's output into this step's argument dict.
    map_input: Optional[Callable[[Any], Dict[str, Any]]] = None


class ToolChain:
    """An ordered sequence of tool invocations forming a pipeline."""

    def __init__(self, registry: ToolRegistry, steps: Optional[List[ChainStep]] = None):
        self.registry = registry
        self.steps: List[ChainStep] = steps or []

    def add(
        self,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        map_input: Optional[Callable[[Any], Dict[str, Any]]] = None,
    ) -> "ToolChain":
        self.steps.append(ChainStep(tool, arguments or {}, map_input))
        return self

    def run(
        self,
        initial: Optional[Dict[str, Any]] = None,
        *,
        context: Optional[ToolContext] = None,
    ) -> ToolResult:
        payload: Dict[str, Any] = dict(initial or {})
        last = ToolResult.success(None)
        for step in self.steps:
            args = dict(step.arguments)
            if step.map_input is not None:
                args.update(step.map_input(last.output))
            else:
                args.update(payload)
            last = self.registry.execute(step.tool, args, context=context)
            if not last.ok:
                return last  # short-circuit on failure
            payload = {"input": last.output}
        return last
