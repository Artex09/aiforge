"""Shared data types for the AIForge framework.

These primitives are intentionally dependency-free (stdlib only) so the whole
framework can run without any third-party packages installed. Provider adapters
translate to/from these types at the edges.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


def new_id(prefix: str = "id") -> str:
    """Generate a short, unique, human-readable identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Role(str, Enum):
    """Conversation roles understood by every provider adapter."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """A request from an LLM to invoke a tool."""

    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: new_id("call"))

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}


@dataclass
class Message:
    """A single message in a conversation."""

    role: Role
    content: str = ""
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name:
            data["name"] = self.name
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            data["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        return data

    @classmethod
    def system(cls, content: str) -> "Message":
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(cls, content: str = "", tool_calls: Optional[List[ToolCall]] = None) -> "Message":
        return cls(role=Role.ASSISTANT, content=content, tool_calls=tool_calls or [])

    @classmethod
    def tool(cls, content: str, tool_call_id: str, name: Optional[str] = None) -> "Message":
        return cls(role=Role.TOOL, content=content, tool_call_id=tool_call_id, name=name)


@dataclass
class Usage:
    """Token accounting for a single LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    """Normalized response returned by every provider."""

    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    raw: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "finish_reason": self.finish_reason,
            "model": self.model,
            "usage": self.usage.to_dict(),
        }


@dataclass
class StreamChunk:
    """One increment of a streaming response."""

    delta: str = ""
    tool_call: Optional[ToolCall] = None
    done: bool = False


@dataclass
class EmbeddingResponse:
    """Result of an embedding request."""

    vectors: List[List[float]] = field(default_factory=list)
    model: str = ""
    usage: Usage = field(default_factory=Usage)


@dataclass
class RunResult:
    """The outcome of an agent or workflow run."""

    output: Any = None
    success: bool = True
    error: Optional[str] = None
    steps: int = 0
    usage: Usage = field(default_factory=Usage)
    messages: List[Message] = field(default_factory=list)
    context_id: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return (self.finished_at or time.time()) - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output": self.output,
            "success": self.success,
            "error": self.error,
            "steps": self.steps,
            "usage": self.usage.to_dict(),
            "context_id": self.context_id,
            "duration": self.duration,
            "metadata": self.metadata,
        }
