"""Agent registry — track live agents and their configurations."""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..core.errors import AgentError
from .agent import Agent, AgentConfig


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._lock = threading.RLock()

    def register(self, agent: Agent) -> Agent:
        with self._lock:
            if agent.config.name in self._agents:
                raise AgentError(f"Agent '{agent.config.name}' already registered")
            self._agents[agent.config.name] = agent
        return agent

    def unregister(self, name: str) -> None:
        with self._lock:
            self._agents.pop(name, None)

    def get(self, name: str) -> Agent:
        with self._lock:
            if name not in self._agents:
                raise AgentError(f"Agent '{name}' is not registered")
            return self._agents[name]

    def has(self, name: str) -> bool:
        return name in self._agents

    def list(self) -> List[Agent]:
        with self._lock:
            return list(self._agents.values())

    def names(self) -> List[str]:
        with self._lock:
            return list(self._agents)

    def configs(self) -> List[AgentConfig]:
        return [a.config for a in self.list()]
