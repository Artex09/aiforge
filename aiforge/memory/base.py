"""Memory record type and the store contract."""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.types import new_id


class MemoryKind(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"
    SESSION = "session"
    VECTOR = "vector"


@dataclass
class MemoryRecord:
    content: str
    kind: MemoryKind = MemoryKind.SHORT_TERM
    id: str = field(default_factory=lambda: new_id("mem"))
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    embedding: Optional[List[float]] = None
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "kind": self.kind.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        return cls(
            id=data.get("id", new_id("mem")),
            content=data["content"],
            kind=MemoryKind(data.get("kind", "short_term")),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
            embedding=data.get("embedding"),
            score=data.get("score", 0.0),
        )


class MemoryStore(abc.ABC):
    """Abstract store for a single memory type."""

    kind: MemoryKind = MemoryKind.SHORT_TERM

    @abc.abstractmethod
    def add(self, record: MemoryRecord) -> str: ...

    @abc.abstractmethod
    def get(self, record_id: str) -> Optional[MemoryRecord]: ...

    @abc.abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[MemoryRecord]: ...

    @abc.abstractmethod
    def all(self) -> List[MemoryRecord]: ...

    @abc.abstractmethod
    def clear(self) -> None: ...

    def delete(self, record_id: str) -> None:  # pragma: no cover - optional
        pass

    def __len__(self) -> int:
        return len(self.all())
