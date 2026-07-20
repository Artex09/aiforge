"""Layered configuration for AIForge.

Resolution order (lowest to highest precedence):

1. Built-in defaults
2. Configuration file (JSON always; YAML if PyYAML is importable)
3. Environment variables prefixed with ``AIFORGE_`` (double underscore = nesting,
   e.g. ``AIFORGE_PROVIDER__MODEL`` -> ``provider.model``)
4. Runtime overrides passed in code

Nested keys are addressed with dotted paths: ``config.get("memory.vector.dimension")``.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..core.errors import ConfigError

ENV_PREFIX = "AIFORGE_"

DEFAULTS: Dict[str, Any] = {
    "provider": {
        "default": "mock",
        "model": "aiforge-mock-1",
        "temperature": 0.7,
        "max_tokens": 1024,
        "fallbacks": [],
        "retries": 2,
        "retry_base_delay": 0.5,
    },
    "embeddings": {
        "provider": "mock",
        "model": "aiforge-embed-1",
        "dimension": 256,
    },
    "memory": {
        "short_term_capacity": 20,
        "vector": {"dimension": 256, "top_k": 5},
        "compression": {"enabled": True, "threshold": 40},
    },
    "workflow": {
        "default_timeout": 120,
        "default_retries": 0,
        "max_parallel": 8,
    },
    "storage": {
        "backend": "local",
        "path": ".aiforge",
        "cache_ttl": 300,
    },
    "security": {
        "sandbox_root": ".aiforge/sandbox",
        "allow_shell": False,
        "network_allowlist": [],
        "max_steps": 12,
        "max_tokens": 100000,
        "max_tool_calls": 50,
    },
    "api": {
        "host": "127.0.0.1",
        "port": 8787,
        "auth_token": None,
        # Cross-origin requests are refused unless the Origin is listed here.
        # The Studio is same-origin, so this stays empty by default.
        "cors_origins": [],
    },
    "logging": {"level": "INFO"},
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _coerce(value: str) -> Any:
    """Best-effort coercion of environment string values to native types."""
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", ""}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


class Config:
    """A merged, dotted-path configuration object."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = _deep_merge(DEFAULTS, data or {})

    # ------------------------------------------------------------------ loaders
    @classmethod
    def load(
        cls,
        path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        use_env: bool = True,
    ) -> "Config":
        data: Dict[str, Any] = {}
        if path:
            data = _deep_merge(data, cls._load_file(path))
        if use_env:
            data = _deep_merge(data, cls._load_env())
        if overrides:
            data = _deep_merge(data, overrides)
        return cls(data)

    @staticmethod
    def _load_file(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise ConfigError(f"Config file not found: {path}")
        text = open(path, "r", encoding="utf-8").read()
        if path.endswith((".yaml", ".yml")):
            try:
                import yaml  # type: ignore

                return yaml.safe_load(text) or {}
            except ImportError as exc:  # pragma: no cover - optional dep
                raise ConfigError(
                    "YAML config requires PyYAML; install it or use JSON."
                ) from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON config: {exc}") from exc

    @staticmethod
    def _load_env() -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for key, value in os.environ.items():
            if not key.startswith(ENV_PREFIX):
                continue
            path = key[len(ENV_PREFIX) :].lower().split("__")
            cursor = data
            for part in path[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[path[-1]] = _coerce(value)
        return data

    # ------------------------------------------------------------------ access
    def get(self, dotted_key: str, default: Any = None) -> Any:
        cursor: Any = self._data
        for part in dotted_key.split("."):
            if isinstance(cursor, dict) and part in cursor:
                cursor = cursor[part]
            else:
                return default
        return cursor

    def set(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        cursor = self._data
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value

    def section(self, name: str) -> Dict[str, Any]:
        value = self.get(name, {})
        return dict(value) if isinstance(value, dict) else {}

    def as_dict(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._data))  # deep copy, JSON-safe

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Config({list(self._data.keys())})"
