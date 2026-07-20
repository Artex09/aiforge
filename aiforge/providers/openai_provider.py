"""OpenAI-compatible provider adapter (lazy import).

The ``openai`` package is only imported when this provider is actually used, so
the framework installs and runs without it. Any OpenAI-compatible endpoint
(``base_url``) works, keeping the layer provider-agnostic.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..core.errors import ProviderError
from ..core.types import (
    EmbeddingResponse,
    LLMResponse,
    Message,
    ToolCall,
    Usage,
)
from .base import LLMProvider, ProviderCapabilities, ProviderConfig


class OpenAIProvider(LLMProvider):
    name = "openai"
    capabilities = ProviderCapabilities(
        streaming=True,
        function_calling=True,
        structured_output=True,
        vision=True,
        reasoning=True,
        embeddings=True,
    )

    def __init__(self, config: Optional[ProviderConfig] = None, **kwargs: Any):
        super().__init__(config, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore
            except ImportError as exc:  # pragma: no cover - optional dep
                raise ProviderError(
                    "OpenAIProvider requires the 'openai' package: pip install openai"
                ) from exc
            self._client = OpenAI(
                api_key=self.config.api_key, base_url=self.config.base_url
            )
        return self._client

    def chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        client = self._get_client()
        payload: Dict[str, Any] = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": [self._to_openai(m) for m in messages],
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = kwargs.get("tool_choice", "auto")
        payload.update(self.config.extra)

        resp = client.chat.completions.create(**payload)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = []
        for tc in getattr(msg, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            model=resp.model,
            usage=Usage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            ),
            raw=resp,
        )

    def embed(self, texts: List[str], **kwargs: Any) -> EmbeddingResponse:
        client = self._get_client()
        model = kwargs.get("model", "text-embedding-3-small")
        resp = client.embeddings.create(model=model, input=texts)
        return EmbeddingResponse(
            vectors=[d.embedding for d in resp.data],
            model=resp.model,
            usage=Usage(prompt_tokens=getattr(resp.usage, "prompt_tokens", 0)),
        )

    @staticmethod
    def _to_openai(message: Message) -> Dict[str, Any]:
        out: Dict[str, Any] = {"role": message.role.value, "content": message.content}
        if message.name:
            out["name"] = message.name
        if message.tool_call_id:
            out["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in message.tool_calls
            ]
        return out
