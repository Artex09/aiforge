"""Agent definition, configuration, lifecycle, and the tool-calling run loop.

An :class:`Agent` is a configured reasoning unit: a provider, a system prompt, a
scoped set of tools, a memory manager, and permission/limits. ``run`` executes
the classic agentic loop — think, optionally call tools, observe, repeat — until
a final answer or a limit is hit.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.context import ExecutionContext
from ..core.errors import AgentError, ExecutionLimitError
from ..core.security import ExecutionLimits, Permissions
from ..core.types import Message, Role, RunResult, ToolCall, new_id
from ..events.bus import EventBus, EventType
from ..memory.base import MemoryKind
from ..memory.manager import MemoryManager
from ..providers.base import LLMProvider
from ..tools.context import ToolContext
from ..tools.registry import ToolRegistry


class AgentStatus(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Serializable agent definition."""

    name: str
    role: str = "assistant"
    description: str = ""
    system_prompt: str = ""
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    tools: List[str] = field(default_factory=list)  # allowed tool names ([] = all granted)
    allow_all_tools: bool = False
    permissions: Optional[List[str]] = None  # None = allow all
    max_steps: int = 8
    use_memory: bool = True
    memory_top_k: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "provider": self.provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": self.tools,
            "allow_all_tools": self.allow_all_tools,
            "permissions": self.permissions,
            "max_steps": self.max_steps,
            "use_memory": self.use_memory,
            "memory_top_k": self.memory_top_k,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


