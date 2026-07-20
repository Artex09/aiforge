"""Vector memory — semantic recall backed by an embedder + vector store."""
from __future__ import annotations

import threading
from typing import Any, List, Optional

from ..storage.vector_store import InMemoryVectorStore
from .base import MemoryKind, MemoryRecord, MemoryStore
from .embeddings import Embedder


class VectorMemory(MemoryStore):
    kind = MemoryKind.VECTOR

    def __init__(
        self,
        embedder: Embedder,
        store: Optional[InMemoryVectorStore] = None,
        top_k: int = 5,
    ):
        self.embedder = embedder
        self.store = store or InMemoryVectorStore()
        self.top_k = top_k
        self._records: dict = {}
        self._lock = threading.RLock()
        self._hydrate()

    def _hydrate(self) -> None:
        for rec in self.store.all():
            self._records[rec.id] = MemoryRecord(
                id=rec.id,
                content=rec.text,
                kind=self.kind,
                metadata=rec.metadata,
                embedding=rec.vector,
            )

    def add(self, record: MemoryRecord) -> str:
        record.kind = self.kind
        if record.embedding is None:
            record.embedding = self.embedder.embed_one(record.content)
        with self._lock:
            self.store.add(
                record.embedding, text=record.content, metadata=record.metadata, id=record.id
            )
            self._records[record.id] = record
        return record.id

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        with self._lock:
            return self._records.get(record_id)

    def search(self, query: str, top_k: Optional[int] = None) -> List[MemoryRecord]:
        vector = self.embedder.embed_one(query)
        hits = self.store.search(vector, top_k=top_k or self.top_k)
        out: List[MemoryRecord] = []
        for vrec, score in hits:
            record = self._records.get(vrec.id)
            if record is None:
                record = MemoryRecord(
                    id=vrec.id, content=vrec.text, kind=self.kind, metadata=vrec.metadata
                )
            record.score = score
            out.append(record)
        return out

    def all(self) -> List[MemoryRecord]:
        with self._lock:
            return list(self._records.values())

    def delete(self, record_id: str) -> None:
        with self._lock:
            self.store.delete(record_id)
            self._records.pop(record_id, None)

    def clear(self) -> None:
        with self._lock:
            self.store.clear()
            self._records.clear()
