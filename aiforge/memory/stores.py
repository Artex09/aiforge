"""Non-vector memory stores: short-term, working, session, long-term."""
from __future__ import annotations

import re
import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .base import MemoryKind, MemoryRecord, MemoryStore

# Common words carry no retrieval signal; counting them lets unrelated chatter
# outrank the actual answer (e.g. "what is aiforge?" matching every "is").
_STOPWORDS = frozenset(
    """a an and are as at be but by do does did for from has have how i in is it its
    me my of on or please tell that the this to was were what when where which who why
    will with you your about can could would should""".split()
)


def _terms(query: str) -> set:
    return {t for t in re.findall(r"\w+", query.lower()) if len(t) > 2 and t not in _STOPWORDS}


def _keyword_search(records: List[MemoryRecord], query: str, top_k: int) -> List[MemoryRecord]:
    terms = _terms(query)
    if not terms:
        return records[-top_k:]
    scored = []
    for rec in records:
        text = rec.content.lower()
        matched = sum(1 for t in terms if t in text)  # distinct terms covered
        if matched:
            freq = sum(text.count(t) for t in terms)
            # Coverage of distinct query terms dominates; raw frequency only breaks ties.
            rec.score = matched + min(freq, 9) * 0.05
            scored.append(rec)
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]


class ShortTermMemory(MemoryStore):
    """A bounded rolling buffer — the agent's recent conversational context."""

    kind = MemoryKind.SHORT_TERM

    def __init__(self, capacity: int = 20):
        self.capacity = capacity
        self._buffer: Deque[MemoryRecord] = deque(maxlen=capacity)
        self._lock = threading.RLock()

    def add(self, record: MemoryRecord) -> str:
        record.kind = self.kind
        with self._lock:
            self._buffer.append(record)
        return record.id

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        with self._lock:
            return next((r for r in self._buffer if r.id == record_id), None)

    def search(self, query: str, top_k: int = 5) -> List[MemoryRecord]:
        with self._lock:
            return _keyword_search(list(self._buffer), query, top_k)

    def all(self) -> List[MemoryRecord]:
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


class WorkingMemory(MemoryStore):
    """A scratchpad keyed by name — the agent's active variables/notes."""

    kind = MemoryKind.WORKING

    def __init__(self):
        self._slots: Dict[str, MemoryRecord] = {}
        self._lock = threading.RLock()

    def set(self, key: str, content: str, **metadata: Any) -> str:
        rec = MemoryRecord(content=content, kind=self.kind, metadata={"key": key, **metadata})
        with self._lock:
            self._slots[key] = rec
        return rec.id

    def get_slot(self, key: str) -> Optional[str]:
        with self._lock:
            rec = self._slots.get(key)
        return rec.content if rec else None

    def add(self, record: MemoryRecord) -> str:
        key = record.metadata.get("key", record.id)
        with self._lock:
            self._slots[key] = record
        return record.id

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        with self._lock:
            return next((r for r in self._slots.values() if r.id == record_id), None)

    def search(self, query: str, top_k: int = 5) -> List[MemoryRecord]:
        with self._lock:
            return _keyword_search(list(self._slots.values()), query, top_k)

    def all(self) -> List[MemoryRecord]:
        with self._lock:
            return list(self._slots.values())

    def clear(self) -> None:
        with self._lock:
            self._slots.clear()


class SessionMemory(MemoryStore):
    """Per-session history, optionally persisted to a storage backend."""

    kind = MemoryKind.SESSION

    def __init__(self, session_id: str = "default", backend: Any = None):
        self.session_id = session_id
        self._backend = backend
        self._records: List[MemoryRecord] = []
        self._lock = threading.RLock()
        self._restore()

    def _ns(self) -> str:
        return f"session_memory:{self.session_id}"

    def _restore(self) -> None:
        if self._backend is None:
            return
        stored = self._backend.get(self._ns(), "records", default=[])
        self._records = [MemoryRecord.from_dict(r) for r in stored or []]

    def _persist(self) -> None:
        if self._backend is not None:
            self._backend.set(self._ns(), "records", [r.to_dict() for r in self._records])

    def add(self, record: MemoryRecord) -> str:
        record.kind = self.kind
        with self._lock:
            self._records.append(record)
            self._persist()
        return record.id

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        with self._lock:
            return next((r for r in self._records if r.id == record_id), None)

    def search(self, query: str, top_k: int = 5) -> List[MemoryRecord]:
        with self._lock:
            return _keyword_search(list(self._records), query, top_k)

    def all(self) -> List[MemoryRecord]:
        with self._lock:
            return list(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._persist()


class LongTermMemory(MemoryStore):
    """Durable keyword-searchable memory persisted to a storage backend."""

    kind = MemoryKind.LONG_TERM

    def __init__(self, backend: Any = None, namespace: str = "long_term_memory"):
        self._backend = backend
        self._ns = namespace
        self._records: List[MemoryRecord] = []
        self._lock = threading.RLock()
        self._restore()

    def _restore(self) -> None:
        if self._backend is None:
            return
        stored = self._backend.get(self._ns, "records", default=[])
        self._records = [MemoryRecord.from_dict(r) for r in stored or []]

    def _persist(self) -> None:
        if self._backend is not None:
            self._backend.set(self._ns, "records", [r.to_dict() for r in self._records])

    def add(self, record: MemoryRecord) -> str:
        record.kind = self.kind
        with self._lock:
            self._records.append(record)
            self._persist()
        return record.id

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        with self._lock:
            return next((r for r in self._records if r.id == record_id), None)

    def search(self, query: str, top_k: int = 5) -> List[MemoryRecord]:
        with self._lock:
            return _keyword_search(list(self._records), query, top_k)

    def all(self) -> List[MemoryRecord]:
        with self._lock:
            return list(self._records)

    def delete(self, record_id: str) -> None:
        with self._lock:
            self._records = [r for r in self._records if r.id != record_id]
            self._persist()

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._persist()
