"""Concrete workflow steps.

Covers the catalog's Workflow Engine surface: Sequential, Conditional, Parallel,
Nested, Loops, Retries, Timeouts, Fallback Paths, and Branching. Steps reach
agents/tools via services placed on the execution context by the engine.
"""
from __future__ import annotations

import concurrent.futures
import threading
from typing import Any, Callable, Dict, List, Optional, Union

from ..core.context import ExecutionContext
from ..core.errors import StepError
from ..core.types import Message
from .base import Step, StepResult, Workflow

Condition = Union[str, Callable[[ExecutionContext], bool]]


def _resolve_input(context: ExecutionContext, spec: Any) -> Any:
    """Resolve an input spec: ``{"$var": "name"}`` reads a context variable,
    ``{"$last": true}`` reads the previous step output, otherwise literal."""
    if isinstance(spec, dict):
        if "$var" in spec:
            return context.get(spec["$var"])
        if "$last" in spec:
            return context.get("__last__")
        return {k: _resolve_input(context, v) for k, v in spec.items()}
    if isinstance(spec, str) and spec.startswith("$"):
        return context.get(spec[1:])
    return spec


def _eval_condition(condition: Condition, context: ExecutionContext) -> bool:
    if callable(condition):
        return bool(condition(context))
    # String conditions are evaluated by a safe AST interpreter (no eval, no
    # calls, no attribute access) against the context variables by name.
    from ..core.safe_eval import safe_eval

    try:
        return bool(safe_eval(condition, dict(context.variables)))
    except Exception as exc:  # noqa: BLE001
        raise StepError(f"Failed to evaluate condition '{condition}': {exc}") from exc


class FunctionStep(Step):
    """Run an arbitrary Python callable ``fn(context) -> Any``."""

    type = "function"

    def __init__(self, fn: Callable[[ExecutionContext], Any], name: str = ""):
        super().__init__(name)
        self.fn = fn

    def execute(self, context: ExecutionContext) -> StepResult:
        try:
            return StepResult.ok(self.fn(context))
        except Exception as exc:  # noqa: BLE001
            return StepResult.fail(str(exc))


class SetVariableStep(Step):
    """Assign values into context variables."""

    type = "set_variable"

    def __init__(self, values: Dict[str, Any], name: str = ""):
        super().__init__(name)
        self.values = values

    def execute(self, context: ExecutionContext) -> StepResult:
        resolved = {k: _resolve_input(context, v) for k, v in self.values.items()}
        context.update(resolved)
        return StepResult.ok(resolved)

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "values": self.values}


class AgentStep(Step):
    """Invoke a registered agent with a (templated) prompt."""

    type = "agent"

    def __init__(
        self,
        agent: str,
        prompt: Any = None,
        name: str = "",
        output_var: Optional[str] = None,
    ):
        super().__init__(name)
        self.agent = agent
        self.prompt = prompt
        self.output_var = output_var

    def execute(self, context: ExecutionContext) -> StepResult:
        agents = context.metadata.get("agents")
        if agents is None or not agents.has(self.agent):
            return StepResult.fail(f"Agent '{self.agent}' not available")
        prompt = _resolve_input(context, self.prompt)
        if prompt is None:
            prompt = context.get("__last__") or context.get("input", "")
        prompt = self._render(str(prompt), context)
        child = context.child(self.agent)
        result = agents.get(self.agent).run(prompt, context=child)
        if self.output_var:
            context.set(self.output_var, result.output)
        return StepResult(output=result.output, success=result.success, error=result.error)

    @staticmethod
    def _render(template: str, context: ExecutionContext) -> str:
        out = template
        for key, value in context.variables.items():
            out = out.replace("{" + key + "}", str(value))
        return out

    def validate(self) -> List[str]:
        return [] if self.agent else ["agent step requires an agent name"]

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "agent": self.agent, "prompt": self.prompt, "output_var": self.output_var}


