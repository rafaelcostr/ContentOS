"""Plugin manifest domain model."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    hooks: list[str] = field(default_factory=list)
    entrypoint: str = ""
    platform: str = ""
    author: str = "ContentOS"
    builtin: bool = False
    category: str = "publish"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginManifest":
        return cls(
            name=str(data["name"]),
            version=str(data.get("version", "1.0.0")),
            description=str(data.get("description", "")),
            hooks=list(data.get("hooks") or []),
            entrypoint=str(data.get("entrypoint", "")),
            platform=str(data.get("platform") or data.get("name", "")),
            author=str(data.get("author", "ContentOS")),
            builtin=bool(data.get("builtin", False)),
            category=str(data.get("category", "publish")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "hooks": self.hooks,
            "entrypoint": self.entrypoint,
            "platform": self.platform,
            "author": self.author,
            "builtin": self.builtin,
            "category": self.category,
        }
