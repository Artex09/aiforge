"""Workflow serialization to/from plain dicts and JSON.

Declarative steps (agent, tool, sequence, conditional-with-expression, loop,
parallel, retry, timeout, fallback, set_variable) round-trip fully. Steps backed
by Python callables cannot be reconstructed from data and raise on load.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ..core.errors import WorkflowError
from .base import Step, Workflow
from .steps import (
    AgentStep,
    ConditionalStep,
    FallbackStep,
    LoopStep,
    ParallelStep,
    RetryStep,
    SequenceStep,
    SetVariableStep,
    TimeoutStep,
    ToolStep,
)


def workflow_to_json(workflow: Workflow, indent: int = 2) -> str:
    return json.dumps(workflow.to_dict(), indent=indent, default=str)


def workflow_from_dict(data: Dict[str, Any]) -> Workflow:
    steps = [step_from_dict(s) for s in data.get("steps", [])]
    return Workflow(
        name=data["name"],
        steps=steps,
        description=data.get("description", ""),
        metadata=data.get("metadata", {}),
    )


def workflow_from_json(text: str) -> Workflow:
    return workflow_from_dict(json.loads(text))


def step_from_dict(data: Dict[str, Any]) -> Step:
    stype = data.get("type")
    name = data.get("name", "")
    if stype == "agent":
        return AgentStep(data["agent"], data.get("prompt"), name=name, output_var=data.get("output_var"))
    if stype == "tool":
        return ToolStep(data["tool"], data.get("arguments", {}), name=name, output_var=data.get("output_var"))
    if stype == "set_variable":
        return SetVariableStep(data.get("values", {}), name=name)
    if stype == "sequence":
        return SequenceStep([step_from_dict(s) for s in data.get("steps", [])], name=name)
    if stype == "parallel":
        return ParallelStep(
            [step_from_dict(s) for s in data.get("steps", [])],
            name=name,
            max_workers=data.get("max_workers", 8),
        )
    if stype == "conditional":
        cond = data.get("condition")
        if cond == "<callable>":
            raise WorkflowError("Cannot deserialize a callable condition")
        else_data = data.get("else")
        return ConditionalStep(
            cond,
            step_from_dict(data["then"]),
            step_from_dict(else_data) if else_data else None,
            name=name,
        )
    if stype == "loop":
        return LoopStep(
            step_from_dict(data["body"]),
            over=data.get("over"),
            while_condition=data.get("while"),
            item_var=data.get("item_var", "item"),
            max_iterations=data.get("max_iterations", 100),
            name=name,
        )
    if stype == "retry":
        return RetryStep(step_from_dict(data["step"]), max_retries=data.get("max_retries", 2), name=name)
    if stype == "timeout":
        return TimeoutStep(step_from_dict(data["step"]), timeout=data.get("timeout", 30.0), name=name)
    if stype == "fallback":
        return FallbackStep([step_from_dict(s) for s in data.get("steps", [])], name=name)
    raise WorkflowError(f"Cannot deserialize step of type '{stype}'")