class Agent:
    """A runnable agent bound to a provider, tools, and memory."""

    def __init__(
        self,
        config: AgentConfig,
        provider: LLMProvider,
        *,
        tools: Optional[ToolRegistry] = None,
        memory: Optional[MemoryManager] = None,
        events: Optional[EventBus] = None,
        state: Any = None,
        secrets: Any = None,
        limits: Optional[ExecutionLimits] = None,
        sandbox_root: Optional[str] = None,
        config_obj: Any = None,
    ):
        from ..agents.roles import ROLES

        self.id = new_id("agent")
        self.config = config
        self.provider = provider
        self.tools = tools or ToolRegistry(events)
        self.memory = memory
        self.events = events
        self.state = state
        self.secrets = secrets
        self.limits = limits or ExecutionLimits(max_steps=config.max_steps)
        self.sandbox_root = sandbox_root
        self._config_obj = config_obj
        self.status = AgentStatus.CREATED
        self.permissions = Permissions.from_list(config.permissions)

        role_def = ROLES.get(config.role)
        for perm in role_def.default_permissions:
            self.permissions.grant(perm)
        self._role_prompt = role_def.prompt

        from ..core.retry import RetryPolicy

        cfg = config_obj
        self._retry = RetryPolicy(
            attempts=(cfg.get("provider.retries", 2) + 1) if cfg else 3,
            base_delay=cfg.get("provider.retry_base_delay", 0.5) if cfg else 0.5,
        )
        self.status = AgentStatus.READY
        self._emit(EventType.AGENT_CREATED, {"name": config.name, "role": config.role})

    # ------------------------------------------------------------------ prompt
    def _build_system_prompt(self) -> str:
        parts = [self._role_prompt]
        if self.config.system_prompt:
            parts.append(self.config.system_prompt)
        parts.append(f"Your name is {self.config.name}.")
        return "\n\n".join(p for p in parts if p)

    def _allowed_tools(self) -> Optional[List[str]]:
        if self.config.allow_all_tools:
            return None
        if self.config.tools:
            return list(self.config.tools)
        return []  # no tools granted

    def _tool_schemas(self) -> List[Dict[str, Any]]:
        allowed = self._allowed_tools()
        if allowed is None:
            return self.tools.schemas()
        if not allowed:
            return []
        return self.tools.schemas([n for n in allowed if self.tools.has(n)])

    # --------------------------------------------------------------------- run
    def run(
        self,
        user_input: str,
        *,
        context: Optional[ExecutionContext] = None,
        history: Optional[List[Message]] = None,
    ) -> RunResult:
        ctx = context or ExecutionContext(name=self.config.name)
        ctx.events = ctx.events or self.events
        ctx.state = ctx.state or self.state
        ctx.memory = ctx.memory or self.memory
        result = RunResult(context_id=ctx.id)
        self.status = AgentStatus.RUNNING
        self._emit(EventType.AGENT_START, {"agent": self.config.name, "input": user_input[:200]})

        try:
            messages = self._assemble_messages(user_input, history)
            tool_schemas = self._tool_schemas()
            tool_context = self._tool_context(ctx)

            final_text = ""
            for step in range(1, self.config.max_steps + 1):
                ctx.tick_step()
                try:
                    self.limits.check_steps(ctx.step_count)
                except ExecutionLimitError as exc:
                    final_text = f"[stopped: {exc.message}]"
                    break

                response = self._retry.run(
                    lambda: self.provider.chat(
                        messages,
                        tools=tool_schemas or None,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                    ),
                    on_retry=lambda n, exc, delay: self._emit(
                        EventType.LLM_REQUEST,
                        {"agent": self.config.name, "retry": n, "error": str(exc), "backoff": round(delay, 2)},
                    ),
                )
                ctx.add_usage(response.usage)
                result.usage = ctx.usage
                self._emit(
                    EventType.LLM_RESPONSE,
                    {
                        "agent": self.config.name,
                        "model": response.model,
                        "usage": response.usage.to_dict(),
                        "step": step,
                    },
                )
                self._emit(EventType.AGENT_STEP, {"agent": self.config.name, "step": step})

                if not response.has_tool_calls:
                    final_text = response.content
                    messages.append(Message.assistant(final_text))
                    break

                messages.append(Message.assistant(response.content, response.tool_calls))
                for call in response.tool_calls:
                    tool_msg = self._run_tool(call, tool_context, ctx)
                    messages.append(tool_msg)
            else:
                final_text = final_text or "[stopped: max steps reached]"

            self._persist_memory(user_input, final_text)
            result.output = final_text
            result.messages = messages
            result.steps = ctx.step_count
            result.success = True
            self.status = AgentStatus.DONE
            self._emit(EventType.AGENT_END, {"agent": self.config.name, "steps": ctx.step_count})
        except Exception as exc:  # noqa: BLE001
            self.status = AgentStatus.ERROR
            result.success = False
            result.error = str(exc)
            self._emit(EventType.AGENT_ERROR, {"agent": self.config.name, "error": str(exc)})
            raise AgentError(f"Agent '{self.config.name}' failed: {exc}") from exc
        finally:
            result.finished_at = time.time()
        return result

    # --------------------------------------------------------------- internals
    def _assemble_messages(
        self, user_input: str, history: Optional[List[Message]]
    ) -> List[Message]:
        messages: List[Message] = [Message.system(self._build_system_prompt())]
        if self.config.use_memory and self.memory is not None:
            messages.extend(self.memory.context_messages(user_input, self.config.memory_top_k))
        if history:
            messages.extend(history)
        messages.append(Message.user(user_input))
        return messages

    def _tool_context(self, ctx: ExecutionContext) -> ToolContext:
        return ToolContext(
            agent_name=self.config.name,
            execution_id=ctx.id,
            state=self.state,
            memory=self.memory,
            events=self.events,
            config=self._config_obj,
            secrets=self.secrets,
            sandbox_root=self.sandbox_root,
            permissions=self.permissions,
        )

    def _run_tool(
        self, call: ToolCall, tool_context: ToolContext, ctx: ExecutionContext
    ) -> Message:
        ctx.tick_tool_call()
        try:
            self.limits.check_tool_calls(ctx.tool_calls)
        except ExecutionLimitError as exc:
            return Message.tool(f"Error: {exc.message}", call.id, call.name)

        allowed = self._allowed_tools()
        result = self.tools.execute(
            call.name, call.arguments, context=tool_context, allowed=allowed
        )
        content = str(result.output) if result.ok else f"Error: {result.error}"
        return Message.tool(content, call.id, call.name)

    def _persist_memory(self, user_input: str, final_text: str) -> None:
        if not self.config.use_memory or self.memory is None:
            return
        self.memory.remember(f"User asked {self.config.name}: {user_input}", MemoryKind.SHORT_TERM)
        if final_text:
            self.memory.remember(f"{self.config.name} answered: {final_text}", MemoryKind.SHORT_TERM)

    def _emit(self, etype: EventType, data: Dict[str, Any]) -> None:
        if self.events is not None:
            self.events.emit(etype, data, source=f"agent:{self.config.name}")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Agent {self.config.name} role={self.config.role} status={self.status.value}>"
