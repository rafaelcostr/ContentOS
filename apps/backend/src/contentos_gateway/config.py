from functools import lru_cache

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
