"""Agent system: definition, registry, roles, templates, communication."""
from .agent import Agent, AgentConfig, AgentStatus
from .communication import AgentMessage, Coordinator, MessageBus
from .crew import Crew, CrewResult, Process, Task
from .registry import AgentRegistry
from .roles import ROLES, AgentRole, RoleDefinition
from .templates import get_template, list_templates

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentStatus",
    "AgentRegistry",
    "AgentRole",
    "RoleDefinition",
    "ROLES",
    "Coordinator",
    "MessageBus",
    "AgentMessage",
    "Crew",
    "Task",
    "CrewResult",
    "Process",
    "get_template",
    "list_templates",
]
