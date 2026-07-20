"""Provider registry with fallback chains.

Register provider instances by name, pick a default, and define an ordered
fallback list so a failing primary provider transparently rolls over.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ..core.errors import ProviderError, ProviderNotFoundError
from ..core.types import LLMResponse, Message
from .base import LLMProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._default: Optional[str] = None
        self._fallbacks: List[str] = []
        self._lock = threading.RLock()

    def register(
        self, provider: LLMProvider, *, default: bool = False
    ) -> LLMProvider:
        with self._lock:
            self._providers[provider.name] = provider
            if default or self._default is None:
                self._default = provider.name
        return provider

    def unregister(self, name: str) -> None:
        with self._lock:
            self._providers.pop(name, None)
            if self._default == name:
                self._default = next(iter(self._providers), None)

    def get(self, name: Optional[str] = None) -> LLMProvider:
        with self._lock:
            key = name or self._default
            if key is None:
                raise ProviderNotFoundError("No providers registered")
            if key not in self._providers:
                raise ProviderNotFoundError(f"Provider '{key}' is not registered")
            return self._providers[key]

    def names(self) -> List[str]:
        with self._lock:
            return list(self._providers)

    def set_default(self, name: str) -> None:
        with self._lock:
            if name not in self._providers:
                raise ProviderNotFoundError(f"Provider '{name}' is not registered")
            self._default = name

    def set_fallbacks(self, names: List[str]) -> None:
        self._fallbacks = list(names)

    def chat_with_fallback(
        self, messages: List[Message], *, provider: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """Try the requested/default provider, then each fallback in order."""
        chain: List[str] = []
        primary = provider or self._default
        if primary:
            chain.append(primary)
        chain.extend(n for n in self._fallbacks if n not in chain)

        errors: List[str] = []
        for name in chain:
            try:
                return self.get(name).chat(messages, **kwargs)
            except Exception as exc:  # noqa: BLE001 - roll over to next provider
                errors.append(f"{name}: {exc}")
        raise ProviderError(
            "All providers failed", details={"attempts": errors or ["<none>"]}
        )
