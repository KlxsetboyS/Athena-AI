"""Athena AI – centralized application configuration.

All configuration is read from environment variables at startup.
Pydantic-Settings validates types and provides clear errors if a required
variable is missing or malformed.

Usage::

    from athena.config import get_settings

    settings = get_settings()
    print(settings.database_url)

The ``get_settings()`` function is cached with ``@lru_cache`` so the
environment is only read once per process.  Tests that need custom values
should call ``get_settings.cache_clear()`` after patching the environment.

Environment variables (all optional – defaults shown):

    DATABASE_URL        sqlite+aiosqlite:///./athena.db
    DATABASE_ECHO       false
    DATABASE_POOL_SIZE  5
    LOG_LEVEL           INFO
    LOG_FORMAT          text
    APP_ENV             development
    REQUEST_ID_HEADER   X-Request-ID
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All fields have sensible defaults so the application works out-of-the-box
    with SQLite for local development without any environment setup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # silently ignore unknown env vars
    )

    # ── Database ──────────────────────────────────────────────────────────────

    database_url: str = "sqlite+aiosqlite:///./athena.db"
    """Async SQLAlchemy connection URL.

    - SQLite (dev/test): ``sqlite+aiosqlite:///./athena.db``
    - PostgreSQL (prod): ``postgresql+asyncpg://user:pass@host:5432/dbname``
    """

    database_echo: bool = False
    """When True, SQLAlchemy logs every SQL statement.  Use only in development."""

    database_pool_size: int = 5
    """Connection pool size.  Ignored by SQLite (which uses StaticPool)."""

    # ── Logging ───────────────────────────────────────────────────────────────

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    """Python logging level, applied globally at startup."""

    log_format: Literal["text", "json"] = "text"
    """Output format.  Use ``json`` in production for log aggregation pipelines."""

    # ── Application ───────────────────────────────────────────────────────────

    app_env: Literal["development", "testing", "production"] = "development"
    """Deployment environment.  Affects defaults and safety guards."""

    request_id_header: str = "X-Request-ID"
    """HTTP header name used to propagate request correlation IDs."""

    # ── Validators ────────────────────────────────────────────────────────────


    # ── HTTP Client ───────────────────────────────────────────────────────────

    http_connect_timeout: float = 5.0
    """Seconds to wait for TCP connection to establish."""

    http_read_timeout: float = 30.0
    """Seconds to wait for the server to send a response body."""

    http_write_timeout: float = 10.0
    """Seconds to wait to send the request body."""

    http_pool_timeout: float = 5.0
    """Seconds to wait for a connection from the pool."""

    # ── Retry ─────────────────────────────────────────────────────────────────

    retry_max_attempts: int = 3
    """Total number of attempts (1 = no retries)."""

    retry_backoff_base: float = 1.0
    """Base wait time in seconds for exponential backoff."""

    retry_backoff_max: float = 60.0
    """Maximum wait time cap in seconds."""

    retry_jitter: bool = True
    """Randomise wait time by ±50 % to avoid thundering herd."""

    # ── Football Data provider ────────────────────────────────────────────────

    football_data_api_key: str | None = None
    """API key for football-data.org.  None = provider disabled."""

    football_data_base_url: str = "https://api.football-data.org/v4"
    """Base URL for the football-data.org v4 API."""

    football_data_rate_limit_per_minute: int = 10
    """Request rate limit (tier free = 10/min)."""

    # ── The Odds API provider ─────────────────────────────────────────────────

    odds_api_key: str | None = None
    """API key for the-odds-api.com.  None = provider disabled."""

    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    """Base URL for the-odds-api.com v4 API."""

    odds_api_rate_limit_per_month: int = 500
    """Request quota per month (tier free = 500)."""

    @field_validator("database_url")
    @classmethod
    def database_url_must_be_async(cls, v: str) -> str:
        """Reject sync drivers that would block the event loop."""
        blocked = ("postgresql://", "mysql://", "sqlite:///")
        for prefix in blocked:
            if v.startswith(prefix):
                raise ValueError(
                    f"database_url must use an async driver "
                    f"(e.g. postgresql+asyncpg://, sqlite+aiosqlite://). "
                    f"Got: {v!r}"
                )
        return v

    @field_validator("database_pool_size")
    @classmethod
    def pool_size_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"database_pool_size must be >= 1, got {v}")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Call ``get_settings.cache_clear()`` in tests that need to inject
    custom environment variables.
    """
    return Settings()
