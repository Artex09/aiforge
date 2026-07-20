"""Anthropic (Claude) provider adapter (lazy import).

The ``anthropic`` package is imported only on first use. Translates AIForge
messages into the Anthropic Messages API shape, including tool use.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..core.errors import ProviderError
from ..core.types import LLMResponse, Message, Role, ToolCall, Usage
from .base import LLMProvider, ProviderCapabilities, ProviderConfig


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    capabilities = ProviderCapabilities(
        streaming=True,
        function_calling=True,
        structured_output=True,
        vision=True,
        reasoning=True,
        embeddings=False,
    )

    def __init__(self, config: Optional[ProviderConfig] = None, **kwargs: Any):
        super().__init__(config, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic  # type: ignore
            except ImportError as exc:  # pragma: no cover - optional dep
                raise ProviderError(
                    "AnthropicProvider requires the 'anthropic' package: pip install anthropic"
                ) from exc
            self._client = Anthropic(api_key=self.config.api_key)
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
        system_prompt, converted = self._split_and_convert(messages)

        payload: Dict[str, Any] = {
            "model": self.config.model or "claude-fable-5",
            "messages": converted,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if tools:
            payload["tools"] = [self._to_anthropic_tool(t) for t in tools]
        payload.update(self.config.extra)

        resp = client.messages.create(**payload)

        content_text, tool_calls = "", []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                content_text += block.text
            elif getattr(block, "type", None) == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )
        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            finish_reason=resp.stop_reason or "stop",
            model=resp.model,
            usage=Usage(
                prompt_tokens=resp.usage.input_tokens,
                completion_tokens=resp.usage.output_tokens,
            ),
            raw=resp,
        )

    @staticmethod
    def _split_and_convert(messages: List[Message]):
        system_parts: List[str] = []
        converted: List[Dict[str, Any]] = []
        pending_tool_results: List[Dict[str, Any]] = []

        def _flush_tool_results() -> None:
            # The Anthropic API requires every tool_result for one assistant turn
            # to live in a single user message, so we coalesce consecutive ones.
            if pending_tool_results:
                converted.append({"role": "user", "content": list(pending_tool_results)})
                pending_tool_results.clear()

        for m in messages:
            if m.role == Role.SYSTEM:
                system_parts.append(m.content)
                continue
            if m.role == Role.TOOL:
                pending_tool_results.append(
                    {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                )
                continue
            _flush_tool_results()
            if m.role == Role.ASSISTANT and m.tool_calls:
                blocks: List[Dict[str, Any]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )
                converted.append({"role": "assistant", "content": blocks})
                continue
            converted.append({"role": m.role.value, "content": m.content})
        _flush_tool_results()  # trailing tool results (conversation ends on tools)
        return "\n".join(system_parts), converted

    @staticmethod
    def _to_anthropic_tool(tool: Dict[str, Any]) -> Dict[str, Any]:
        fn = tool.get("function", tool)
        return {
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        }
