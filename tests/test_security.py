"""Regression tests for the security fixes. These fail on the pre-fix code."""
import json
import os
import urllib.error
import urllib.request

import pytest

from aiforge.agents.agent import AgentConfig
from aiforge.core.errors import ValidationError
from aiforge.core.safe_eval import safe_eval
from aiforge.core.security import Permissions
from aiforge.tools.builtin.calculator import calculator
from aiforge.tools.builtin.web import HttpRequestTool
from aiforge.tools.context import ToolContext
from aiforge.workflows.builder import WorkflowBuilder
from aiforge.workflows.steps import ConditionalStep, ToolStep


# --------------------------------------------------------------- safe_eval / RCE
def test_safe_eval_allows_conditions():
    assert safe_eval("n > 5", {"n": 10}) is True
    assert safe_eval("a and b == 'ok'", {"a": True, "b": "ok"}) is True
    assert safe_eval("x in items", {"x": 2, "items": [1, 2, 3]}) is True


@pytest.mark.parametrize(
    "expr",
    [
        "__import__('os').system('echo hi')",
        "().__class__.__bases__",
        "open('pwned', 'w')",
        "[c for c in (1, 2)]",
    ],
)
def test_safe_eval_blocks_code(expr):
    with pytest.raises(ValidationError):
        safe_eval(expr, {})


def test_workflow_condition_cannot_execute(engine, tmp_path):
    marker = tmp_path / "pwned.txt"
    # A condition that tries to call open() must NOT create a file.
    wf = (
        WorkflowBuilder("rce")
        .set({"n": 1})
        .condition(
            f"open({str(marker)!r}, 'w')",
            ToolStep("calculator", {"expression": "1"}, name="t"),
            name="branch",
        )
        .build()
    )
    with pytest.raises(Exception):
        engine.run_workflow(wf)
    assert not marker.exists()


# --------------------------------------------------------------- SSRF
def _http(engine):
    tool = HttpRequestTool()
    ctx = ToolContext(config=engine.config, permissions=Permissions(allow_all=True))
    return tool, ctx


def test_http_blocks_file_scheme(engine):
    tool, ctx = _http(engine)
    result = tool.run(url="file:///etc/passwd", context=ctx)
    assert not result.ok and "http(s)" in (result.error or "")


def test_http_blocks_loopback(engine):
    tool, ctx = _http(engine)
    result = tool.run(url="http://127.0.0.1:80/", context=ctx)
    assert not result.ok and "internal" in (result.error or "").lower()


def test_http_blocks_cloud_metadata(engine):
    tool, ctx = _http(engine)
    result = tool.run(url="http://169.254.169.254/latest/meta-data/", context=ctx)
    assert not result.ok


# --------------------------------------------------------------- sandbox symlink
def test_sandbox_blocks_symlink_escape(engine, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("top secret", encoding="utf-8")
    link = os.path.join(engine.sandbox.root, "escape")
    try:
        os.symlink(str(secret), link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted on this host")
    result = engine.call_tool("read_file", {"path": "escape"})
    assert not result.ok  # realpath resolves the link and rejects the escape


# --------------------------------------------------------------- calculator DoS
def test_calculator_rejects_huge_exponent():
    result = calculator.run(expression="9**9**9")
    assert not result.ok
    assert calculator.run(expression="2 ** 10").output == 1024


# --------------------------------------------------------------- permissions
def test_agent_permissions_deny_by_default(engine):
    agent = engine.create_agent(AgentConfig(name="p", tools=["read_file"]))
    assert agent.permissions.has("fs") is False  # assistant role grants nothing
    assert Permissions.from_list(None).has("fs") is False
    assert Permissions.from_list(["*"]).has("anything") is True


# --------------------------------------------------------------- API status codes + CORS
def test_api_client_errors_and_cors(engine):
    from aiforge.api.server import serve_in_thread

    server = serve_in_thread(engine, port=8797)
    base = "http://127.0.0.1:8797"
    try:
        # unknown tool -> 400, not 500
        req = urllib.request.Request(
            base + "/api/tools/nope/run",
            data=json.dumps({"arguments": {}}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            assert False, "expected an error"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        # malformed JSON body -> 400
        req = urllib.request.Request(
            base + "/api/memory",
            data=b"{not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            assert False
        except urllib.error.HTTPError as exc:
            assert exc.code == 400

        # cross-origin request gets NO wildcard ACAO header
        req = urllib.request.Request(base + "/api/health", headers={"Origin": "http://evil.example"})
        resp = urllib.request.urlopen(req)
        assert resp.headers.get("Access-Control-Allow-Origin") is None
    finally:
        server.shutdown()
