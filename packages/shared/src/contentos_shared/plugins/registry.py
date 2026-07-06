"""Plugin system — extensibility without modifying core.

Future plugins: TikTok, Instagram, YouTube, Telegram, Discord agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PluginMeta:
    name: str
    version: str
    description: str
    author: str = "ContentOS"
    hooks: list[str] = field(default_factory=list)


class ContentOSPlugin(ABC):
    """Base class for all ContentOS plugins."""

    @property
    @abstractmethod
    def meta(self) -> PluginMeta: ...

    @abstractmethod
    async def on_load(self) -> None:
        """Called when plugin is registered."""

    @abstractmethod
    async def on_unload(self) -> None:
        """Called when plugin is removed."""


class PluginRegistry:
    """Singleton registry — Factory pattern for plugins."""

    _instance: "PluginRegistry | None" = None

    def __init__(self) -> None:
        self._plugins: dict[str, ContentOSPlugin] = {}

    @classmethod
    def instance(cls) -> "PluginRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, plugin: ContentOSPlugin) -> None:
        self._plugins[plugin.meta.name] = plugin

    def get(self, name: str) -> ContentOSPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginMeta]:
        return [p.meta for p in self._plugins.values()]

    def hook(self, hook_name: str) -> list[ContentOSPlugin]:
        return [p for p in self._plugins.values() if hook_name in p.meta.hooks]

    async def load_all(self) -> None:
        for plugin in self._plugins.values():
            await plugin.on_load()
