"""Network tools (stdlib urllib) plus an offline web-search stub.

``http_request`` honours an optional network allowlist provided via the tool
context and declares the ``network`` permission. ``web_search`` returns
deterministic offline placeholder results so examples run without connectivity;
swap in a real search plugin when needed.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional

from ..base import Tool, ToolResult, tool
from ..context import ToolContext


def _screen_url(url: str, allowlist: List[str]) -> Optional[str]:
    """Return an error string if *url* is unsafe to fetch, else None.

    Blocks non-HTTP(S) schemes (so ``file://``, ``ftp://``, ``gopher://`` cannot
    read local files) and — unless the host is explicitly allow-listed — any host
    that resolves to a private, loopback, link-local, reserved, or multicast
    address (blocking SSRF to ``127.0.0.1`` and cloud metadata at
    ``169.254.169.254``).
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Only http(s) URLs are allowed (got '{parsed.scheme or 'none'}')"
    host = parsed.hostname
    if not host:
        return "URL has no host"
    if host in allowlist:
        return None  # explicit opt-in overrides the internal-address block
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        return f"Cannot resolve host '{host}'"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return f"Host '{host}' resolves to a blocked internal address ({ip})"
    return None


class HttpRequestTool(Tool):
    name = "http_request"
    description = "Perform an HTTP(S) request and return status, headers and body."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "default": "GET"},
            "body": {"type": "string", "default": ""},
            "headers": {"type": "object"},
        },
        "required": ["url"],
    }
    permissions = ["network"]
    wants_context = True

    def run(
        self,
        url: str,
        method: str = "GET",
        body: str = "",
        headers: Optional[dict] = None,
        context: Optional[ToolContext] = None,
    ) -> ToolResult:
        allowlist = []
        if context and context.config is not None:
            allowlist = context.config.get("security.network_allowlist", []) or []
        problem = _screen_url(url, allowlist)
        if problem:
            return ToolResult.failure(problem)

        req = urllib.request.Request(
            url,
            data=body.encode("utf-8") if body else None,
            method=method.upper(),
            headers=headers or {},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 - allowlisted
                text = resp.read().decode("utf-8", errors="replace")
                return ToolResult.success(
                    {"status": resp.status, "headers": dict(resp.headers), "body": text[:20000]}
                )
        except urllib.error.HTTPError as exc:
            return ToolResult.failure(f"HTTP {exc.code}: {exc.reason}", status=exc.code)
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(str(exc))


@tool(
    name="web_search",
    description="Search the web for a query (offline placeholder results).",
)
def web_search(query: str, max_results: int = 3) -> ToolResult:
    results = [
        {
            "title": f"Result {i + 1} for '{query}'",
            "url": f"https://example.invalid/search?q={urllib.parse.quote(query)}&r={i}",
            "snippet": f"Offline placeholder snippet #{i + 1} about {query}.",
        }
        for i in range(max(1, min(max_results, 10)))
    ]
    return ToolResult.success(results)


http_request = HttpRequestTool()
