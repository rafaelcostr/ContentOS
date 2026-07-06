"""AI Gateway configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "ContentOS AI Gateway"
    debug: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    host: str = os.getenv("AI_GATEWAY_HOST", "0.0.0.0")
    port: int = int(os.getenv("AI_GATEWAY_PORT", "8020"))


settings = Settings()
