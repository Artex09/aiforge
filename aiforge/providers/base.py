"""LLM provider contract.

A provider translates AIForge :class:`Message` objects into a vendor API and
normalises the reply back into an :class:`LLMResponse`. Capabilities (streaming,
function-calling, vision, embeddings, reasoning) are declared so the framework
can route intelligently and degrade gracefully.
"""
from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from ..core.errors import ProviderError
from ..core.types import (
    EmbeddingResponse,
    LLMResponse,
    Message,
    StreamChunk,
)


@dataclass
class ProviderCapabilities:
    streaming: bool = False
    function_calling: bool = False
    structured_output: bool = False
    vision: bool = False
    reasoning: bool = False
    embeddings: bool = False


@dataclass
class ProviderConfig:
    name: str
    model: str = ""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    extra: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(abc.ABC):
    """Base class every provider adapter extends."""

    name: str = "base"
    capabilities: ProviderCapabilities = ProviderCapabilities()

    def __init__(self, config: Optional[ProviderConfig] = None, **kwargs: Any):
        self.config = config or ProviderConfig(name=self.name, **kwargs)

    # ------------------------------------------------------------------ chat
    @abc.abstractmethod
    def chat(
        self,
        messages: List[Message],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return a single completion for *messages*."""

    # ---------------------------------------------------------------- stream
    def stream(
        self, messages: List[Message], **kwargs: Any
    ) -> Iterator[StreamChunk]:
        """Yield the completion incrementally. Default: chunk a full reply."""
        response = self.chat(messages, **kwargs)
        for token in response.content.split(" "):
            yield StreamChunk(delta=token + " ")
        for call in response.tool_calls:
            yield StreamChunk(tool_call=call)
        yield StreamChunk(done=True)

    # ------------------------------------------------------------ structured
    def structured(
        self,
        messages: List[Message],
        schema: Dict[str, Any],
        *,
        max_attempts: int = 3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Return a dict conforming to *schema*, validating and re-asking on failure.

        Default strategy: instruct the model to answer with JSON only, parse it,
        validate against the schema, and — if invalid — feed the errors back and
        retry up to ``max_attempts`` times. Providers with native structured
        output should override for a single-shot guarantee.
        """
        from ..core.schema import validate_against_schema

        convo: List[Message] = [
            Message.system(
                "You must respond with a single valid JSON object that conforms to "
                "this JSON schema. Do not include prose or code fences.\n" + json.dumps(schema)
            ),
            *messages,
        ]
        last_error = "no attempt made"
        for _ in range(max(1, max_attempts)):
            response = self.chat(convo, **kwargs)
            try:
                data = self._extract_json(response.content)
            except ProviderError as exc:
                last_error = str(exc)
                convo.append(Message.assistant(response.content))
                convo.append(Message.user(f"That was not valid JSON ({exc}). Return only JSON."))
                continue
            problems = validate_against_schema(data, schema)
            if not problems:
                return data
            last_error = "; ".join(problems)
            convo.append(Message.assistant(response.content))
            convo.append(
                Message.user("The JSON did not match the schema: " + last_error + ". Fix it.")
            )
        raise ProviderError(f"Could not obtain schema-valid structured output: {last_error}")

    # ------------------------------------------------------------- embeddings
    def embed(self, texts: List[str], **kwargs: Any) -> EmbeddingResponse:
        raise ProviderError(f"Provider '{self.name}' does not support embeddings")

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Model did not return valid JSON: {exc}") from exc

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.name} model={self.config.model}>"
