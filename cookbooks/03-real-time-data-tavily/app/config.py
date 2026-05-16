"""Pydantic Settings — every env var is validated at boot."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings. Read once at boot, then injected via Depends()."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Nebius
    nebius_api_key: str = Field(..., min_length=1)
    nebius_base_url: HttpUrl = Field(default=HttpUrl("https://api.studio.nebius.ai/v1/"))
    nebius_planner_model: str = Field(default="Qwen/Qwen3-30B-A3B-Instruct")
    nebius_writer_model: str = Field(default="meta-llama/Llama-3.3-70B-Instruct")

    # Tavily
    tavily_api_key: str = Field(..., min_length=1)
    tavily_search_depth: Literal["basic", "advanced"] = Field(default="basic")
    tavily_max_results: int = Field(default=5, ge=1, le=20)

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    env: Literal["development", "staging", "production"] = Field(default="development")

    # Security
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    max_request_bytes: int = Field(default=65_536, ge=1024)

    # Observability
    log_level: Literal["debug", "info", "warning", "error"] = Field(default="info")

    # Limits
    rate_limit_per_minute: int = Field(default=10, ge=1)
    request_timeout_seconds: int = Field(default=60, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept either a JSON list or a comma-separated string from env."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return value
            return [v.strip() for v in value.split(",") if v.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Memoized settings accessor. Use this everywhere — never call Settings() directly."""
    return Settings()  # type: ignore[call-arg]
