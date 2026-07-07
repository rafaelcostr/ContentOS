"""SEO metadata package — V5.2.3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformSeo:
    platform: str
    title: str
    description: str
    hashtags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "hashtags": list(self.hashtags),
        }


@dataclass
class SeoPackage:
    title: str
    description: str
    hashtags: list[str]
    keywords: list[str]
    title_variants: list[str]
    platforms: list[PlatformSeo]
    seo_score: float
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "hashtags": list(self.hashtags),
            "keywords": list(self.keywords),
            "title_variants": list(self.title_variants),
            "platforms": {p.platform: p.to_dict() for p in self.platforms},
            "seo_score": round(self.seo_score, 2),
            "recommendations": list(self.recommendations),
        }
