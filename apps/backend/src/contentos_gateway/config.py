from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ContentOS"
    debug: bool = True
    database_url: str = "postgresql+asyncpg://contentos:contentos_secret@localhost:5432/contentos"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    workflow_engine_url: str = "http://workflow-engine:8001"
    cors_origins: str = "http://localhost:3000"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
                return True
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.debug:
            return self
        if not self.jwt_secret.strip() or self.jwt_secret.startswith("change-me") or len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be configured with at least 32 characters when DEBUG=false")
        if "*" in self.cors_origins_list:
            raise ValueError("CORS_ORIGINS cannot contain '*' when DEBUG=false and credentials are enabled")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
