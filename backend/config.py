"""Central configuration. Phase 1: extract config layer (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    github_token: str = ""
    gemini_model: str = "gemini-1.5-flash"
    max_rounds: int = 2
    request_timeout_s: int = 30
    max_diff_chars: int = 80000
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./polymind.db"
    redis_url: str = ""
    log_level: str = "INFO"
    env: str = "dev"
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    rate_limit_per_hour: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_llm_key(self) -> bool:
        return bool(self.gemini_api_key and "here" not in self.gemini_api_key.lower()
                    and len(self.gemini_api_key) > 8)


@lru_cache
def get_settings() -> Settings:
    return Settings()