class ToolStep(Step):
    """Invoke a registered tool directly."""

    type = "tool"

    def __init__(
        self,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        name: str = "",
        output_var: Optional[str] = None,
    ):
        super().__init__(name)
        self.tool = tool
        self.arguments = arguments or {}
        self.output_var = output_var

    def execute(self, context: ExecutionContext) -> StepResult:
        tools = context.metadata.get("tools")
        if tools is None or not tools.has(self.tool):
            return StepResult.fail(f"Tool '{self.tool}' not available")
        args = {k: _resolve_input(context, v) for k, v in self.arguments.items()}
        result = tools.execute(self.tool, args, context=context.metadata.get("tool_context"))
        if self.output_var and result.ok:
            context.set(self.output_var, result.output)
        return StepResult(output=result.output, success=result.ok, error=result.error)

    def validate(self) -> List[str]:
        return [] if self.tool else ["tool step requires a tool name"]

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "tool": self.tool, "arguments": self.arguments, "output_var": self.output_var}


class SequenceStep(Step):
    """Run child steps in order, threading each output into ``__last__``."""

    type = "sequence"

    def __init__(self, steps: List[Step], name: str = ""):
        super().__init__(name)
        self.steps = steps

    def execute(self, context: ExecutionContext) -> StepResult:
        last: StepResult = StepResult.ok(context.get("__last__"))
        for step in self.steps:
            last = step.execute(context)
            context.set("__last__", last.output)
            context.set(step.name, last.output)
            if not last.success:
                return last
        return last

    def validate(self) -> List[str]:
        problems: List[str] = []
        for step in self.steps:
            problems.extend(step.validate())
        return problems

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "steps": [s.to_dict() for s in self.steps]}


class ConditionalStep(Step):
    """Branch to ``then_step`` or ``else_step`` based on a condition."""

    type = "conditional"

    def __init__(
        self,
        condition: Condition,
        then_step: Step,
        else_step: Optional[Step] = None,
        name: str = "",
    ):
        super().__init__(name)
        self.condition = condition
        self.then_step = then_step
        self.else_step = else_step

    def execute(self, context: ExecutionContext) -> StepResult:
        branch = self.then_step if _eval_condition(self.condition, context) else self.else_step
        if branch is None:
            return StepResult.ok(None, skipped=True)
        return branch.execute(context)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "condition": self.condition if isinstance(self.condition, str) else "<callable>",
            "then": self.then_step.to_dict(),
            "else": self.else_step.to_dict() if self.else_step else None,
        }


class BranchStep(Step):
    """Multi-way switch: first matching case runs; otherwise the default."""

    type = "branch"

    def __init__(
        self,
        cases: List[tuple],  # (condition, step)
        default: Optional[Step] = None,
        name: str = "",
    ):
        super().__init__(name)
        self.cases = cases
        self.default = default

    def execute(self, context: ExecutionContext) -> StepResult:
        for condition, step in self.cases:
            if _eval_condition(condition, context):
                return step.execute(context)
        if self.default is not None:
            return self.default.execute(context)
        return StepResult.ok(None, skipped=True)


class ParallelStep(Step):
    """Execute child steps concurrently and collect their outputs."""

    type = "parallel"

    def __init__(self, steps: List[Step], name: str = "", max_workers: int = 8):
        super().__init__(name)
        self.steps = steps
        self.max_workers = max_workers

    def execute(self, context: ExecutionContext) -> StepResult:
        outputs: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        lock = threading.Lock()

        def _run(step: Step) -> None:
            child = context.child(step.name)
            child.variables = dict(context.variables)
            res = step.execute(child)
            with lock:
                outputs[step.name] = res.output
                if not res.success:
                    errors[step.name] = res.error or "failed"

        workers = min(self.max_workers, max(1, len(self.steps)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_run, self.steps))

        for key, value in outputs.items():
            context.set(key, value)
        if errors:
            return StepResult(output=outputs, success=False, error=str(errors), metadata={"errors": errors})
        return StepResult.ok(outputs)

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "steps": [s.to_dict() for s in self.steps], "max_workers": self.max_workers}


