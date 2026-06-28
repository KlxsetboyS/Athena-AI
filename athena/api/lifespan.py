"""FastAPI application lifespan — startup and graceful shutdown.

The lifespan context manager is the recommended way (since FastAPI 0.93)
to run code at startup and shutdown, replacing the deprecated
``@app.on_event("startup")`` / ``@app.on_event("shutdown")`` decorators.

What happens at startup
-----------------------
1. ``Settings`` are loaded and validated (fast-fail if config is wrong).
2. Logging is configured once for the whole process.
3. An async engine is created and stored on ``app.state`` for introspection
   (e.g. the ``/health/ready`` endpoint).
4. A connectivity check is performed — if the DB is unreachable the process
   exits immediately rather than accepting traffic that will fail.

What happens at shutdown
------------------------
1. The async engine disposes its connection pool cleanly.
   This prevents ``ResourceWarning`` from unclosed sockets and ensures
   in-flight queries finish before the process exits.

Compatibility note
------------------
``deps.py`` is intentionally *not* changed.  The ``get_session`` dependency
continues to use its own ``_get_session_factory()`` (lru_cache).  The engine
stored on ``app.state`` is used *only* by the health check endpoint.
This keeps full backward compatibility with the 160 existing tests.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from athena.config import get_settings
from athena.db.session import async_ping, build_async_engine, build_async_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown.

    The engine stored on ``app.state`` is separate from the one used by
    ``deps.py``.  This is intentional: it avoids modifying the public
    dependency contract while still enabling the health endpoint to verify
    DB connectivity using the *same* ``DATABASE_URL`` from ``Settings``.
    """
    settings = get_settings()

    # ── Logging (configured first so startup messages are captured) ───────────
    # Import here to avoid circular import at module level
    # (logging_config imports middleware, middleware is part of api package)
    from athena.logging_config import configure_logging
    configure_logging(level=settings.log_level, fmt=settings.log_format)

    logger.info(
        "Athena AI starting",
        extra={
            "app_env": settings.app_env,
            "database_url": _redact_url(settings.database_url),
            "log_level": settings.log_level,
        },
    )

    # ── Database engine for health checks ────────────────────────────────────
    engine = build_async_engine(
        settings.database_url,
        echo=settings.database_echo,
    )

    try:
        await async_ping(engine)
        logger.info("Database connectivity confirmed")
    except Exception as exc:  # noqa: BLE001
        logger.error("Database unreachable at startup: %s", exc)
        await engine.dispose()
        raise RuntimeError(
            f"Cannot connect to database: {exc}"
        ) from exc

    # Expose on app.state for the health endpoint (read-only, no mutations)
    app.state.db_engine = engine
    app.state.db_session_factory = build_async_session_factory(engine)

    logger.info("Athena AI startup complete")

    yield  # ── Application runs here ─────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Athena AI shutting down — disposing connection pool")
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
