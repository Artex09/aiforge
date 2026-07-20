# Plugins

Plugins extend AIForge by registering agents, tools, memory stores, providers,
workflows, storage backends, or dashboard panels.

## Writing a plugin

```python
from aiforge.plugins.base import ToolPlugin, PluginInfo, PluginKind
from aiforge.tools.base import tool, ToolResult

@tool(name="weather", description="Return a weather report for a city.")
def weather(city: str) -> ToolResult:
    return ToolResult.success({"city": city, "temp_c": 21})

class WeatherPlugin(ToolPlugin):
    @property
    def info(self):
        return PluginInfo(name="weather", kind=PluginKind.TOOL, version="0.1.0")

    def register(self, engine):
        engine.tools.register(weather)

PLUGIN = WeatherPlugin()   # module-level `PLUGIN` (or `PLUGINS` list)
```

## Loading plugins

```python
engine.plugins.register(WeatherPlugin())          # direct
engine.plugins.load_from_directory("./plugins")   # scan *.py for PLUGIN/PLUGINS
engine.plugins.load_from_module("my_pkg.plugins")  # import a module
```

A working example ships at
`aiforge/plugins/examples/weather_tool_plugin.py`.

## Plugin kinds

`ToolPlugin`, `AgentPlugin`, `MemoryPlugin`, `LLMPlugin`, `WorkflowPlugin`,
`StoragePlugin`, `DashboardPlugin`. `DashboardPlugin.panels()` returns descriptors
surfaced by the dashboard (`GET /api/plugins`).

## Contract

Each plugin exposes an `info` property (`PluginInfo`) and a `register(engine)`
hook invoked at load time. `unregister(engine)` is optional (best-effort). A
failing `register` raises `PluginError` and the plugin is not added.
