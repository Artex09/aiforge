"""Deterministic, offline mock provider.

This is what makes AIForge runnable and testable with zero API keys and zero
network access. It implements the full capability surface: chat, streaming,
function-calling (via a simple heuristic), structured output, and deterministic
hash-based embeddings.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable, Dict, List, Optional

from ..core.types import (
    EmbeddingResponse,
    LLMResponse,
    Message,
    Role,
    ToolCall,
    Usage,
)
from .base import LLMProvider, ProviderCapabilities, ProviderConfig

# A scripted-response hook: given the message list, optionally return a canned
# LLMResponse. Useful for tests and deterministic examples.
ScriptFn = Callable[[List[Message]], Optional[LLMResponse]]


def _hash_embedding(text: str, dim: int = 256) -> List[float]:
    """Deterministic bag-of-hashed-tokens embedding, L2-normalised."""
    vec = [0.0] * dim
    for token in re.findall(r"\w+", text.lower()):
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
        vec[(h // dim) % dim] += 0.5
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec] if norm else vec


class MockProvider(LLMProvider):
    """Offline provider with predictable behaviour."""

    name = "mock"
    capabilities = ProviderCapabilities(
        streaming=True,
        function_calling=True,
        structured_output=True,
        vision=True,
        reasoning=True,
        embeddings=True,
    )

    def __init__(
        self,
        config: Optional[ProviderConfig] = None,
        script: Optional[ScriptFn] = None,
        canned: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ):
        super().__init__(config, **kwargs)
        self.script = script
        self.canned = canned or {}
        self._dim = 256

    def chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if self.script:
            scripted = self.script(messages)
            if scripted is not None:
                return scripted

        last_user = next(
            (m for m in reversed(messages) if m.role == Role.USER), None
        )
        prompt = last_user.content if last_user else ""

        # Canned exact-match replies take priority.
        for key, reply in self.canned.items():
            if key.lower() in prompt.lower():
                return self._resp(reply, messages)

        # Once a tool result is available, synthesize a final answer instead of
        # calling another tool — this prevents infinite tool-call loops.
        awaiting_answer = bool(messages) and messages[-1].role == Role.TOOL

        # If tools are offered and the prompt asks to compute/use one, emit a
        # tool call for the first tool whose name is referenced.
        if tools and not awaiting_answer:
            call = self._maybe_tool_call(prompt, tools)
            if call is not None:
                return LLMResponse(
                    content="",
                    tool_calls=[call],
                    finish_reason="tool_calls",
                    model=self.config.model or "aiforge-mock-1",
                    usage=self._usage(messages, ""),
                )

        reply = self._reflect(prompt, messages)
        return self._resp(reply, messages)

    # -------------------------------------------------------------- helpers
    def _maybe_tool_call(
        self, prompt: str, tools: List[Dict[str, Any]]
    ) -> Optional[ToolCall]:
        for tool in tools:
            fn = tool.get("function", tool)
            name = fn.get("name", "")
            if name and name.lower() in prompt.lower():
                args = self._guess_args(prompt, fn)
                return ToolCall(name=name, arguments=args)
        # calculator heuristic
        if re.search(r"\d\s*[-+*/]\s*\d", prompt):
            for tool in tools:
                fn = tool.get("function", tool)
                if fn.get("name") in {"calculator", "calc"}:
                    # Capture a full arithmetic expression (digit … operator … digit).
                    expr = re.search(r"\d[\d\s+\-*/().]*\d", prompt)
                    return ToolCall(
                        name=fn["name"],
                        arguments={"expression": (expr.group(0).strip() if expr else "0")},
                    )
        return None

    @staticmethod
    def _guess_args(prompt: str, fn: Dict[str, Any]) -> Dict[str, Any]:
        params = (fn.get("parameters") or {}).get("properties", {})
        args: Dict[str, Any] = {}
        for pname, spec in params.items():
            if spec.get("type") == "string":
                args[pname] = prompt
            elif spec.get("type") in {"number", "integer"}:
                m = re.search(r"-?\d+(?:\.\d+)?", prompt)
                args[pname] = float(m.group(0)) if m else 0
            elif spec.get("type") == "boolean":
                args[pname] = True
        return args

    def _reflect(self, prompt: str, messages: List[Message]) -> str:
        system = next((m for m in messages if m.role == Role.SYSTEM), None)
        persona = ""
        if system and system.content:
            persona = system.content.strip().splitlines()[0][:80]
        tool_results = [m for m in messages if m.role == Role.TOOL]
        if tool_results:
            return (
                f"Based on the tool results ({tool_results[-1].content[:200]}), "
                f"here is the answer to: {prompt[:120]}"
            )
        prefix = f"[{persona}] " if persona else ""
        if not prompt:
            return f"{prefix}Hello — I am an AIForge mock agent ready to help."
        return f"{prefix}Mock response to: {prompt[:200]}"

    def _resp(self, content: str, messages: List[Message]) -> LLMResponse:
        return LLMResponse(
            content=content,
            finish_reason="stop",
            model=self.config.model or "aiforge-mock-1",
            usage=self._usage(messages, content),
        )

    @staticmethod
    def _usage(messages: List[Message], content: str) -> Usage:
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        return Usage(prompt_tokens=prompt_tokens, completion_tokens=len(content.split()))

    def structured(
        self, messages: List[Message], schema: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        # Produce a plausible object satisfying the schema deterministically.
        props = schema.get("properties", {})
        last_user = next((m for m in reversed(messages) if m.role == Role.USER), None)
        text = last_user.content if last_user else ""
        out: Dict[str, Any] = {}
        for key, spec in props.items():
            t = spec.get("type", "string")
            if t == "string":
                out[key] = text[:120] or f"mock-{key}"
            elif t in {"number", "integer"}:
                out[key] = 0
            elif t == "boolean":
                out[key] = True
            elif t == "array":
                out[key] = []
            elif t == "object":
                out[key] = {}
        return out

    def embed(self, texts: List[str], **kwargs: Any) -> EmbeddingResponse:
        vectors = [_hash_embedding(t, self._dim) for t in texts]
        return EmbeddingResponse(
            vectors=vectors,
            model=self.config.model or "aiforge-embed-1",
            usage=Usage(prompt_tokens=sum(len(t.split()) for t in texts)),
        )
