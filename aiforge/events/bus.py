"""Event bus — the backbone of AIForge's event-driven architecture.

Every subsystem publishes lifecycle events here. Monitoring, plugins, the
dashboard, and user code subscribe. Handlers may be plain callables or
coroutine functions; the bus dispatches both. A bounded ring buffer keeps the
most recent events for the monitoring/inspection surfaces.
"""
from __future__ import annotations

import threading
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

from ..core.types import new_id


class EventType(str, Enum):
    """Canonical event categories emitted across the framework."""

    # Execution lifecycle
    EXECUTION_START = "execution.start"
    EXECUTION_END = "execution.end"
    EXECUTION_ERROR = "execution.error"

    # Agent lifecycle
    AGENT_CREATED = "agent.created"
    AGENT_START = "agent.start"
    AGENT_STEP = "agent.step"
    AGENT_MESSAGE = "agent.message"
    AGENT_END = "agent.end"
    AGENT_ERROR = "agent.error"

    # Workflow lifecycle
    WORKFLOW_START = "workflow.start"
    WORKFLOW_STEP_START = "workflow.step.start"
    WORKFLOW_STEP_END = "workflow.step.end"
    WORKFLOW_END = "workflow.end"
    WORKFLOW_ERROR = "workflow.error"

    # Tool lifecycle
    TOOL_START = "tool.start"
    TOOL_END = "tool.end"
    TOOL_ERROR = "tool.error"

    # Memory lifecycle
    MEMORY_WRITE = "memory.write"
    MEMORY_READ = "memory.read"
    MEMORY_COMPRESS = "memory.compress"

    # LLM lifecycle
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    LLM_STREAM = "llm.stream"

    # Generic error + custom
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class Event:
    """A single event flowing through the bus."""

    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    name: Optional[str] = None
    id: str = field(default_factory=lambda: new_id("evt"))
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name or self.type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


Handler = Callable[[Event], Any]

WILDCARD = "*"


class EventBus:
    """Thread-safe publish/subscribe hub with lifecycle hooks."""

    def __init__(self, history_size: int = 1000):
        self._subscribers: Dict[str, List[Handler]] = {}
        self._before_hooks: List[Handler] = []
        self._after_hooks: List[Handler] = []
        self._history: Deque[Event] = deque(maxlen=history_size)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ subscribe
    def subscribe(self, event_type: Any, handler: Handler) -> Callable[[], None]:
        """Register *handler* for *event_type* (an :class:`EventType`, its string
        value, or ``"*"`` for all events). Returns an unsubscribe function."""
        key = self._key(event_type)
        with self._lock:
            self._subscribers.setdefault(key, []).append(handler)

        def _unsubscribe() -> None:
            with self._lock:
                if handler in self._subscribers.get(key, []):
                    self._subscribers[key].remove(handler)

        return _unsubscribe

    def on(self, event_type: Any) -> Callable[[Handler], Handler]:
        """Decorator form of :meth:`subscribe`."""

        def _decorator(handler: Handler) -> Handler:
            self.subscribe(event_type, handler)
            return handler

        return _decorator

    def add_hook(self, when: str, handler: Handler) -> None:
        """Add a global lifecycle hook. ``when`` is ``"before"`` or ``"after"``."""
        with self._lock:
            if when == "before":
                self._before_hooks.append(handler)
            elif when == "after":
                self._after_hooks.append(handler)
            else:
                raise ValueError("hook 'when' must be 'before' or 'after'")

    # ------------------------------------------------------------------ publish
    def emit(
        self,
        event_type: Any,
        data: Optional[Dict[str, Any]] = None,
        *,
        source: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Event:
        """Build and dispatch an event to all matching subscribers."""
        etype = event_type if isinstance(event_type, EventType) else EventType(str(event_type))
        event = Event(type=etype, data=data or {}, source=source, name=name)
        self.publish(event)
        return event

    def publish(self, event: Event) -> None:
        """Dispatch a pre-built :class:`Event`."""
        with self._lock:
            self._history.append(event)
            handlers = list(self._subscribers.get(self._key(event.type), []))
            handlers += list(self._subscribers.get(WILDCARD, []))
            before = list(self._before_hooks)
            after = list(self._after_hooks)

        for hook in before:
            self._invoke(hook, event)
        for handler in handlers:
            self._invoke(handler, event)
        for hook in after:
            self._invoke(hook, event)

    # ------------------------------------------------------------------ history
    def history(self, event_type: Any = None, limit: int = 100) -> List[Event]:
        with self._lock:
            events = list(self._history)
        if event_type is not None:
            key = self._key(event_type)
            events = [e for e in events if e.type.value == key]
        return events[-limit:]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # ------------------------------------------------------------------ internals
    @staticmethod
    def _key(event_type: Any) -> str:
        if event_type == WILDCARD:
            return WILDCARD
        if isinstance(event_type, EventType):
            return event_type.value
        return str(event_type)

    def _invoke(self, handler: Handler, event: Event) -> None:
        try:
            result = handler(event)
            # Support coroutine handlers without forcing an event loop everywhere.
            if hasattr(result, "__await__"):
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(result)  # type: ignore[arg-type]
                    else:
                        loop.run_until_complete(result)  # type: ignore[arg-type]
                except RuntimeError:
                    asyncio.run(result)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 - handlers must never break the emitter
            # A failing subscriber should not take down the whole pipeline.
            traceback.print_exc()
