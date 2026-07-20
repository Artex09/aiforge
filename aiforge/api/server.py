"""REST API + dashboard host, built on the Python standard library only.

No external web framework is used (keeping the "no external frontend framework"
and minimal-dependency constraints). A small router dispatches JSON endpoints
under ``/api/*`` and serves the vanilla dashboard from ``dashboard/static``.
"""
from __future__ import annotations

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from ..agents.agent import AgentConfig
from ..core.engine import Engine
from ..core.errors import (
    AuthError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolValidationError,
    ValidationError,
)
from ..workflows.serialization import workflow_from_dict

# Ordinary client mistakes -> 400; permission/auth -> 403; everything else -> 500.
_CLIENT_ERRORS = (ToolValidationError, ToolNotFoundError, ValidationError, KeyError, ValueError)
_FORBIDDEN_ERRORS = (ToolPermissionError, AuthError)

Route = Tuple[str, "re.Pattern[str]", Callable[..., Any]]

_PKG_ROOT = os.path.dirname(os.path.dirname(__file__))
_FRONTEND_DIST = os.path.join(_PKG_ROOT, "frontend", "dist")
_LEGACY_STATIC = os.path.join(_PKG_ROOT, "dashboard", "static")


def _web_root() -> str:
    """Prefer the built React (Node) frontend; fall back to the legacy static UI."""
    if os.path.isfile(os.path.join(_FRONTEND_DIST, "index.html")):
        return _FRONTEND_DIST
    return _LEGACY_STATIC


DASHBOARD_DIR = _web_root()


class Router:
    def __init__(self) -> None:
        self.routes: List[Route] = []

    def add(self, method: str, pattern: str, handler: Callable[..., Any]) -> None:
        regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")
        self.routes.append((method.upper(), regex, handler))

    def match(self, method: str, path: str):
        for m, regex, handler in self.routes:
            if m != method.upper():
                continue
            found = regex.match(path)
            if found:
                return handler, found.groupdict()
        return None, None


