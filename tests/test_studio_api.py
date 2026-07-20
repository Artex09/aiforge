"""The Studio's operational surface must be real, not decorative: provider
connections, run history (Traces), saved crews (Automations), and workspace
config all round-trip through the REST API."""
import json
import urllib.error
import urllib.request

from aiforge.api.server import serve_in_thread


def _get(base, path):
    return json.loads(urllib.request.urlopen(base + path).read())


def _send(base, path, body, method="POST"):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    return json.loads(urllib.request.urlopen(req).read())


def test_provider_info_names_the_default(engine):
    info = engine.provider_info()
    assert info["default"] == "mock"
    assert any(d["name"] == "mock" and d["default"] for d in info["detail"])


def test_connect_provider_registers_and_sets_default(engine):
    info = engine.connect_provider(
        "anthropic", api_key="test-key-123", model="claude-fable-5", make_default=True
    )
    assert "anthropic" in info["providers"]
    assert info["default"] == "anthropic"
    # The key lives in the vault, never in the response payload.
    assert "test-key-123" not in json.dumps(info)
    assert engine.secrets.get("ANTHROPIC_API_KEY") == "test-key-123"


def test_connect_provider_rejects_unknown_and_keyless(engine):
    import pytest

    with pytest.raises(ValueError):
        engine.connect_provider("closedai", api_key="x")
    with pytest.raises(ValueError):
        engine.connect_provider("openai", api_key="   ")


def test_disconnect_provider_drops_registration_and_vault_key(engine):
    engine.connect_provider("openai", api_key="sk-test", make_default=False)
    info = engine.disconnect_provider("openai")
    assert "openai" not in info["providers"]
    assert engine.secrets.get("OPENAI_API_KEY") in (None, "")
    import pytest

    with pytest.raises(ValueError):
        engine.disconnect_provider("mock")


def test_run_history_is_recorded_and_served(engine):
    from aiforge.agents.planner import plan_crew

    plan = plan_crew("Build a backend with Rust language")
    result = engine.run_graph(plan["graph"])
    assert result["success"] is True

    server = serve_in_thread(engine, port=8917)
    try:
        runs = _get("http://127.0.0.1:8917", "/api/runs")["runs"]
        assert len(runs) >= 1
        latest = runs[0]
        assert latest["success"] is True
        assert len(latest["tasks"]) == 3
        assert latest["tokens"] > 0
    finally:
        server.shutdown()


def test_saved_crews_round_trip_over_http(engine):
    server = serve_in_thread(engine, port=8918)
    base = "http://127.0.0.1:8918"
    graph = {
        "process": "sequential",
        "nodes": [
            {"id": "agent-1", "type": "agent", "data": {"name": "Dev"}},
            {"id": "task-1", "type": "task", "data": {"label": "Ship it", "agent": "Dev"}},
        ],
        "edges": [],
    }
    try:
        saved = _send(base, "/api/crews", {"name": "my crew", "graph": graph})
        assert saved["crews"][0]["name"] == "my crew"
        assert saved["crews"][0]["agents"] == 1
        assert saved["crews"][0]["tasks"] == 1

        listed = _get(base, "/api/crews")["crews"]
        assert listed[0]["graph"]["nodes"][0]["id"] == "agent-1"

        after = _send(base, "/api/crews/my%20crew", None, method="DELETE")
        assert after["crews"] == []
    finally:
        server.shutdown()


def test_save_crew_validates_input(engine):
    server = serve_in_thread(engine, port=8919)
    base = "http://127.0.0.1:8919"
    try:
        try:
            _send(base, "/api/crews", {"name": "", "graph": {"nodes": [1]}})
            assert False, "expected a 400"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
        try:
            _send(base, "/api/crews", {"name": "x", "graph": {"nodes": []}})
            assert False, "expected a 400"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
    finally:
        server.shutdown()


def test_config_endpoint_redacts_auth_token(engine):
    engine.config.set("api.auth_token", "super-secret")
    server = serve_in_thread(engine, port=8921)
    try:
        cfg = _get("http://127.0.0.1:8921", "/api/config")["config"]
        assert "auth_token" not in cfg.get("api", {})
        assert "super-secret" not in json.dumps(cfg)
        assert cfg["provider"]["default"] == "mock"
    finally:
        server.shutdown()


def test_templates_expose_full_agent_detail(engine):
    server = serve_in_thread(engine, port=8922)
    try:
        data = _get("http://127.0.0.1:8922", "/api/templates")
        assert "research_assistant" in data["templates"]
        detail = {a["name"]: a for a in data["agents"]}
        assert detail["coding_agent"]["role"] == "coder"
        assert "write_file" in detail["coding_agent"]["tools"]
    finally:
        server.shutdown()
