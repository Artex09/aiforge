"""Crew — the easy, high-level way to run a team of agents.

A Crew groups agents and tasks and runs them under a **process**. The default
process is ``sequential``: tasks run in order, and each task receives the
accumulated output of the tasks before it as context. This mirrors the mental
model of "serial agents" — a straight pipeline of specialists.

Example::

    crew = Crew(
        engine,
        tasks=[
            Task("Research AI agents", agent="researcher"),
            Task("Write a report from the research", agent="writer"),
        ],
    )
    result = crew.kickoff()
    print(result.output)          # final task output
    print(result.task_outputs)    # every task's output
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.errors import AgentError
from ..core.types import RunResult, Usage, new_id
from ..events.bus import EventType


class Process(str, Enum):
    SEQUENTIAL = "sequential"
    #: Reserved for a future hierarchical/manager process (roadmap).
    HIERARCHICAL = "hierarchical"


@dataclass
class Task:
    """A single unit of work assigned to an agent."""

    description: str
    agent: str
    expected_output: str = ""
    name: str = ""
    tools: List[str] = field(default_factory=list)
    output: Any = None
    id: str = field(default_factory=lambda: new_id("task"))

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.description[:40].strip() or self.id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent": self.agent,
            "expected_output": self.expected_output,
            "tools": self.tools,
            "output": self.output,
        }


@dataclass
class CrewResult:
    output: Any = None
    success: bool = True
    error: Optional[str] = None
    task_outputs: List[Dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    duration: float = 0.0
    cost_usd: float = 0.0
    model: str = ""
    crew: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output": self.output,
            "success": self.success,
            "error": self.error,
            "task_outputs": self.task_outputs,
            "usage": self.usage.to_dict(),
            "duration": self.duration,
            "cost_usd": self.cost_usd,
            "model": self.model,
            "crew": self.crew,
        }


class Crew:
    """A team of agents that completes an ordered list of tasks."""

    def __init__(
        self,
        engine: Any,
        tasks: List[Task],
        *,
        name: str = "crew",
        process: str = Process.SEQUENTIAL.value,
        verbose: bool = False,
    ):
        self.engine = engine
        self.tasks = tasks
        self.name = name
        self.process = process
        self.verbose = verbose
        self.id = new_id("crew")

    # ------------------------------------------------------------------ run
    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> CrewResult:
        """Run the crew and return a :class:`CrewResult`."""
        started = time.time()
        result = CrewResult(crew=self.name)
        if not self.tasks:
            result.success = False
            result.error = "Crew has no tasks to run"
            result.duration = time.time() - started
            return result
        self._emit(EventType.WORKFLOW_START, {"crew": self.name, "process": self.process})

        context_parts: List[str] = []
        if inputs:
            for key, value in inputs.items():
                context_parts.append(f"{key}: {value}")

        try:
            for index, task in enumerate(self.tasks, start=1):
                if not self.engine.agents.has(task.agent):
                    raise AgentError(f"Task '{task.name}' references unknown agent '{task.agent}'")
                agent = self.engine.agents.get(task.agent)
                prompt = self._build_prompt(task, context_parts)

                self._emit(
                    EventType.WORKFLOW_STEP_START,
                    {"crew": self.name, "task": task.name, "agent": task.agent, "step": index},
                )
                run: RunResult = agent.run(prompt)
                task.output = run.output
                result.usage = result.usage + run.usage
                result.task_outputs.append(
                    {"task": task.name, "agent": task.agent, "output": run.output, "success": run.success}
                )
                context_parts.append(f"Result of '{task.name}':\n{run.output}")
                self._emit(
                    EventType.WORKFLOW_STEP_END,
                    {"crew": self.name, "task": task.name, "success": run.success},
                )
                if not run.success:
                    raise AgentError(f"Task '{task.name}' failed: {run.error}")

            result.output = self.tasks[-1].output if self.tasks else None
            result.success = True
            result.model = self._model_hint()
            from ..core.pricing import cost_from_usage

            result.cost_usd = cost_from_usage(result.model, result.usage)
            self._emit(
                EventType.WORKFLOW_END,
                {"crew": self.name, "tasks": len(self.tasks), "cost_usd": result.cost_usd},
            )
        except Exception as exc:  # noqa: BLE001
            result.success = False
            result.error = str(exc)
            self._emit(EventType.WORKFLOW_ERROR, {"crew": self.name, "error": str(exc)})
        finally:
            result.duration = time.time() - started
            self._record(result)
        return result

    # ------------------------------------------------------------- internals
    def _build_prompt(self, task: Task, context_parts: List[str]) -> str:
        lines = [task.description]
        if task.expected_output:
            lines.append(f"\nExpected output: {task.expected_output}")
        if context_parts:
            lines.append("\nContext from previous steps:\n" + "\n\n".join(context_parts[-6:]))
        return "\n".join(lines)

    def _model_hint(self) -> str:
        """Best-effort model name for cost accounting (first agent's provider)."""
        for task in self.tasks:
            if self.engine.agents.has(task.agent):
                agent = self.engine.agents.get(task.agent)
                model = agent.config.model or getattr(agent.provider.config, "model", "")
                if model:
                    return model
        return self.engine.config.get("provider.model", "aiforge-mock-1")

    def _record(self, result: CrewResult) -> None:
        try:
            self.engine.backend.append(
                "crew_runs",
                {"crew": self.name, "success": result.success, "duration": result.duration,
                 "tasks": len(self.tasks), "timestamp": time.time()},
            )
        except Exception:  # noqa: BLE001 - history is best-effort
            pass

    def _emit(self, etype: EventType, data: Dict[str, Any]) -> None:
        if self.engine.events is not None:
            self.engine.events.emit(etype, data, source=f"crew:{self.name}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "process": self.process,
            "tasks": [t.to_dict() for t in self.tasks],
        }
