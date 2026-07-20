import json
import os
import urllib.request

from aiforge.plugins.base import PluginInfo, PluginKind, ToolPlugin


class _DemoPlugin(ToolPlugin):
    @property
    def info(self):
        return PluginInfo(name="demo", kind=PluginKind.TOOL, description="demo")

    def register(self, engine):
        from aiforge.tools.base import tool, ToolResult

        @tool(name="echo_demo", description="echo")
        def echo_demo(text: str) -> ToolResult:
            return ToolResult.success(text)

        engine.tools.register(echo_demo)


def test_plugin_registration(engine):
    engine.plugins.register(_DemoPlugin())
    assert engine.tools.has("echo_demo")
    assert any(p.name == "demo" for p in engine.plugins.list())


def test_plugin_directory_load(engine):
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "aiforge", "plugins", "examples",
    )
    loaded = engine.plugins.load_from_directory(path)
    assert "weather" in loaded
    assert engine.tools.has("weather")


def test_api_endpoints(engine):
    from aiforge.api.server import serve_in_thread

    server = serve_in_thread(engine, port=8799)
    try:
        base = "http://127.0.0.1:8799"
        health = json.loads(urllib.request.urlopen(base + "/api/health").read())
        assert health["status"] == "ok"

        # create + run an agent over HTTP
        req = urllib.request.Request(
            base + "/api/agents",
            data=json.dumps({"template": "research_assistant"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        created = json.loads(urllib.request.urlopen(req).read())
        assert "created" in created

        run = urllib.request.Request(
            base + f"/api/agents/{created['created']}/run",
            data=json.dumps({"input": "hello"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        result = json.loads(urllib.request.urlopen(run).read())
        assert result["success"] is True
    finally:
        server.shutdown()
