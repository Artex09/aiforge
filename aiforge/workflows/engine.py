"""Workflow execution engine.

Executes a :class:`Workflow` step-by-step against an :class:`ExecutionContext`,
emitting lifecycle events, persisting execution history, and honouring engine-
level defaults for retries and timeouts.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..core.context import ExecutionContext
from ..core.errors import WorkflowError
from ..core.types import RunResult
from ..events.bus import EventBus, EventType
from .base import Step, Workflow


class WorkflowEngine:
    def __init__(
        self,
        *,
        events: Optional[EventBus] = None,
        agents: Any = None,
        tools: Any = None,
        state: Any = None,
        memory: Any = None,
        config: Any = None,
        backend: Any = None,
        sandbox_root: Optional[str] = None,
        secrets: Any = None,
    ):
        self.events = events
        self.agents = agents
        self.tools = tools
        self.state = state
        self.memory = memory
        self.config = config
        self.backend = backend
        self.sandbox_root = sandbox_root
        self.secrets = secrets

    def execute(
        self,
        workflow: Workflow,
        inputs: Optional[Dict[str, Any]] = None,
        *,
        context: Optional[ExecutionContext] = None,
    ) -> RunResult:
        workflow.ensure_valid()
        ctx = context or self._new_context(workflow.name)
        if inputs:
            ctx.update(inputs)
            ctx.set("input", inputs.get("input", inputs))

        result = RunResult(context_id=ctx.id, metadata={"workflow": workflow.name})
        self._emit(EventType.WORKFLOW_START, {"workflow": workflow.name, "inputs": list((inputs or {}).keys())})

        try:
            last_output: Any = ctx.get("input")
            for step in workflow.steps:
                last_output = self._run_step(step, ctx)
            result.output = last_output
            result.success = True
            result.steps = len(workflow.steps)
            result.usage = ctx.usage
            self._emit(EventType.WORKFLOW_END, {"workflow": workflow.name, "steps": result.steps})
        except Exception as exc:  # noqa: BLE001
            result.success = False
            result.error = str(exc)
            self._emit(EventType.WORKFLOW_ERROR, {"workflow": workflow.name, "error": str(exc)})
            raise WorkflowError(f"Workflow '{workflow.name}' failed: {exc}") from exc
        finally:
            result.finished_at = time.time()
            self._record_history(workflow, ctx, result)
        return result

    def _run_step(self, step: Step, ctx: ExecutionContext) -> Any:
        self._emit(EventType.WORKFLOW_STEP_START, {"step": step.name, "type": step.type})
        started = time.time()
        step_result = step.execute(ctx)
        ctx.set("__last__", step_result.output)
        ctx.set(step.name, step_result.output)
        self._emit(
            EventType.WORKFLOW_STEP_END,
            {
                "step": step.name,
                "type": step.type,
                "success": step_result.success,
                "duration": time.time() - started,
            },
        )
        if not step_result.success:
            raise WorkflowError(
                f"Step '{step.name}' failed: {step_result.error}",
                details={"step": step.name, "error": step_result.error},
            )
        return step_result.output

    def _new_context(self, name: str) -> ExecutionContext:
        from ..core.security import Permissions
        from ..tools.context import ToolContext

        ctx = ExecutionContext(name=name)
        ctx.events = self.events
        ctx.state = self.state
        ctx.memory = self.memory
        ctx.config = self.config
        ctx.secrets = self.secrets
        tool_context = ToolContext(
            agent_name=name,
            execution_id=ctx.id,
            state=self.state,
            memory=self.memory,
            events=self.events,
            config=self.config,
            secrets=self.secrets,
            sandbox_root=self.sandbox_root,
            permissions=Permissions(allow_all=True),
        )
        ctx.metadata.update(
            {
                "agents": self.agents,
                "tools": self.tools,
                "engine": self,
                "tool_context": tool_context,
            }
        )
        return ctx

    def _record_history(self, workflow: Workflow, ctx: ExecutionContext, result: RunResult) -> None:
        if self.backend is None:
            return
        try:
            self.backend.append(
                "executions",
                {
                    "workflow": workflow.name,
                    "context_id": ctx.id,
                    "success": result.success,
                    "error": result.error,
                    "duration": result.duration,
                    "usage": result.usage.to_dict(),
                    "variables": {k: _safe(v) for k, v in ctx.variables.items()},
                    "timestamp": time.time(),
                },
            )
        except Exception:  # noqa: BLE001 - history is best-effort
            pass

    def _emit(self, etype: EventType, data: Dict[str, Any]) -> None:
        if self.events is not None:
            self.events.emit(etype, data, source="workflow")


def _safe(value: Any, limit: int = 500) -> Any:
    text = value if isinstance(value, (str, int, float, bool)) or value is None else repr(value)
    if isinstance(text, str) and len(text) > limit:
        return text[:limit] + "…"
    return text
