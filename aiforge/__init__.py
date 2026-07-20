"""AIForge — a modular framework for building autonomous multi-agent AI systems.

Public API::

    from aiforge import AIForge, Engine, Config
    from aiforge import Agent, AgentConfig, tool, WorkflowBuilder

Design philosophy: modular, extensible, framework-first, provider-agnostic,
tool-first, memory-first, event-driven, production-ready, developer-friendly.
"""
from __future__ import annotations

__version__ = "0.3.0"
__all__ = [
    "__version__",
    "AIForge",
    "Engine",
    "Config",
    "Agent",
    "AgentConfig",
    "tool",
    "Tool",
    "ToolResult",
    "WorkflowBuilder",
    "Message",
    "EventType",
]

from .agents.agent import Agent, AgentConfig
from .config.settings import Config
from .core.engine import Engine
from .core.types import Message
from .events.bus import EventType
from .sdk.client import AIForge
from .tools.base import Tool, ToolResult, tool
from .workflows.builder import WorkflowBuilder
