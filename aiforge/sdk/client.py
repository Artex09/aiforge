"""AIForge SDK — the friendly, high-level entry point.

This is the object most applications use::

    from aiforge.sdk import AIForge

    forge = AIForge()
    agent = forge.agent("assistant", system_prompt="You are helpful.")
    print(forge.run(agent, "Hello!").output)
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..agents.agent import Agent, AgentConfig
from ..config.settings import Config
from ..core.engine import Engine
from ..core.types import RunResult
from ..memory.base import MemoryKind
from ..providers.base import LLMProvider
from ..tools.base import FunctionTool, Tool
from ..workflows.base import Workflow
from ..workflows.builder import WorkflowBuilder


class AIForge:
    """A thin, ergonomic wrapper over :class:`Engine`."""

    def __init__(
        self,
        config: Optional[Config] = None,
        config_path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ):
        if config is None:
            config = Config.load(path=config_path, overrides=overrides)
        self.engine = Engine(config)

    # --------------------------------------------------------------- config
    @property
    def config(self) -> Config:
        return self.engine.config

    def set_secret(self, key: str, value: str) -> "AIForge":
        self.engine.secrets.set(key, value)
        return self

    # --------------------------------------------------------------- agents
    def agent(
        self,
        name: str,
        *,
        role: str = "assistant",
        system_prompt: str = "",
        tools: Optional[List[str]] = None,
        provider: Optional[str] = None,
        template: Optional[str] = None,
        **kwargs: Any,
    ) -> Agent:
        if template is not None:
            return self.engine.agent_from_template(template, name=name, **kwargs)
        config = AgentConfig(
            name=name,
            role=role,
            system_prompt=system_prompt,
            tools=tools or [],
            allow_all_tools=tools is None and kwargs.pop("allow_all_tools", False),
            provider=provider,
            **kwargs,
        )
        return self.engine.create_agent(config)

    def run(self, agent: Any, user_input: str, **kwargs: Any) -> RunResult:
        name = agent.config.name if isinstance(agent, Agent) else agent
        return self.engine.run_agent(name, user_input, **kwargs)

    # ---------------------------------------------------------------- tools
    def tool(self, func_or_tool: Any = None, **kwargs: Any):
        """Register a tool. Usable as ``forge.tool(my_tool)`` or as a decorator
        ``@forge.tool(description=...)``."""
        if isinstance(func_or_tool, Tool):
            return self.engine.tools.register(func_or_tool)
        if callable(func_or_tool):
            return self.engine.tools.register(FunctionTool(func_or_tool, **kwargs))

        def _decorator(func: Callable[..., Any]) -> Tool:
            return self.engine.tools.register(FunctionTool(func, **kwargs))

        return _decorator

    def call_tool(self, name: str, **arguments: Any):
        return self.engine.call_tool(name, arguments)

    # --------------------------------------------------------------- memory
    def remember(self, content: str, semantic: bool = False, **metadata: Any) -> str:
        if semantic:
            return self.engine.memory.remember_semantic(content, metadata)
        return self.engine.memory.remember(content, MemoryKind.SHORT_TERM, metadata)

    def recall(self, query: str, top_k: int = 5) -> List[str]:
        return [r.content for r in self.engine.memory.recall(query, top_k)]

    # ---------------------------------------------------------------- crews
    def task(self, description: str, agent: str, *, expected_output: str = "", **kwargs: Any):
        """Create a :class:`Task` for a crew."""
        from ..agents.crew import Task

        return Task(description=description, agent=agent, expected_output=expected_output, **kwargs)

    def crew(self, tasks, *, name: str = "crew", process: str = "sequential"):
        """Create a sequential (serial) crew of agents.

        Example::

            forge.agent("researcher", role="researcher")
            forge.agent("writer")
            crew = forge.crew([
                forge.task("Research the topic", agent="researcher"),
                forge.task("Write a report", agent="writer"),
            ])
            print(crew.kickoff().output)
        """
        return self.engine.create_crew(tasks, name=name, process=process)

    # ------------------------------------------------------------ workflows
    def workflow(self, name: str, description: str = "") -> WorkflowBuilder:
        return WorkflowBuilder(name, description)

    def run_workflow(self, workflow: Workflow, inputs: Optional[Dict[str, Any]] = None) -> RunResult:
        return self.engine.run_workflow(workflow, inputs)

    # ------------------------------------------------------------- providers
    def register_provider(self, provider: LLMProvider, *, default: bool = False) -> LLMProvider:
        return self.engine.register_provider(provider, default=default)

    # ---------------------------------------------------------------- server
    def serve(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        from ..api.server import serve

        serve(self.engine, host=host, port=port)

    # ------------------------------------------------------------------ misc
    def status(self) -> Dict[str, Any]:
        return self.engine.status()

    def load_plugins(self, path: str) -> List[str]:
        return self.engine.plugins.load_from_directory(path)
