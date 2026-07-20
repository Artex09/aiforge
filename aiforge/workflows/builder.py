"""Fluent workflow builder — an ergonomic way to assemble a :class:`Workflow`."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..core.context import ExecutionContext
from .base import Step, Workflow
from .steps import (
    AgentStep,
    ConditionalStep,
    FallbackStep,
    FunctionStep,
    LoopStep,
    ParallelStep,
    RetryStep,
    SetVariableStep,
    TimeoutStep,
    ToolStep,
)


class WorkflowBuilder:
    def __init__(self, name: str, description: str = ""):
        self._workflow = Workflow(name, description=description)

    # ---------------------------------------------------------------- steps
    def agent(self, agent: str, prompt: Any = None, *, name: str = "", output_var: Optional[str] = None) -> "WorkflowBuilder":
        self._workflow.add(AgentStep(agent, prompt, name=name, output_var=output_var))
        return self

    def tool(self, tool: str, arguments: Optional[Dict[str, Any]] = None, *, name: str = "", output_var: Optional[str] = None) -> "WorkflowBuilder":
        self._workflow.add(ToolStep(tool, arguments, name=name, output_var=output_var))
        return self

    def function(self, fn: Callable[[ExecutionContext], Any], *, name: str = "") -> "WorkflowBuilder":
        self._workflow.add(FunctionStep(fn, name=name))
        return self

    def set(self, values: Dict[str, Any], *, name: str = "") -> "WorkflowBuilder":
        self._workflow.add(SetVariableStep(values, name=name))
        return self

    def condition(self, condition: Any, then_step: Step, else_step: Optional[Step] = None, *, name: str = "") -> "WorkflowBuilder":
        self._workflow.add(ConditionalStep(condition, then_step, else_step, name=name))
        return self

    def parallel(self, steps: List[Step], *, name: str = "", max_workers: int = 8) -> "WorkflowBuilder":
        self._workflow.add(ParallelStep(steps, name=name, max_workers=max_workers))
        return self

    def loop(self, body: Step, *, over: Optional[str] = None, while_condition: Any = None, item_var: str = "item", max_iterations: int = 100, name: str = "") -> "WorkflowBuilder":
        self._workflow.add(
            LoopStep(body, over=over, while_condition=while_condition, item_var=item_var, max_iterations=max_iterations, name=name)
        )
        return self

    def retry(self, step: Step, max_retries: int = 2, *, name: str = "") -> "WorkflowBuilder":
        self._workflow.add(RetryStep(step, max_retries=max_retries, name=name))
        return self

    def timeout(self, step: Step, timeout: float = 30.0, *, name: str = "") -> "WorkflowBuilder":
        self._workflow.add(TimeoutStep(step, timeout=timeout, name=name))
        return self

    def fallback(self, steps: List[Step], *, name: str = "") -> "WorkflowBuilder":
        self._workflow.add(FallbackStep(steps, name=name))
        return self

    def step(self, step: Step) -> "WorkflowBuilder":
        self._workflow.add(step)
        return self

    # ---------------------------------------------------------------- build
    def build(self) -> Workflow:
        self._workflow.ensure_valid()
        return self._workflow
