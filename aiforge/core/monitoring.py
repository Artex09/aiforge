"""Monitoring: metrics collection and execution timeline.

The :class:`Monitor` subscribes to the event bus and aggregates token usage,
tool-call counts, errors, and per-execution timelines. It powers the dashboard,
the ``/metrics`` API endpoint, and the CLI ``monitor`` view.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..events.bus import Event, EventBus, EventType


class Monitor:
    def __init__(self, events: EventBus, backend: Any = None):
        self.events = events
        self.backend = backend
        self._lock = threading.RLock()
        self.metrics: Dict[str, float] = defaultdict(float)
        self.tool_usage: Dict[str, int] = defaultdict(int)
        self.errors: List[Dict[str, Any]] = []
        self.timeline: List[Dict[str, Any]] = []
        self._subscribe()

    def _subscribe(self) -> None:
        self.events.subscribe("*", self._on_event)

    def _on_event(self, event: Event) -> None:
        with self._lock:
            self.metrics[f"events.{event.type.value}"] += 1
            self.timeline.append(
                {
                    "id": event.id,
                    "type": event.type.value,
                    "source": event.source,
                    "timestamp": event.timestamp,
                    "data": _compact(event.data),
                }
            )
            if len(self.timeline) > 2000:
                self.timeline = self.timeline[-2000:]

            if event.type == EventType.TOOL_END:
                tool = event.data.get("tool", "unknown")
                self.tool_usage[tool] += 1
                self.metrics["tools.calls"] += 1
                self.metrics["tools.duration"] += float(event.data.get("duration", 0) or 0)
            elif event.type == EventType.LLM_RESPONSE:
                usage = event.data.get("usage", {}) or {}
                self.metrics["tokens.prompt"] += usage.get("prompt_tokens", 0)
                self.metrics["tokens.completion"] += usage.get("completion_tokens", 0)
                self.metrics["tokens.total"] += usage.get("total_tokens", 0)
                self.metrics["llm.calls"] += 1
                model = event.data.get("model")
                if model:
                    from .pricing import estimate_cost

                    self.metrics["cost.usd"] += estimate_cost(
                        model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
                    )
            elif event.type in (
                EventType.ERROR,
                EventType.AGENT_ERROR,
                EventType.WORKFLOW_ERROR,
                EventType.TOOL_ERROR,
                EventType.EXECUTION_ERROR,
            ):
                self.errors.append(
                    {
                        "type": event.type.value,
                        "source": event.source,
                        "error": event.data.get("error"),
                        "timestamp": event.timestamp,
                    }
                )
                self.metrics["errors.total"] += 1

        if self.backend is not None:
            try:
                self.backend.append("events", event.to_dict())
            except Exception:  # noqa: BLE001 - monitoring must never crash a run
                pass

    # ------------------------------------------------------------------ views
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "metrics": dict(self.metrics),
                "tool_usage": dict(self.tool_usage),
                "errors": list(self.errors[-50:]),
                "timeline_size": len(self.timeline),
            }

    def get_timeline(self, limit: int = 100, execution_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            items = self.timeline
            if execution_id:
                items = [
                    e for e in items if e.get("data", {}).get("execution_id") == execution_id
                ]
            return items[-limit:]

    def reset(self) -> None:
        with self._lock:
            self.metrics.clear()
            self.tool_usage.clear()
            self.errors.clear()
            self.timeline.clear()


def _compact(data: Dict[str, Any], limit: int = 300) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in data.items():
        text = value if isinstance(value, str) else repr(value)
        out[key] = text if len(text) <= limit else text[:limit] + "…"
    return out
