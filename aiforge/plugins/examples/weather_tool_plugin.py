"""Example tool plugin — registers a fake 'weather' tool.

Drop a file like this in a plugins directory and load it with
``engine.plugins.load_from_directory(path)``. The module exposes ``PLUGIN``.
"""
from __future__ import annotations

from aiforge.core.engine import Engine
from aiforge.plugins.base import PluginInfo, PluginKind, ToolPlugin
from aiforge.tools.base import ToolResult, tool


@tool(name="weather", description="Return a (fake) weather report for a city.")
def weather(city: str) -> ToolResult:
    # A real plugin would call a weather API here (declaring the 'network' perm).
    return ToolResult.success({"city": city, "temp_c": 21, "conditions": "Clear"})


class WeatherPlugin(ToolPlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="weather",
            kind=PluginKind.TOOL,
            version="0.1.0",
            description="Adds a demo weather tool.",
        )

    def register(self, engine: Engine) -> None:
        engine.tools.register(weather)


PLUGIN = WeatherPlugin()
