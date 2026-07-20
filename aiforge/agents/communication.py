"""Agent communication — mailboxes and a coordinator for multi-agent teams.

Agents exchange :class:`AgentMessage` objects through per-recipient mailboxes on
a shared :class:`MessageBus`. The :class:`Coordinator` orchestrates a team,
optionally routing a task to the best-suited agent.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from ..core.types import RunResult, new_id
from ..events.bus import EventBus, EventType
from .agent import Agent
from .registry import AgentRegistry


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    content: str
    id: str = field(default_factory=lambda: new_id("msg"))
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageBus:
    """Per-recipient mailboxes for inter-agent messaging."""

    def __init__(self, events: Optional[EventBus] = None):
        self._mailboxes: Dict[str, Deque[AgentMessage]] = defaultdict(deque)
        self._events = events
        self._lock = threading.RLock()

    def send(self, message: AgentMessage) -> None:
        with self._lock:
            self._mailboxes[message.recipient].append(message)
        if self._events is not None:
            self._events.emit(
                EventType.AGENT_MESSAGE,
                {"from": message.sender, "to": message.recipient, "content": message.content[:200]},
                source="communication",
            )

    def receive(self, recipient: str) -> Optional[AgentMessage]:
        with self._lock:
            box = self._mailboxes.get(recipient)
            return box.popleft() if box else None

    def inbox(self, recipient: str) -> List[AgentMessage]:
        with self._lock:
            return list(self._mailboxes.get(recipient, ()))

    def broadcast(self, sender: str, content: str, recipients: List[str]) -> None:
        for recipient in recipients:
            self.send(AgentMessage(sender=sender, recipient=recipient, content=content))


class Coordinator:
    """Route tasks across a team of agents and support hand-offs."""

    def __init__(self, registry: AgentRegistry, bus: Optional[MessageBus] = None):
        self.registry = registry
        self.bus = bus or MessageBus()

    def route(self, task: str, router_agent: Optional[str] = None) -> str:
        """Pick an agent for *task*. If a router agent is provided, ask it;
        otherwise choose by keyword overlap with each agent's description."""
        agents = self.registry.list()
        if not agents:
            raise ValueError("No agents registered to route to")
        if router_agent and self.registry.has(router_agent):
            names = ", ".join(a.config.name for a in agents)
            prompt = (
                f"Choose exactly one agent name from [{names}] best suited for this task. "
                f"Reply with only the name.\nTask: {task}"
            )
            reply = self.registry.get(router_agent).run(prompt).output or ""
            for agent in agents:
                if agent.config.name.lower() in reply.lower():
                    return agent.config.name
        terms = {t for t in task.lower().split() if len(t) > 3}
        best, best_score = agents[0].config.name, -1
        for agent in agents:
            text = f"{agent.config.description} {agent.config.role}".lower()
            score = sum(1 for t in terms if t in text)
            if score > best_score:
                best, best_score = agent.config.name, score
        return best

    def dispatch(self, task: str, agent_name: Optional[str] = None, **kwargs: Any) -> RunResult:
        name = agent_name or self.route(task)
        return self.registry.get(name).run(task, **kwargs)

    def pipeline(self, task: str, agent_names: List[str]) -> RunResult:
        """Feed a task through several agents in sequence, chaining outputs."""
        current = task
        result = RunResult(output=task)
        for name in agent_names:
            result = self.registry.get(name).run(current)
            current = str(result.output)
        return result
