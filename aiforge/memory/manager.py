"""MemoryManager — unifies every memory store behind one API.

Implements the catalog's Memory System: short/long/working/session/vector
stores plus Retrieval (cross-store), Ranking (recency + relevance), and
Compression (summarise old short-term memory to keep context small).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..events.bus import EventBus, EventType
from ..providers.base import LLMProvider
from ..core.types import Message
from .base import MemoryKind, MemoryRecord
from .embeddings import Embedder
from .stores import LongTermMemory, SessionMemory, ShortTermMemory, WorkingMemory
from .vector import VectorMemory


class MemoryManager:
    def __init__(
        self,
        *,
        embedder: Optional[Embedder] = None,
        backend: Any = None,
        events: Optional[EventBus] = None,
        provider: Optional[LLMProvider] = None,
        short_term_capacity: int = 20,
        session_id: str = "default",
        compression_threshold: int = 40,
        compression_enabled: bool = True,
    ):
        self.events = events
        self.provider = provider
        self.embedder = embedder or Embedder(provider)
        self.compression_threshold = compression_threshold
        self.compression_enabled = compression_enabled

        self.short_term = ShortTermMemory(capacity=short_term_capacity)
        self.working = WorkingMemory()
        self.session = SessionMemory(session_id=session_id, backend=backend)
        self.long_term = LongTermMemory(backend=backend)
        self.vector = VectorMemory(self.embedder)

        self._stores = {
            MemoryKind.SHORT_TERM: self.short_term,
            MemoryKind.WORKING: self.working,
            MemoryKind.SESSION: self.session,
            MemoryKind.LONG_TERM: self.long_term,
            MemoryKind.VECTOR: self.vector,
        }

    # ------------------------------------------------------------------ write
    def remember(
        self,
        content: str,
        kind: MemoryKind = MemoryKind.SHORT_TERM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        record = MemoryRecord(content=content, kind=kind, metadata=metadata or {})
        rid = self._stores[kind].add(record)
        self._emit(EventType.MEMORY_WRITE, {"kind": kind.value, "id": rid, "content": content[:120]})
        if kind == MemoryKind.SHORT_TERM and self.compression_enabled:
            self._maybe_compress()
        return rid

    def remember_semantic(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store in both long-term and vector memory for durable, semantic recall."""
        self.long_term.add(MemoryRecord(content=content, kind=MemoryKind.LONG_TERM, metadata=metadata or {}))
        return self.remember(content, MemoryKind.VECTOR, metadata)

    # ------------------------------------------------------------------- read
    def recall(
        self,
        query: str,
        top_k: int = 5,
        kinds: Optional[List[MemoryKind]] = None,
        rrf_k: int = 60,
    ) -> List[MemoryRecord]:
        """Retrieve across stores and fuse with Reciprocal Rank Fusion.

        Each store returns its own ranked list; RRF combines them by rank
        (``score = Σ 1/(rrf_k + rank)``) rather than by raw score, so a cosine
        similarity and a keyword-overlap count — which live on different scales —
        can be merged fairly. This is the principled alternative to blending
        heterogeneous scores directly.
        """
        kinds = kinds or [MemoryKind.VECTOR, MemoryKind.LONG_TERM, MemoryKind.SHORT_TERM]
        fused: Dict[str, Dict[str, Any]] = {}
        for kind in kinds:
            results = self._stores[kind].search(query, top_k)
            for rank_index, rec in enumerate(results):
                contribution = 1.0 / (rrf_k + rank_index + 1)
                entry = fused.get(rec.content)
                if entry is None:
                    fused[rec.content] = {"record": rec, "score": contribution}
                else:
                    entry["score"] += contribution
        ordered = sorted(fused.values(), key=lambda e: e["score"], reverse=True)[:top_k]
        out: List[MemoryRecord] = []
        for entry in ordered:
            record = entry["record"]
            record.score = round(entry["score"], 6)
            out.append(record)
        self._emit(EventType.MEMORY_READ, {"query": query[:120], "hits": len(out)})
        return out

    def rank(self, records: List[MemoryRecord]) -> List[MemoryRecord]:
        """Combine normalized relevance score with recency for a final ranking."""
        if not records:
            return []
        now = time.time()
        max_score = max((r.score for r in records), default=1.0) or 1.0
        oldest = min((r.timestamp for r in records), default=now)
        span = max(now - oldest, 1.0)
        for rec in records:
            relevance = rec.score / max_score
            recency = 1.0 - ((now - rec.timestamp) / span)
            rec.score = round(0.7 * relevance + 0.3 * recency, 6)
        deduped: Dict[str, MemoryRecord] = {}
        for rec in sorted(records, key=lambda r: r.score, reverse=True):
            deduped.setdefault(rec.content, rec)
        return list(deduped.values())

    def context_messages(self, query: Optional[str] = None, top_k: int = 5) -> List[Message]:
        """Build system messages injecting relevant memories into a prompt."""
        records = self.recall(query, top_k) if query else self.short_term.all()[-top_k:]
        if not records:
            return []
        lines = "\n".join(f"- {r.content}" for r in records)
        return [Message.system(f"Relevant memory:\n{lines}")]

    # ------------------------------------------------------------- compression
    def _maybe_compress(self) -> None:
        records = self.short_term.all()
        if len(records) < self.compression_threshold:
            return
        self.compress()

    def compress(self) -> Optional[str]:
        """Summarise the oldest half of short-term memory into one long-term record."""
        records = self.short_term.all()
        if not records:
            return None
        half = max(1, len(records) // 2)
        to_compress = records[:half]
        joined = "\n".join(r.content for r in to_compress)
        summary = self._summarize(joined)
        self.long_term.add(
            MemoryRecord(
                content=f"[summary] {summary}",
                kind=MemoryKind.LONG_TERM,
                metadata={"compressed_from": len(to_compress)},
            )
        )
        # rebuild short-term with the retained recent half
        self.short_term.clear()
        for rec in records[half:]:
            self.short_term.add(rec)
        self._emit(EventType.MEMORY_COMPRESS, {"compressed": len(to_compress)})
        return summary

    def _summarize(self, text: str) -> str:
        if self.provider is not None:
            try:
                resp = self.provider.chat(
                    [
                        Message.system("Summarise the following notes in 2-3 sentences."),
                        Message.user(text[:4000]),
                    ]
                )
                return resp.content.strip()
            except Exception:  # noqa: BLE001 - fall back to truncation
                pass
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        return ". ".join(sentences[:3])[:500]

    # ------------------------------------------------------------------ utils
    def clear(self) -> None:
        for store in self._stores.values():
            store.clear()

    def stats(self) -> Dict[str, int]:
        return {kind.value: len(store.all()) for kind, store in self._stores.items()}

    def _emit(self, etype: EventType, data: Dict[str, Any]) -> None:
        if self.events is not None:
            self.events.emit(etype, data, source="memory")
