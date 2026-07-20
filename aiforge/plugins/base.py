"""Plugin system.

A plugin is a small object that extends AIForge by registering agents, tools,
memory stores, providers, workflows, storage backends, or dashboard panels. Each
plugin declares a ``kind`` and a ``register(engine)`` hook invoked at load time.
"""
from __future__ import annotations

import abc
import importlib
import importlib.util
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..core.errors import PluginError

if TYPE_CHECKING:  # avoid import cycle at runtime
    from ..core.engine import Engine


class PluginKind(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    MEMORY = "memory"
    LLM = "llm"
    WORKFLOW = "workflow"
    STORAGE = "storage"
    DASHBOARD = "dashboard"


@dataclass
class PluginInfo:
    name: str
    kind: PluginKind
    version: str = "0.1.0"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class Plugin(abc.ABC):
    """Base class for all plugins."""

    kind: PluginKind = PluginKind.TOOL

    @property
    @abc.abstractmethod
    def info(self) -> PluginInfo: ...

    @abc.abstractmethod
    def register(self, engine: "Engine") -> None:
        """Wire this plugin's contributions into the engine."""

    def unregister(self, engine: "Engine") -> None:  # pragma: no cover - optional
        """Undo :meth:`register` (best effort)."""


# Convenience typed bases (purely for clarity/self-documentation).
class ToolPlugin(Plugin):
    kind = PluginKind.TOOL


class AgentPlugin(Plugin):
    kind = PluginKind.AGENT


class MemoryPlugin(Plugin):
    kind = PluginKind.MEMORY


class LLMPlugin(Plugin):
    kind = PluginKind.LLM


class WorkflowPlugin(Plugin):
    kind = PluginKind.WORKFLOW


class StoragePlugin(Plugin):
    kind = PluginKind.STORAGE


class DashboardPlugin(Plugin):
    kind = PluginKind.DASHBOARD

    def panels(self) -> List[Dict[str, Any]]:
        """Return dashboard panel descriptors to surface in the UI."""
        return []


class PluginManager:
    def __init__(self, engine: "Engine"):
        self.engine = engine
        self._plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> Plugin:
        info = plugin.info
        if info.name in self._plugins:
            raise PluginError(f"Plugin '{info.name}' already registered")
        try:
            plugin.register(self.engine)
        except Exception as exc:  # noqa: BLE001
            raise PluginError(f"Plugin '{info.name}' failed to register: {exc}") from exc
        self._plugins[info.name] = plugin
        return plugin

    def unregister(self, name: str) -> None:
        plugin = self._plugins.pop(name, None)
        if plugin is not None:
            try:
                plugin.unregister(self.engine)
            except Exception:  # noqa: BLE001
                pass

    def get(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def list(self) -> List[PluginInfo]:
        return [p.info for p in self._plugins.values()]

    def dashboard_panels(self) -> List[Dict[str, Any]]:
        panels: List[Dict[str, Any]] = []
        for plugin in self._plugins.values():
            if isinstance(plugin, DashboardPlugin):
                panels.extend(plugin.panels())
        return panels

    # ------------------------------------------------------------- discovery
    def load_from_directory(self, path: str) -> List[str]:
        """Import every ``*.py`` in *path* and register objects named ``PLUGIN``
        (a Plugin instance) or ``PLUGINS`` (an iterable of them)."""
        loaded: List[str] = []
        if not os.path.isdir(path):
            return loaded
        for filename in sorted(os.listdir(path)):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            module = self._import_file(os.path.join(path, filename))
            for candidate in self._extract(module):
                self.register(candidate)
                loaded.append(candidate.info.name)
        return loaded

    def load_from_module(self, module_path: str) -> List[str]:
        module = importlib.import_module(module_path)
        loaded: List[str] = []
        for candidate in self._extract(module):
            self.register(candidate)
            loaded.append(candidate.info.name)
        return loaded

    @staticmethod
    def _import_file(file_path: str):
        name = f"aiforge_plugin_{os.path.splitext(os.path.basename(file_path))[0]}"
        spec = importlib.util.spec_from_file_location(name, file_path)
        if spec is None or spec.loader is None:
            raise PluginError(f"Cannot load plugin file: {file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _extract(module) -> List[Plugin]:
        found: List[Plugin] = []
        if hasattr(module, "PLUGIN") and isinstance(module.PLUGIN, Plugin):
            found.append(module.PLUGIN)
        if hasattr(module, "PLUGINS"):
            found.extend(p for p in module.PLUGINS if isinstance(p, Plugin))
        return found