class LoopStep(Step):
    """Repeat a body step: over an iterable variable, or while a condition holds."""

    type = "loop"

    def __init__(
        self,
        body: Step,
        *,
        over: Optional[str] = None,
        item_var: str = "item",
        while_condition: Optional[Condition] = None,
        max_iterations: int = 100,
        name: str = "",
    ):
        super().__init__(name)
        self.body = body
        self.over = over
        self.item_var = item_var
        self.while_condition = while_condition
        self.max_iterations = max_iterations

    def execute(self, context: ExecutionContext) -> StepResult:
        results: List[Any] = []
        if self.over is not None:
            items = context.get(self.over) or []
            for i, item in enumerate(items):
                if i >= self.max_iterations:
                    break
                context.set(self.item_var, item)
                res = self.body.execute(context)
                results.append(res.output)
                if not res.success:
                    return StepResult(output=results, success=False, error=res.error)
        else:
            count = 0
            while self.while_condition is not None and _eval_condition(self.while_condition, context):
                if count >= self.max_iterations:
                    break
                res = self.body.execute(context)
                results.append(res.output)
                count += 1
                if not res.success:
                    return StepResult(output=results, success=False, error=res.error)
        context.set("__last__", results)
        return StepResult.ok(results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "body": self.body.to_dict(),
            "over": self.over,
            "item_var": self.item_var,
            "while": self.while_condition if isinstance(self.while_condition, str) else None,
            "max_iterations": self.max_iterations,
        }


class RetryStep(Step):
    """Wrap a step, retrying on failure up to ``max_retries`` times."""

    type = "retry"

    def __init__(self, step: Step, max_retries: int = 2, name: str = ""):
        super().__init__(name)
        self.step = step
        self.max_retries = max_retries

    def execute(self, context: ExecutionContext) -> StepResult:
        last = StepResult.fail("not run")
        for attempt in range(self.max_retries + 1):
            last = self.step.execute(context)
            if last.success:
                last.metadata["attempts"] = attempt + 1
                return last
        last.metadata["attempts"] = self.max_retries + 1
        return last

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "step": self.step.to_dict(), "max_retries": self.max_retries}


class TimeoutStep(Step):
    """Wrap a step, failing if it exceeds ``timeout`` seconds."""

    type = "timeout"

    def __init__(self, step: Step, timeout: float = 30.0, name: str = ""):
        super().__init__(name)
        self.step = step
        self.timeout = timeout

    def execute(self, context: ExecutionContext) -> StepResult:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.step.execute, context)
            try:
                return future.result(timeout=self.timeout)
            except concurrent.futures.TimeoutError:
                return StepResult.fail(f"Step '{self.step.name}' timed out after {self.timeout}s")

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "step": self.step.to_dict(), "timeout": self.timeout}


class FallbackStep(Step):
    """Try each candidate step in order until one succeeds."""

    type = "fallback"

    def __init__(self, steps: List[Step], name: str = ""):
        super().__init__(name)
        self.steps = steps

    def execute(self, context: ExecutionContext) -> StepResult:
        last = StepResult.fail("no fallback steps")
        for step in self.steps:
            last = step.execute(context)
            if last.success:
                return last
        return last

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "steps": [s.to_dict() for s in self.steps]}


class NestedWorkflowStep(Step):
    """Run another workflow as a single step (composition/nesting)."""

    type = "nested"

    def __init__(self, workflow: Workflow, name: str = ""):
        super().__init__(name or workflow.name)
        self.workflow = workflow

    def execute(self, context: ExecutionContext) -> StepResult:
        engine = context.metadata.get("engine")
        if engine is None:
            return StepResult.fail("no engine available for nested workflow")
        child = context.child(self.workflow.name)
        child.metadata = dict(context.metadata)
        result = engine.execute(self.workflow, context=child)
        return StepResult(output=result.output, success=result.success, error=result.error)

    def to_dict(self) -> Dict[str, Any]:
        return {**super().to_dict(), "workflow": self.workflow.to_dict()}
