"""Embedding helper that prefers a provider but always has an offline fallback."""
from __future__ import annotations

from typing import List, Optional

from ..providers.base import LLMProvider
from ..providers.mock import _hash_embedding


class Embedder:
    """Wraps a provider's ``embed`` and falls back to deterministic hashing."""

    def __init__(self, provider: Optional[LLMProvider] = None, dimension: int = 256):
        self.provider = provider
        self.dimension = dimension

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self.provider is not None and self.provider.capabilities.embeddings:
            try:
                return self.provider.embed(texts).vectors
            except Exception:  # noqa: BLE001 - degrade to offline embeddings
                pass
        return [_hash_embedding(t, self.dimension) for t in texts]

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]
