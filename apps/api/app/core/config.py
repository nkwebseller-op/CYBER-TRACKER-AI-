"""Centralized, validated application settings.

All configuration is read from the environment (optionally via a local
.env file for development). Nothing here hardcodes a secret, a path, or a
provider implementation — see services/agent for why AI provider selection
is a string switch, not an import.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_secret_key: str = Field(default="dev-only-insecure-key-change-me")
    api_cors_origins: str = Field(default="http://localhost:3000")

    database_url: str = Field(
        default="postgresql+asyncpg://cyberai:cyberai@localhost:5432/cyberai"
    )

    ai_provider: str = Field(default="gemini")
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
