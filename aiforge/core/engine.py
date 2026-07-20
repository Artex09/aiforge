"""The AIForge core engine.

The engine is the composition root: it constructs and wires every subsystem —
config, events, storage, providers, tools, memory, state, security, monitoring,
agents, workflows, and plugins — and exposes a cohesive API the SDK, CLI, and
API layer build on.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..agents.agent import Agent, AgentConfig
from ..agents.communication import Coordinator, MessageBus
from ..agents.registry import AgentRegistry
from ..agents.templates import get_template
from ..config.settings import Config
from ..core.context import ExecutionContext
from ..core.errors import ProviderNotFoundError
from ..core.monitoring import Monitor
from ..core.security import (
    ExecutionLimits,
    Sandbox,
    SecretsManager,
    TokenAuthenticator,
)
from ..core.state import StateManager
from ..core.types import RunResult
from ..events.bus import EventBus
from ..memory.embeddings import Embedder
from ..memory.manager import MemoryManager
from ..providers.base import LLMProvider, ProviderConfig
from ..providers.mock import MockProvider
from ..providers.registry import ProviderRegistry
from ..storage.base import StorageBackend
from ..storage.cache import TTLCache
from ..storage.local import LocalStorage
from ..tools.builtin import register_builtins
from ..tools.registry import ToolRegistry
from ..workflows.base import Workflow
from ..workflows.engine import WorkflowEngine


class Engine:
    def __init__(
        self,
        config: Optional[Config] = None,
        *,
        backend: Optional[StorageBackend] = None,
        register_builtin_tools: bool = True,
    ):
        self.config = config or Config()

        # Event backbone
        self.events = EventBus(history_size=self.config.get("logging.history_size", 2000))

        # Storage + cache
        self.backend: StorageBackend = backend or self._make_backend()
        self.cache = TTLCache(default_ttl=self.config.get("storage.cache_ttl", 300))

        # Security
        self.secrets = SecretsManager()
        self.sandbox = Sandbox(self.config.get("security.sandbox_root", ".aiforge/sandbox"))
        self.limits = ExecutionLimits(
            max_steps=self.config.get("security.max_steps", 12),
            max_tokens=self.config.get("security.max_tokens", 100000),
            max_tool_calls=self.config.get("security.max_tool_calls", 50),
        )
        self.auth = TokenAuthenticator(self.config.get("api.auth_token"))

        # Providers
        self.providers = ProviderRegistry()
        self._bootstrap_providers()

        # Tools
        self.tools = ToolRegistry(self.events)
        if register_builtin_tools:
            register_builtins(self.tools, include_shell=self.config.get("security.allow_shell", False))

        # State (restore any previously persisted scopes)
        self.state = StateManager(backend=self.backend)
        self.state.load()

        # Memory
        self.embedder = Embedder(
            self._safe_provider(self.config.get("embeddings.provider")),
            dimension=self.config.get("embeddings.dimension", 256),
        )
        self.memory = MemoryManager(
            embedder=self.embedder,
            backend=self.backend,
            events=self.events,
            provider=self._safe_provider(),
            short_term_capacity=self.config.get("memory.short_term_capacity", 20),
            compression_threshold=self.config.get("memory.compression.threshold", 40),
            compression_enabled=self.config.get("memory.compression.enabled", True),
        )

        # Agents + communication
        self.agents = AgentRegistry()
        self.messages = MessageBus(self.events)
        self.coordinator = Coordinator(self.agents, self.messages)

        # Workflows
        self.workflow_engine = WorkflowEngine(
            events=self.events,
            agents=self.agents,
            tools=self.tools,
            state=self.state,
            memory=self.memory,
            config=self.config,
            backend=self.backend,
            sandbox_root=self.sandbox.root,
            secrets=self.secrets,
        )

        # Monitoring
        self.monitor = Monitor(self.events, backend=self.backend)

        # Plugins (imported lazily to avoid a cycle)
        from ..plugins.base import PluginManager

        self.plugins = PluginManager(self)

    # ------------------------------------------------------------- bootstrap
    def _make_backend(self) -> StorageBackend:
        backend = self.config.get("storage.backend", "local")
        path = self.config.get("storage.path", ".aiforge")
        if backend == "sqlite":
            from ..storage.sqlite_store import SQLiteStorage

            return SQLiteStorage(path=f"{path}/aiforge.db")
        return LocalStorage(root=path)

    def _bootstrap_providers(self) -> None:
        # Always register the offline mock provider so the framework runs anywhere.
        default_name = self.config.get("provider.default", "mock")
        model = self.config.get("provider.model", "aiforge-mock-1")
        mock = MockProvider(
            ProviderConfig(name="mock", model=model, temperature=self.config.get("provider.temperature", 0.7))
        )
        self.providers.register(mock, default=(default_name == "mock"))
        self.providers.set_fallbacks(self.config.get("provider.fallbacks", []))

        # Register real providers if configured with credentials.
        self._maybe_register_openai()
        self._maybe_register_anthropic()
        if default_name != "mock" and default_name in self.providers.names():
            self.providers.set_default(default_name)

    def _maybe_register_openai(self) -> None:
        key = self.secrets.get("OPENAI_API_KEY")
        if not key:
            return
        from ..providers.openai_provider import OpenAIProvider

        self.providers.register(
            OpenAIProvider(
                ProviderConfig(
                    name="openai",
                    model=self.config.get("provider.openai_model", "gpt-4o-mini"),
                    api_key=key,
                    base_url=self.config.get("provider.openai_base_url"),
                )
            )
        )

    def _maybe_register_anthropic(self) -> None:
        key = self.secrets.get("ANTHROPIC_API_KEY")
        if not key:
            return
        from ..providers.anthropic_provider import AnthropicProvider

        self.providers.register(
            AnthropicProvider(
                ProviderConfig(
                    name="anthropic",
                    model=self.config.get("provider.anthropic_model", "claude-fable-5"),
                    api_key=key,
                )
            )
        )

    def _safe_provider(self, name: Optional[str] = None) -> Optional[LLMProvider]:
        try:
            return self.providers.get(name)
        except ProviderNotFoundError:
            return None

    def register_provider(self, provider: LLMProvider, *, default: bool = False) -> LLMProvider:
        return self.providers.register(provider, default=default)

    # --------------------------------------------------------------- agents
    def create_agent(
        self,
        config: AgentConfig,
        *,
        provider: Optional[str] = None,
        register: bool = True,
    ) -> Agent:
        prov = self.providers.get(provider or config.provider)
        agent = Agent(
            config,
            prov,
            tools=self.tools,
            memory=self.memory if config.use_memory else None,
            events=self.events,
            state=self.state,
            secrets=self.secrets,
            limits=ExecutionLimits(
                max_steps=config.max_steps,
                max_tokens=self.limits.max_tokens,
                max_tool_calls=self.limits.max_tool_calls,
            ),
            sandbox_root=self.sandbox.root,
            config_obj=self.config,
        )
        if register:
            self.agents.register(agent)
        return agent

    def agent_from_template(self, template: str, register: bool = True, **overrides: Any) -> Agent:
        config = get_template(template)
        for key, value in overrides.items():
            setattr(config, key, value)
        return self.create_agent(config, register=register)

    def run_agent(self, name: str, user_input: str, **kwargs: Any) -> RunResult:
        return self.agents.get(name).run(user_input, **kwargs)

    # ----------------------------------------------------------------- crews
    def create_crew(self, tasks, *, name: str = "crew", process: str = "sequential"):
        from ..agents.crew import Crew

        return Crew(self, tasks, name=name, process=process)

    def run_graph(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Build agents + tasks from a visual-editor graph and run them.

        ``graph`` = ``{process, nodes:[{id,type,data}], edges:[{source,target}]}``
        where node ``type`` is ``agent``, ``task``, or ``trigger``.
        """
        from ..agents.crew import Crew, Task

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        process = graph.get("process", "sequential")

        # 1) Materialise agents (ephemeral, replacing any same-named agent).
        agent_nodes = [n for n in nodes if n.get("type") == "agent"]
        for node in agent_nodes:
            data = node.get("data", {})
            aname = data.get("name") or node.get("id")
            if self.agents.has(aname):
                self.agents.unregister(aname)
            self.create_agent(
                AgentConfig(
                    name=aname,
                    role=data.get("role", "assistant"),
                    system_prompt=data.get("system_prompt", ""),
                    model=data.get("model"),
                    tools=data.get("tools", []),
                    allow_all_tools=not data.get("tools"),
                )
            )

        # 2) Order task nodes by following edges, else by array order.
        task_nodes = [n for n in nodes if n.get("type") == "task"]
        ordered = self._order_by_edges(task_nodes, edges)

        # 3) Assign each task to an agent (explicit, or the first agent).
        default_agent = (agent_nodes[0]["data"].get("name") if agent_nodes else None)
        tasks = []
        for node in ordered:
            data = node.get("data", {})
            agent_name = data.get("agent") or default_agent
            if not agent_name:
                continue
            tasks.append(
                Task(
                    description=data.get("description", data.get("label", "Do the task")),
                    agent=agent_name,
                    expected_output=data.get("expected_output", ""),
                    name=data.get("label") or data.get("name", ""),
                    tools=data.get("tools", []),
                )
            )

        crew = Crew(self, tasks, name=graph.get("name", "studio-crew"), process=process)
        result = crew.kickoff(graph.get("inputs"))
        return result.to_dict()

    @staticmethod
    def _order_by_edges(task_nodes, edges):
        by_id = {n["id"]: n for n in task_nodes}
        if not edges:
            return task_nodes
        # A task is a "start" only if no *other task* feeds it. Edges from a
        # trigger (or any non-task node) must not disqualify the first task,
        # otherwise a `trigger -> task-1` edge would drop task-1 from `starts`.
        incoming = {
            e["target"]: e["source"]
            for e in edges
            if e.get("target") in by_id and e.get("source") in by_id
        }
        starts = [n for n in task_nodes if n["id"] not in incoming]
        order, seen = [], set()
        frontier = starts or task_nodes[:1]
        adjacency: Dict[str, list] = {}
        for e in edges:
            adjacency.setdefault(e["source"], []).append(e["target"])
        stack = [n["id"] for n in frontier]
        while stack:
            nid = stack.pop(0)
            if nid in seen or nid not in by_id:
                continue
            seen.add(nid)
            order.append(by_id[nid])
            stack.extend(adjacency.get(nid, []))
        for n in task_nodes:  # append any leftovers deterministically
            if n["id"] not in seen:
                order.append(n)
        return order

    def graph_to_code(self, graph: Dict[str, Any]) -> str:
        """Render a visual-editor graph as a runnable Python script (SDK calls).

        This makes the Studio round-trippable: graph -> code -> run, or edit the
        code and re-import. The generated script uses only the public SDK.
        """
        import json as _json

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        agent_nodes = [n for n in nodes if n.get("type") == "agent"]
        task_nodes = self._order_by_edges([n for n in nodes if n.get("type") == "task"], edges)

        lines = [
            '"""Generated by AIForge Studio. Run: python this_file.py"""',
            "from aiforge.sdk import AIForge",
            "",
            "forge = AIForge()",
            "",
            "# --- Agents ---",
        ]
        default_agent = agent_nodes[0]["data"].get("name") if agent_nodes else None
        for node in agent_nodes:
            d = node.get("data", {})
            name = d.get("name", "agent")
            args = [_json.dumps(name), f"role={_json.dumps(d.get('role', 'assistant'))}"]
            if d.get("tools"):
                args.append(f"tools={_json.dumps(d['tools'])}")
            if d.get("system_prompt"):
                args.append(f"system_prompt={_json.dumps(d['system_prompt'])}")
            if d.get("model"):
                args.append(f"model={_json.dumps(d['model'])}")
            lines.append(f"forge.agent({', '.join(args)})")

        lines += ["", "# --- Crew (sequential) ---", "crew = forge.crew(["]
        for node in task_nodes:
            d = node.get("data", {})
            agent_name = d.get("agent") or default_agent or "assistant"
            desc = d.get("description") or d.get("label", "Do the task")
            task_args = [_json.dumps(desc), f"agent={_json.dumps(agent_name)}"]
            if d.get("expected_output"):
                task_args.append(f"expected_output={_json.dumps(d['expected_output'])}")
            lines.append(f"    forge.task({', '.join(task_args)}),")
        lines += [
            "])",
            "",
            "result = crew.kickoff()",
            "print(result.output)",
            "for step in result.task_outputs:",
            '    print(f"\\n[{step[\'agent\']}] {step[\'task\']}\\n{step[\'output\']}")',
            "",
        ]
        return "\n".join(lines)

    def tool_catalog(self) -> Dict[str, Any]:
        """Tool schemas grouped into categories for the Tools panel."""
        categories = {
            "AI & Machine Learning": {"summarize_text", "web_search"},
            "Automation & Integration": {"http_request", "current_datetime"},
            "Database & Data": {"json_parse", "json_query", "calculator"},
            "File & Document": {"read_file", "write_file", "list_dir"},
            "System": {"shell"},
        }
        grouped: Dict[str, list] = {c: [] for c in categories}
        grouped["Integrations"] = []
        for tool in self.tools.list():
            placed = False
            for cat, names in categories.items():
                if tool.name in names:
                    grouped[cat].append(tool.schema.to_openai())
                    placed = True
                    break
            if not placed:
                grouped["Integrations"].append(tool.schema.to_openai())
        return {"categories": grouped}

    # ------------------------------------------------------------ workflows
    def run_workflow(
        self, workflow: Workflow, inputs: Optional[Dict[str, Any]] = None
    ) -> RunResult:
        return self.workflow_engine.execute(workflow, inputs)

    # ------------------------------------------------------------- utilities
    def tool_context(self):
        """A ToolContext with full grants for direct (SDK/API) tool calls,
        scoped to the engine's sandbox root."""
        from ..core.security import Permissions
        from ..tools.context import ToolContext

        return ToolContext(
            agent_name="engine",
            state=self.state,
            memory=self.memory,
            events=self.events,
            config=self.config,
            secrets=self.secrets,
            sandbox_root=self.sandbox.root,
            permissions=Permissions(allow_all=True),
        )

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None):
        return self.tools.execute(name, arguments or {}, context=self.tool_context())

    def context(self, name: str = "") -> ExecutionContext:
        ctx = ExecutionContext(name=name)
        ctx.events = self.events
        ctx.state = self.state
        ctx.memory = self.memory
        ctx.config = self.config
        ctx.secrets = self.secrets
        ctx.limits = self.limits
        ctx.metadata.update({"agents": self.agents, "tools": self.tools, "engine": self.workflow_engine})
        return ctx

    def status(self) -> Dict[str, Any]:
        return {
            "providers": self.providers.names(),
            "tools": self.tools.names(),
            "agents": self.agents.names(),
            "memory": self.memory.stats(),
            "plugins": [p.name for p in self.plugins.list()],
            "metrics": self.monitor.snapshot()["metrics"],
        }

    def shutdown(self) -> None:
        try:
            self.backend.close()
        except Exception:  # noqa: BLE001
            pass
