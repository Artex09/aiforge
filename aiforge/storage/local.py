"""Local filesystem storage backend (JSON files, zero dependencies)."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List

from ..core.errors import StorageError
from ..core.types import new_id
from .base import StorageBackend


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


class LocalStorage(StorageBackend):
    """Persists namespaces as ``<root>/<namespace>.json`` and collections as
    newline-delimited JSON under ``<root>/collections/<name>.ndjson``."""

    def __init__(self, root: str = ".aiforge"):
        self.root = os.path.abspath(root)
        self._lock = threading.RLock()
        os.makedirs(self.root, exist_ok=True)
        os.makedirs(os.path.join(self.root, "collections"), exist_ok=True)

    # -------------------------------------------------------------- internals
    def _ns_path(self, namespace: str) -> str:
        return os.path.join(self.root, f"{_safe(namespace)}.json")

    def _load_ns(self, namespace: str) -> Dict[str, Any]:
        path = self._ns_path(namespace)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            raise StorageError(f"Failed to read namespace '{namespace}': {exc}") from exc

    def _save_ns(self, namespace: str, data: Dict[str, Any]) -> None:
        path = self._ns_path(namespace)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
        os.replace(tmp, path)  # atomic on POSIX and Windows

    # -------------------------------------------------------------- key/value
    def set(self, namespace: str, key: str, value: Any) -> None:
        with self._lock:
            data = self._load_ns(namespace)
            data[key] = value
            self._save_ns(namespace, data)

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._load_ns(namespace).get(key, default)

    def delete(self, namespace: str, key: str) -> None:
        with self._lock:
            data = self._load_ns(namespace)
            data.pop(key, None)
            self._save_ns(namespace, data)

    def exists(self, namespace: str, key: str) -> bool:
        with self._lock:
            return key in self._load_ns(namespace)

    def keys(self, namespace: str) -> List[str]:
        with self._lock:
            return list(self._load_ns(namespace).keys())

    def items(self, namespace: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._load_ns(namespace))

    # ---------------------------------------------------------------- records
    def _coll_path(self, collection: str) -> str:
        return os.path.join(self.root, "collections", f"{_safe(collection)}.ndjson")

    def append(self, collection: str, record: Dict[str, Any]) -> str:
        rec = dict(record)
        rec.setdefault("id", new_id("rec"))
        with self._lock:
            with open(self._coll_path(collection), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, default=str) + "\n")
        return rec["id"]

    def query(
        self, collection: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        path = self._coll_path(collection)
        if not os.path.exists(path):
            return []
        with self._lock:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        records = [json.loads(line) for line in lines if line.strip()]
        if offset:
            records = records[offset:]
        # limit > 0 -> newest N; limit == 0 -> none; limit < 0 -> all.
        if limit == 0:
            return []
        return records[-limit:] if limit > 0 else records
