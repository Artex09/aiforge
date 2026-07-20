"""State management: global/local/shared state with versioning, validation,
and optional persistence.

Scopes:
  * ``global``  — shared across the whole engine
  * ``<scope>`` — arbitrary named local scopes (e.g. per-agent, per-workflow)
  * ``shared``  — an explicit cross-agent shared context

Every mutation is versioned so a prior snapshot can be restored.
"""
from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .errors import ValidationError

Validator = Callable[[str, Any], None]


@dataclass
class StateVersion:
    version: int
    scope: str
    snapshot: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class StateManager:
    def __init__(self, backend: Any = None, persist_namespace: str = "state"):
        self._scopes: Dict[str, Dict[str, Any]] = {"global": {}, "shared": {}}
        self._versions: List[StateVersion] = []
        self._validators: Dict[str, List[Validator]] = {}
        self._counter = 0
        self._backend = backend
        self._ns = persist_namespace
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ access
    def get(self, key: str, default: Any = None, scope: str = "global") -> Any:
        with self._lock:
            return copy.deepcopy(self._scopes.get(scope, {}).get(key, default))

    def set(self, key: str, value: Any, scope: str = "global") -> None:
        self._validate(scope, key, value)
        with self._lock:
            self._scopes.setdefault(scope, {})[key] = copy.deepcopy(value)
            self._record(scope)
        self._persist(scope)

    def update(self, values: Dict[str, Any], scope: str = "global") -> None:
        for key, value in values.items():
            self._validate(scope, key, value)
        with self._lock:
            self._scopes.setdefault(scope, {}).update(copy.deepcopy(values))
            self._record(scope)
        self._persist(scope)

    def delete(self, key: str, scope: str = "global") -> None:
        with self._lock:
            self._scopes.get(scope, {}).pop(key, None)
            self._record(scope)
        self._persist(scope)

    def all(self, scope: str = "global") -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._scopes.get(scope, {}))

    def scopes(self) -> List[str]:
        with self._lock:
            return list(self._scopes)

    def clear(self, scope: Optional[str] = None) -> None:
        with self._lock:
            if scope is None:
                self._scopes = {"global": {}, "shared": {}}
            else:
                self._scopes[scope] = {}

    # -------------------------------------------------------------- validation
    def add_validator(self, scope: str, validator: Validator) -> None:
        self._validators.setdefault(scope, []).append(validator)

    def _validate(self, scope: str, key: str, value: Any) -> None:
        for validator in self._validators.get(scope, []):
            try:
                validator(key, value)
            except Exception as exc:  # noqa: BLE001
                raise ValidationError(
                    f"State validation failed for {scope}.{key}: {exc}"
                ) from exc

    # --------------------------------------------------------------- versioning
    def _record(self, scope: str) -> None:
        self._counter += 1
        self._versions.append(
            StateVersion(self._counter, scope, copy.deepcopy(self._scopes[scope]))
        )
        if len(self._versions) > 500:
            self._versions = self._versions[-500:]

    @property
    def version(self) -> int:
        return self._counter

    def history(self, scope: Optional[str] = None) -> List[StateVersion]:
        with self._lock:
            if scope is None:
                return list(self._versions)
            return [v for v in self._versions if v.scope == scope]

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._scopes)

    def restore(self, snapshot: Dict[str, Dict[str, Any]]) -> None:
        with self._lock:
            self._scopes = copy.deepcopy(snapshot)
            for scope in self._scopes:
                self._record(scope)

    def rollback(self, version: int) -> bool:
        with self._lock:
            for entry in reversed(self._versions):
                if entry.version == version:
                    self._scopes[entry.scope] = copy.deepcopy(entry.snapshot)
                    self._record(entry.scope)
                    return True
        return False

    # -------------------------------------------------------------- persistence
    def _persist(self, scope: str) -> None:
        if self._backend is not None:
            self._backend.set(self._ns, scope, self._scopes.get(scope, {}))

    def load(self) -> None:
        if self._backend is None:
            return
        with self._lock:
            for scope in self._backend.keys(self._ns):
                self._scopes[scope] = self._backend.get(self._ns, scope, {})
