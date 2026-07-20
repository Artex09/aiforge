"""Storage backend contract.

Backends provide a namespaced key/value surface plus append-only records for
execution history and logs. Concrete backends: :mod:`local` (JSON files) and
:mod:`sqlite_store` (stdlib sqlite3). Everything is JSON-serialisable.
"""
from __future__ import annotations

import abc
from typing import Any, Dict, Iterable, List, Optional


class StorageBackend(abc.ABC):
    """Abstract namespaced key/value + record store."""

    # -------------------------------------------------------------- key/value
    @abc.abstractmethod
    def set(self, namespace: str, key: str, value: Any) -> None: ...

    @abc.abstractmethod
    def get(self, namespace: str, key: str, default: Any = None) -> Any: ...

    @abc.abstractmethod
    def delete(self, namespace: str, key: str) -> None: ...

    @abc.abstractmethod
    def exists(self, namespace: str, key: str) -> bool: ...

    @abc.abstractmethod
    def keys(self, namespace: str) -> List[str]: ...

    @abc.abstractmethod
    def items(self, namespace: str) -> Dict[str, Any]: ...

    def clear(self, namespace: str) -> None:
        for key in self.keys(namespace):
            self.delete(namespace, key)

    # ---------------------------------------------------------------- records
    @abc.abstractmethod
    def append(self, collection: str, record: Dict[str, Any]) -> str:
        """Append *record* to an ordered *collection*; return its id."""

    @abc.abstractmethod
    def query(
        self, collection: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Return records from *collection*, newest last."""

    def close(self) -> None:  # pragma: no cover - optional
        """Release any resources held by the backend."""
