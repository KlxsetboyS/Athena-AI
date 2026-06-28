"""FastAPI application lifespan — startup and graceful shutdown.

Sprint 2.2 additions
--------------------
- Provider clients (httpx.AsyncClient wrappers) are initialised at startup
  and registered in ``app.state.providers`` as a ``dict[str, BaseProvider]``.
- Shutdown order: provider clients closed FIRST, then the database engine.
  This prevents in-flight retries from trying to write to a closed pool.

Backward compatibility
----------------------
All Sprint 2.0/2.1 behaviour is preserved.  ``deps.py`` is unchanged.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from fastapi import FastAPI

from athena.config import get_settings
from athena.db.session import async_ping, build_async_engine, build_async_session_factory
from athena.providers.base import BaseProvider
from athena.providers.client import ProviderClient
from athena.providers.rate_limiter import RateLimiter
from athena.providers.retry import RetryPolicy

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown.

    Startup order
    -------------
    1. Load and validate Settings.
    2. Configure structured logging.
    3. Create async DB engine; verify connectivity (fast-fail).
    4. Initialise provider clients for configured API keys.
    5. Register providers in ``app.state.providers``.

    Shutdown order
    --------------
    1. Close all provider HTTP clients (flush in-flight retries).
    2. Dispose the database connection pool.
    """
    settings = get_settings()

    # ── Logging ───────────────────────────────────────────────────────────────
    from athena.logging_config import configure_logging
    configure_logging(level=settings.log_level, fmt=settings.log_format)

    logger.info(
        "Athena AI starting",
        extra={
            "app_env": settings.app_env,
            "database_url": _redact_url(settings.database_url),
        },
    )

    # ── Database ──────────────────────────────────────────────────────────────
    engine = build_async_engine(
        settings.database_url,
        echo=settings.database_echo,
    )
    try:
        await async_ping(engine)
        logger.info("Database connectivity confirmed")
    except Exception as exc:
        logger.error("Database unreachable at startup: %s", exc)
        await engine.dispose()
        raise RuntimeError(f"Cannot connect to database: {exc}") from exc

    app.state.db_engine = engine
    app.state.db_session_factory = build_async_session_factory(engine)

    # ── Provider clients ──────────────────────────────────────────────────────
    provider_clients: list[ProviderClient] = []
    providers: dict[str, BaseProvider] = {}

    timeout = httpx.Timeout(
        connect=settings.http_connect_timeout,
        read=settings.http_read_timeout,
        write=settings.http_write_timeout,
        pool=settings.http_pool_timeout,
    )
    retry_policy = RetryPolicy(
        max_attempts=settings.retry_max_attempts,
        backoff_base=settings.retry_backoff_base,
        backoff_max=settings.retry_backoff_max,
        jitter=settings.retry_jitter,
    )

    if settings.football_data_api_key:
        from athena.providers.football_data.provider import FootballDataProvider

        min_interval = 60.0 / max(settings.football_data_rate_limit_per_minute, 1)
        fd_client = ProviderClient(
            base_url=settings.football_data_base_url,
            headers={"X-Auth-Token": settings.football_data_api_key},
            timeout=timeout,
            retry_policy=retry_policy,
            rate_limiter=RateLimiter(min_interval_seconds=min_interval),
            provider_name="football-data",
        )
        provider_clients.append(fd_client)
        fd_provider = FootballDataProvider(fd_client)
        providers[fd_provider.name] = fd_provider
        logger.info("Provider registered: football-data")

    if settings.odds_api_key:
        from athena.providers.odds_api.provider import OddsAPIProvider

        # odds-api free tier: 500/month ≈ ~1 per hour; use a conservative limit
        oa_client = ProviderClient(
            base_url=settings.odds_api_base_url,
            headers={},  # odds-api authenticates via query param
            timeout=timeout,
            retry_policy=retry_policy,
            rate_limiter=RateLimiter(min_interval_seconds=2.0),
            provider_name="odds-api",
        )
        provider_clients.append(oa_client)
        oa_provider = OddsAPIProvider(oa_client, api_key=settings.odds_api_key)
        providers[oa_provider.name] = oa_provider
        logger.info("Provider registered: odds-api")

    app.state.providers = providers
    logger.info(
        "Athena AI startup complete",
        extra={"providers": list(providers.keys())},
    )

    yield  # ── Application runs ──────────────────────────────────────────────

    # ── Shutdown: providers FIRST, then database ──────────────────────────────
    logger.info("Athena AI shutting down")

    for client in provider_clients:
        try:
            await client.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error closing provider client: %s", exc)

    await engine.dispose()
    logger.info("Athena AI shutdown complete")


def _redact_url(url: str) -> str:
    """Replace password in DB URL with *** for safe logging."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "***")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:  # noqa: BLE001
        pass
    return url
