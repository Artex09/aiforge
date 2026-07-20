"""Workflow primitives: Step, StepResult, and the Workflow container."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.context import ExecutionContext
from ..core.errors import WorkflowError
from ..core.types import new_id


@dataclass
class StepResult:
    output: Any = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any = None, **meta: Any) -> "StepResult":
        return cls(output=output, success=True, metadata=meta)

    @classmethod
    def fail(cls, error: str, **meta: Any) -> "StepResult":
        return cls(success=False, error=error, metadata=meta)


class Step(abc.ABC):
    """A unit of work in a workflow. Reads/writes the shared context and
    returns a :class:`StepResult`."""

    #: Type tag used for serialization; concrete steps override.
    type: str = "step"

    def __init__(self, name: str = ""):
        self.name = name or f"{type(self).__name__.lower()}_{new_id('')[:6]}"

    @abc.abstractmethod
    def execute(self, context: ExecutionContext) -> StepResult: ...

    def validate(self) -> List[str]:
        """Return a list of validation problems ([] means valid)."""
        return []

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "name": self.name}

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.name}>"


class Workflow:
    """An ordered collection of steps plus metadata and validation."""

    def __init__(
        self,
        name: str,
        steps: Optional[List[Step]] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = new_id("wf")
        self.name = name
        self.description = description
        self.steps: List[Step] = steps or []
        self.metadata = metadata or {}

    def add(self, step: Step) -> "Workflow":
        self.steps.append(step)
        return self

    def validate(self) -> List[str]:
        problems: List[str] = []
        if not self.name:
            problems.append("workflow has no name")
        if not self.steps:
            problems.append("workflow has no steps")
        seen: set = set()
        for step in self.steps:
            if step.name in seen:
                problems.append(f"duplicate step name '{step.name}'")
            seen.add(step.name)
            problems.extend(f"{step.name}: {p}" for p in step.validate())
        return problems

    def ensure_valid(self) -> None:
        problems = self.validate()
        if problems:
            raise WorkflowError("Invalid workflow", details={"problems": problems})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "steps": [s.to_dict() for s in self.steps],
        }
