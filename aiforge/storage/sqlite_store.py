"""SQLite storage backend (stdlib sqlite3 — the framework's "Database Support").

Provides durable key/value + ordered collections. Suitable for execution
history, workflow storage, memory persistence, and logs.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any, Dict, List

from ..core.types import new_id
from .base import StorageBackend


class SQLiteStorage(StorageBackend):
    def __init__(self, path: str = ".aiforge/aiforge.db"):
        import os

        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    namespace TEXT NOT NULL,
                    key       TEXT NOT NULL,
                    value     TEXT NOT NULL,
                    PRIMARY KEY (namespace, key)
                );
                CREATE TABLE IF NOT EXISTS records (
                    id         TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    payload    TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_records_coll
                    ON records (collection, created_at);
                """
            )

    # -------------------------------------------------------------- key/value
    def set(self, namespace: str, key: str, value: Any) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO kv(namespace,key,value) VALUES(?,?,?) "
                "ON CONFLICT(namespace,key) DO UPDATE SET value=excluded.value",
                (namespace, key, json.dumps(value, default=str)),
            )

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM kv WHERE namespace=? AND key=?", (namespace, key)
            ).fetchone()
        return json.loads(row["value"]) if row else default

    def delete(self, namespace: str, key: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM kv WHERE namespace=? AND key=?", (namespace, key)
            )

    def exists(self, namespace: str, key: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM kv WHERE namespace=? AND key=?", (namespace, key)
            ).fetchone()
        return row is not None

    def keys(self, namespace: str) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key FROM kv WHERE namespace=?", (namespace,)
            ).fetchall()
        return [r["key"] for r in rows]

    def items(self, namespace: str) -> Dict[str, Any]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key,value FROM kv WHERE namespace=?", (namespace,)
            ).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    # ---------------------------------------------------------------- records
    def append(self, collection: str, record: Dict[str, Any]) -> str:
        rec = dict(record)
        rid = rec.setdefault("id", new_id("rec"))
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO records(id,collection,payload,created_at) VALUES(?,?,?,?)",
                (rid, collection, json.dumps(rec, default=str), time.time()),
            )
        return rid

    def query(
        self, collection: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        # limit > 0 -> newest N; limit == 0 -> none; limit < 0 -> all (-1 in SQL).
        if limit == 0:
            return []
        sql_limit = limit if limit > 0 else -1
        with self._lock:
            rows = self._conn.execute(
                "SELECT payload FROM ("
                "  SELECT payload, created_at FROM records WHERE collection=?"
                "  ORDER BY created_at DESC LIMIT ? OFFSET ?"
                ") ORDER BY created_at ASC",
                (collection, sql_limit, offset),
            ).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
