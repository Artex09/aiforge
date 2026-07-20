"""Exception hierarchy for AIForge.

Every framework-raised error derives from :class:`AIForgeError` so callers can
catch the whole family with a single ``except``.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class AIForgeError(Exception):
    """Base class for all framework errors."""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error": type(self).__name__, "message": self.message, "details": self.details}


class ConfigError(AIForgeError):
    """Invalid or missing configuration."""


class ProviderError(AIForgeError):
    """An LLM provider failed or is misconfigured."""


class ProviderNotFoundError(ProviderError):
    """Requested provider is not registered."""


class ToolError(AIForgeError):
    """A tool failed during execution."""


class ToolNotFoundError(ToolError):
    """Requested tool is not registered."""


class ToolValidationError(ToolError):
    """Tool arguments failed schema validation."""


class ToolPermissionError(ToolError):
    """A caller lacks permission to use a tool."""


class MemoryError_(AIForgeError):
    """Memory subsystem failure."""


class AgentError(AIForgeError):
    """An agent failed."""


class WorkflowError(AIForgeError):
    """A workflow failed to validate or execute."""


class StepError(WorkflowError):
    """A single workflow step failed."""


class StorageError(AIForgeError):
    """A storage backend operation failed."""


class PluginError(AIForgeError):
    """A plugin failed to load or register."""


class ValidationError(AIForgeError):
    """Generic validation failure (state, schema, etc.)."""


class ExecutionLimitError(AIForgeError):
    """An execution limit (steps, tokens, tool calls) was exceeded."""


class TimeoutError_(AIForgeError):
    """An operation exceeded its allotted time."""


class AuthError(AIForgeError):
    """Authentication or authorization failure."""
