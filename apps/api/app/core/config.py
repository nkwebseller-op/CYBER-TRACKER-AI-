"""Centralized, validated application settings.

All configuration is read from the environment (optionally via a local
.env file for development). Nothing here hardcodes a secret, a path, or a
provider implementation — see services/agent for why AI provider selection
is a string switch, not an import.
"""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """Raised when the resolved settings are internally inconsistent
    (e.g. a mock AI provider selected in production)."""


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

    # --- AI provider ---
    ai_provider: str = Field(default="gemini")
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-3.6-flash")

    # Cost/latency/token controls (see services/agent/chat_pipeline.py and
    # services/agent/conversation_context.py for where these are enforced).
    ai_request_timeout_seconds: float = Field(default=30.0)
    ai_max_output_tokens: int = Field(default=2048)
    ai_max_input_chars: int = Field(default=4000)
    ai_retry_max_attempts: int = Field(default=3)
    ai_retry_base_delay_seconds: float = Field(default=0.5)

    # --- Terminal Engine (see services/terminal/config.py for enforcement) ---
    terminal_workspace_root: str | None = Field(default=None)
    terminal_default_timeout_seconds: int = Field(default=30)
    terminal_max_timeout_seconds: int = Field(default=120)
    terminal_max_stdout_bytes: int = Field(default=1_000_000)
    terminal_max_stderr_bytes: int = Field(default=1_000_000)
    terminal_session_ttl_seconds: int = Field(default=900)
    terminal_max_concurrent_sessions: int = Field(default=20)
    # None means auto-detect (prefers `pwsh`, falls back to `powershell.exe`)
    # — see services/terminal/adapters/windows.py.
    terminal_windows_powershell_path: str | None = Field(default=None)
    # None means auto-detect ($SHELL, then bash/sh) — informational only,
    # see services/terminal/adapters/linux.py.
    terminal_linux_shell_path: str | None = Field(default=None)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @model_validator(mode="after")
    def _validate_ai_provider(self) -> "Settings":
        if self.ai_provider not in {"gemini", "mock"}:
            raise ConfigurationError(
                f"AI_PROVIDER must be 'gemini' or 'mock', got {self.ai_provider!r}."
            )
        if self.is_production and self.ai_provider == "mock":
            raise ConfigurationError(
                "AI_PROVIDER=mock is not allowed when ENVIRONMENT=production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
