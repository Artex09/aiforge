"""Security services: secrets, permissions, execution limits, and sandboxing.

Covers the catalog's Security surface: Secrets Management, Permission System,
Tool Isolation (sandbox root), Execution Limits, and the hooks used by the API
layer for Authentication/Authorization.
"""
from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .errors import AuthError, ExecutionLimitError


class SecretsManager:
    """Resolve secrets from an in-memory vault or environment variables, with
    redaction helpers so secrets never leak into logs or events."""

    def __init__(self, env_prefix: str = ""):
        self._vault: Dict[str, str] = {}
        self._env_prefix = env_prefix
        self._lock = threading.RLock()

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._vault[key] = value

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._lock:
            if key in self._vault:
                return self._vault[key]
        return os.environ.get(self._env_prefix + key, os.environ.get(key, default))

    def unset(self, key: str) -> None:
        """Remove a secret from the in-memory vault (environment is untouched)."""
        with self._lock:
            self._vault.pop(key, None)

    def require(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise AuthError(f"Required secret '{key}' is not set")
        return value

    def redact(self, text: str) -> str:
        redacted = text
        with self._lock:
            secrets = list(self._vault.values())
        for secret in secrets:
            if secret:
                redacted = redacted.replace(secret, "***")
        # also redact common token patterns
        redacted = re.sub(r"(sk-|key-|token-)[A-Za-z0-9_\-]{8,}", r"\1***", redacted)
        return redacted


@dataclass
class Permissions:
    """A grant set. ``allow_all`` short-circuits every check."""

    grants: Set[str] = field(default_factory=set)
    allow_all: bool = False

    def has(self, permission: str) -> bool:
        return self.allow_all or permission in self.grants

    def grant(self, permission: str) -> None:
        self.grants.add(permission)

    def revoke(self, permission: str) -> None:
        self.grants.discard(permission)

    @classmethod
    def from_list(cls, items: Optional[List[str]]) -> "Permissions":
        # Deny by default: ``None`` grants nothing (the agent's role may add
        # defaults on top). Pass ``["*"]`` to explicitly grant everything.
        if items is None:
            return cls()
        if "*" in items:
            return cls(allow_all=True)
        return cls(grants=set(items))


@dataclass
class ExecutionLimits:
    """Bounds enforced during a run to prevent runaway executions."""

    max_steps: int = 12
    max_tokens: int = 100_000
    max_tool_calls: int = 50
    timeout_seconds: float = 300.0

    def check_steps(self, count: int) -> None:
        if count > self.max_steps:
            raise ExecutionLimitError(
                f"Step limit exceeded ({count} > {self.max_steps})"
            )

    def check_tokens(self, total: int) -> None:
        if total > self.max_tokens:
            raise ExecutionLimitError(
                f"Token limit exceeded ({total} > {self.max_tokens})"
            )

    def check_tool_calls(self, count: int) -> None:
        if count > self.max_tool_calls:
            raise ExecutionLimitError(
                f"Tool-call limit exceeded ({count} > {self.max_tool_calls})"
            )


class Sandbox:
    """Resolves the filesystem root that sandboxed tools are confined to."""

    def __init__(self, root: str = ".aiforge/sandbox"):
        os.makedirs(os.path.abspath(root), exist_ok=True)
        # realpath so the stored root and every resolved path have symlinks
        # collapsed — escape checks then compare true on-disk locations.
        self.root = os.path.realpath(root)

    def resolve(self, path: str) -> str:
        target = os.path.realpath(os.path.join(self.root, path))
        if not (target == self.root or target.startswith(self.root + os.sep)):
            raise AuthError(f"Path '{path}' escapes the sandbox")
        return target


class TokenAuthenticator:
    """Minimal bearer-token authenticator used by the REST API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def authenticate(self, provided: Optional[str]) -> bool:
        if not self.enabled:
            return True  # auth disabled -> open
        if provided and provided.startswith("Bearer "):
            provided = provided[len("Bearer ") :]
        return provided == self.token