def build_router(engine: Engine) -> Router:
    router = Router()

    router.add("GET", "/api/health", lambda **_: {"status": "ok"})
    router.add("GET", "/api/status", lambda **_: engine.status())
    router.add("GET", "/api/providers", lambda **_: {"providers": engine.providers.names()})

    # Tools
    router.add("GET", "/api/tools", lambda **_: {"tools": engine.tools.schemas()})
    router.add("GET", "/api/tools/catalog", lambda **_: engine.tool_catalog())

    def run_tool(name: str, body: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        result = engine.call_tool(name, body.get("arguments", {}))
        return result.to_dict()

    router.add("POST", "/api/tools/{name}/run", run_tool)

    # Agents
    router.add(
        "GET",
        "/api/agents",
        lambda **_: {"agents": [a.config.to_dict() for a in engine.agents.list()]},
    )

    def create_agent(body: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        if body.get("template"):
            agent = engine.agent_from_template(body["template"], **body.get("overrides", {}))
        else:
            agent = engine.create_agent(AgentConfig.from_dict(body))
        return {"created": agent.config.name}

    router.add("POST", "/api/agents", create_agent)

    def run_agent(name: str, body: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        result = engine.run_agent(name, body.get("input", ""))
        return result.to_dict()

    router.add("POST", "/api/agents/{name}/run", run_agent)

    # Memory
    def memory_search(query: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        q = (query.get("query", [""]) or [""])[0]
        hits = engine.memory.recall(q, top_k=int((query.get("top_k", ["5"]) or ["5"])[0]))
        return {"results": [r.to_dict() for r in hits]}

    router.add("GET", "/api/memory", memory_search)

    def memory_add(body: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        rid = engine.memory.remember(body.get("content", ""))
        return {"id": rid}

    router.add("POST", "/api/memory", memory_add)
    router.add("GET", "/api/memory/stats", lambda **_: engine.memory.stats())

    # Workflows
    def run_workflow(body: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        workflow = workflow_from_dict(body["workflow"])
        result = engine.run_workflow(workflow, body.get("inputs"))
        return result.to_dict()

    router.add("POST", "/api/workflows/run", run_workflow)

    # Crews / visual graph
    def run_crew(body: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        return engine.run_graph(body)

    router.add("POST", "/api/crew/run", run_crew)
    router.add("POST", "/api/graph/run", run_crew)
    router.add("POST", "/api/graph/code", lambda body, **_: {"code": engine.graph_to_code(body)})

    # Studio chat: turn a natural-language brief into a starter crew graph.
    def studio_chat(body: Dict[str, Any], **_: Any) -> Dict[str, Any]:
        return _studio_reply(engine, body.get("message", ""), body.get("graph"))

    router.add("POST", "/api/studio/chat", studio_chat)

    # Monitoring
    router.add("GET", "/api/metrics", lambda **_: engine.monitor.snapshot())
    router.add(
        "GET",
        "/api/timeline",
        lambda query=None, **_: {"timeline": engine.monitor.get_timeline(
            int(((query or {}).get("limit", ["100"]) or ["100"])[0])
        )},
    )
    router.add(
        "GET",
        "/api/events",
        lambda query=None, **_: {"events": [
            e.to_dict() for e in engine.events.history(
                limit=int(((query or {}).get("limit", ["100"]) or ["100"])[0])
            )
        ]},
    )
    router.add(
        "GET",
        "/api/executions",
        lambda **_: {"executions": engine.backend.query("executions", limit=100)},
    )
    router.add(
        "GET",
        "/api/logs",
        lambda **_: {"logs": engine.backend.query("events", limit=200)},
    )
    router.add("GET", "/api/plugins", lambda **_: {"plugins": [p.__dict__ for p in engine.plugins.list()]})
    router.add("GET", "/api/templates", lambda **_: _templates())

    return router


def _templates() -> Dict[str, Any]:
    from ..agents.templates import list_templates

    return {"templates": list_templates()}


def _studio_reply(engine: Engine, message: str, graph: Any) -> Dict[str, Any]:
    """Assistant response for the Studio Chat.

    Delegates to the intent-aware crew planner so a software brief yields an
    architect + engineers + QA (with executable tasks), a data brief yields a
    data crew, and so on — instead of a fixed researcher/writer pair.
    """
    from ..agents.planner import plan_crew

    if not (message or "").strip():
        return {
            "reply": "Tell me what you'd like to build — e.g. “build a backend "
                     "in Rust”, “analyse this sales dataset”, or "
                     "“write a launch blog post” — and I'll assemble the crew.",
            "steps": [],
            "graph": None,
            "process": "sequential",
        }
    plan = plan_crew(message)
    return {
        "reply": plan["reply"],
        "steps": plan["steps"],
        "graph": plan["graph"],
        "process": plan["process"],
    }


def _sse(obj: Dict[str, Any]) -> str:
    return "data: " + json.dumps(obj, default=str) + "\n\n"


def stream_run(engine: Engine, graph: Dict[str, Any]):
    """Run a crew graph and yield SSE lines for each live event, then the result.

    Subscribes to the engine's event bus for the duration of the run so the
    Studio can render a live trace (task/tool/LLM events) as it happens.
    """
    import queue
    import threading

    events_q: "queue.Queue" = queue.Queue()
    unsubscribe = engine.events.subscribe("*", lambda evt: events_q.put(evt.to_dict()))
    holder: Dict[str, Any] = {}

    def _run() -> None:
        try:
            holder["result"] = engine.run_graph(graph)
        except Exception as exc:  # noqa: BLE001
            holder["error"] = str(exc)
        finally:
            events_q.put({"__done__": True})

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    yield _sse({"type": "run.start"})
    while True:
        try:
            item = events_q.get(timeout=180)
        except queue.Empty:
            yield _sse({"type": "run.error", "error": "run timed out"})
            break
        if item.get("__done__"):
            break
        yield _sse({"type": "event", "event": item})
    unsubscribe()
    result = holder.get("result") or {"success": False, "error": holder.get("error", "unknown error")}
    yield _sse({"type": "run.end", "result": result})


def make_handler(engine: Engine, router: Router):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AIForge/0.1"

        def log_message(self, *args: Any) -> None:  # silence default logging
            pass

        # -------------------------------------------------------- auth + io
        def _authorized(self) -> bool:
            if not engine.auth.enabled:
                return True
            return engine.auth.authenticate(self.headers.get("Authorization"))

        def _cors_headers(self) -> None:
            # Same-origin needs no CORS. Only echo an Origin that the operator has
            # explicitly allow-listed — a wildcard would let any visited web page
            # drive the local engine.
            origin = self.headers.get("Origin")
            allowed = engine.config.get("api.cors_origins", []) or []
            if origin and origin in allowed:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def _send_json(self, data: Any, status: int = 200) -> None:
            payload = json.dumps(data, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_body(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if not length:
                return {}
            raw = self.rfile.read(length)
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError(f"Request body is not valid JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError("Request body must be a JSON object")
            return parsed

        # ------------------------------------------------------------ verbs
        def do_OPTIONS(self) -> None:  # noqa: N802
            self._send_json({}, 204)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._handle_api("GET", parsed)
            else:
                self._serve_static(parsed.path)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/runs/stream":
                self._handle_run_stream()
                return
            self._handle_api("POST", parsed)

        def _handle_run_stream(self) -> None:
            if not self._authorized():
                self._send_json({"error": "unauthorized"}, 401)
                return
            try:
                graph = self._read_body()
            except ValueError as exc:
                self._send_json({"error": "ValueError", "message": str(exc)}, 400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self._cors_headers()
            self.end_headers()
            try:
                for chunk in stream_run(engine, graph):
                    self.wfile.write(chunk.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # client closed the stream
            self.close_connection = True

        # --------------------------------------------------------- dispatch
        def _handle_api(self, method: str, parsed) -> None:
            if not self._authorized():
                self._send_json({"error": "unauthorized"}, 401)
                return
            handler, params = router.match(method, parsed.path)
            if handler is None:
                self._send_json({"error": "not found", "path": parsed.path}, 404)
                return
            try:
                kwargs: Dict[str, Any] = dict(params or {})
                if method == "POST":
                    kwargs["body"] = self._read_body()
                kwargs["query"] = parse_qs(parsed.query)
                result = handler(**kwargs)
                self._send_json(result)
            except _FORBIDDEN_ERRORS as exc:
                self._send_json({"error": type(exc).__name__, "message": str(exc)}, 403)
            except _CLIENT_ERRORS as exc:
                self._send_json({"error": type(exc).__name__, "message": str(exc)}, 400)
            except Exception as exc:  # noqa: BLE001 - genuine server fault
                self._send_json({"error": type(exc).__name__, "message": str(exc)}, 500)

        def _serve_static(self, path: str) -> None:
            root = os.path.abspath(_web_root())
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            if rel.startswith("static/"):  # legacy dashboard prefix
                rel = rel[len("static/") :]
            full = os.path.abspath(os.path.join(root, rel))

            # SPA fallback: unknown non-file routes serve index.html so client
            # routing works; only asset-looking paths 404.
            if not full.startswith(root) or not os.path.isfile(full):
                if os.path.splitext(rel)[1] in ("", ".html"):
                    full = os.path.join(root, "index.html")
                if not os.path.isfile(full):
                    self.send_error(404, "Not found")
                    return

            ctype = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css",
                ".js": "application/javascript",
                ".mjs": "application/javascript",
                ".json": "application/json",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".ico": "image/x-icon",
                ".woff": "font/woff",
                ".woff2": "font/woff2",
                ".map": "application/json",
            }.get(os.path.splitext(full)[1], "application/octet-stream")
            with open(full, "rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def create_server(engine: Engine, host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    router = build_router(engine)
    handler = make_handler(engine, router)
    return ThreadingHTTPServer((host, port), handler)


def serve(engine: Engine, host: Optional[str] = None, port: Optional[int] = None) -> None:
    host = host or engine.config.get("api.host", "127.0.0.1")
    port = port or engine.config.get("api.port", 8787)
    server = create_server(engine, host, port)
    using_studio = os.path.isfile(os.path.join(_FRONTEND_DIST, "index.html"))
    ui = "Studio (visual workflow builder)" if using_studio else "legacy dashboard"
    print(f"AIForge - {ui} + REST API at http://{host}:{port}")
    if not using_studio:
        print("  (build the Node UI with: cd aiforge/frontend && npm install && npm run build)")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down…")
    finally:
        server.shutdown()
        engine.shutdown()


def serve_in_thread(engine: Engine, host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    """Start the server on a background thread (used by tests)."""
    server = create_server(engine, host, port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
