"""In-memory TTL cache for the storage layer."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """A simple thread-safe cache with per-entry time-to-live."""

    def __init__(self, default_ttl: float = 300.0, max_size: int = 4096):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def _now(self) -> float:
        return time.time()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            expires, value = entry
            if expires and expires < self._now():
                self._store.pop(key, None)
                return default
            return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        with self._lock:
            if len(self._store) >= self.max_size:
                self._evict()
            ttl = self.default_ttl if ttl is None else ttl
            expires = self._now() + ttl if ttl else 0.0
            self._store[key] = (expires, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def _evict(self) -> None:
        # Drop expired first; if still full, drop the oldest-expiring entry.
        now = self._now()
        expired = [k for k, (exp, _) in self._store.items() if exp and exp < now]
        for k in expired:
            self._store.pop(k, None)
        if len(self._store) >= self.max_size and self._store:
            oldest = min(self._store.items(), key=lambda kv: kv[1][0] or float("inf"))[0]
            self._store.pop(oldest, None)
