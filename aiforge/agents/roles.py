"""Agent roles — built-in archetypes plus a registry for custom roles.

A role bundles a default system-prompt fragment and a suggested permission set,
giving agents a coherent behavioural identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class AgentRole(str, Enum):
    ASSISTANT = "assistant"
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYST = "analyst"
    PLANNER = "planner"
    CRITIC = "critic"
    ROUTER = "router"
    EXECUTOR = "executor"
    CUSTOM = "custom"


@dataclass
class RoleDefinition:
    name: str
    prompt: str
    default_permissions: List[str] = field(default_factory=list)


_BUILTIN: Dict[str, RoleDefinition] = {
    AgentRole.ASSISTANT.value: RoleDefinition(
        "assistant", "You are a helpful, concise general-purpose assistant.", []
    ),
    AgentRole.RESEARCHER.value: RoleDefinition(
        "researcher",
        "You are a meticulous researcher. Gather facts with tools, cite sources, "
        "and separate evidence from inference.",
        ["network"],
    ),
    AgentRole.CODER.value: RoleDefinition(
        "coder",
        "You are an expert software engineer. Write correct, minimal, well-tested code "
        "and explain trade-offs briefly.",
        ["fs"],
    ),
    AgentRole.ANALYST.value: RoleDefinition(
        "analyst",
        "You are a data analyst. Compute precisely, quantify uncertainty, and prefer "
        "tables and concrete numbers.",
        [],
    ),
    AgentRole.PLANNER.value: RoleDefinition(
        "planner",
        "You decompose goals into ordered, verifiable steps and delegate to other agents.",
        [],
    ),
    AgentRole.CRITIC.value: RoleDefinition(
        "critic",
        "You adversarially review work for errors, gaps, and unstated assumptions.",
        [],
    ),
    AgentRole.ROUTER.value: RoleDefinition(
        "router", "You classify a request and route it to the most suitable agent.", []
    ),
    AgentRole.EXECUTOR.value: RoleDefinition(
        "executor", "You carry out concrete actions using the available tools.", ["fs", "network"]
    ),
}


class RoleRegistry:
    def __init__(self):
        self._roles: Dict[str, RoleDefinition] = dict(_BUILTIN)

    def register(self, definition: RoleDefinition) -> None:
        self._roles[definition.name] = definition

    def get(self, name: str) -> RoleDefinition:
        return self._roles.get(name, _BUILTIN[AgentRole.ASSISTANT.value])

    def names(self) -> List[str]:
        return list(self._roles)


ROLES = RoleRegistry()
