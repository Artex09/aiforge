"""Vector database abstraction with a pure-Python default implementation.

The default :class:`InMemoryVectorStore` needs no third-party packages. It uses
cosine similarity computed in pure Python (NumPy is used automatically if
available for speed). Records optionally persist to a :class:`StorageBackend`.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..core.types import new_id
from .base import StorageBackend

try:  # optional acceleration, never required
    import numpy as _np  # type: ignore

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    _np = None
    _HAS_NUMPY = False


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if _HAS_NUMPY:
        va, vb = _np.asarray(a, dtype=float), _np.asarray(b, dtype=float)
        denom = float(_np.linalg.norm(va) * _np.linalg.norm(vb))
        return float(va.dot(vb) / denom) if denom else 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


@dataclass
class VectorRecord:
    id: str
    vector: List[float]
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "vector": self.vector, "text": self.text, "metadata": self.metadata}


class InMemoryVectorStore:
    """A cosine-similarity vector index with optional durable persistence."""

    def __init__(
        self,
        namespace: str = "default",
        backend: Optional[StorageBackend] = None,
    ):
        self.namespace = namespace
        self.backend = backend
        self._records: Dict[str, VectorRecord] = {}
        self._lock = threading.RLock()
        if backend is not None:
            self._restore()

    def _restore(self) -> None:
        assert self.backend is not None
        stored = self.backend.get("vector_store", self.namespace, default={})
        for rid, raw in (stored or {}).items():
            self._records[rid] = VectorRecord(
                id=rid,
                vector=raw["vector"],
                text=raw.get("text", ""),
                metadata=raw.get("metadata", {}),
            )

    def _persist(self) -> None:
        if self.backend is None:
            return
        self.backend.set(
            "vector_store",
            self.namespace,
            {rid: r.to_dict() for rid, r in self._records.items()},
        )

    def add(
        self,
        vector: List[float],
        text: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
    ) -> str:
        rid = id or new_id("vec")
        with self._lock:
            self._records[rid] = VectorRecord(rid, list(vector), text, metadata or {})
            self._persist()
        return rid

    def delete(self, id: str) -> None:
        with self._lock:
            self._records.pop(id, None)
            self._persist()

    def search(
        self, query_vector: List[float], top_k: int = 5, threshold: float = 0.0
    ) -> List[Tuple[VectorRecord, float]]:
        with self._lock:
            scored = [
                (rec, cosine_similarity(query_vector, rec.vector))
                for rec in self._records.values()
            ]
        scored = [pair for pair in scored if pair[1] >= threshold]
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[:top_k]

    def all(self) -> List[VectorRecord]:
        with self._lock:
            return list(self._records.values())

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._persist()

    def __len__(self) -> int:
        return len(self._records)
