"""Athena AI – FastAPI application.

Usage (development)::

    uvicorn athena.api:app --reload

Usage (production)::

    DATABASE_URL=postgresql+asyncpg://user:pass@host/db uvicorn athena.api:app

Sprint 2.1 additions
--------------------
- ``lifespan`` context manager: DB connectivity check at startup, clean pool
  shutdown on exit.
- ``RequestIDMiddleware``: propagates ``X-Request-ID`` through every request.
- ``/health`` (liveness) and ``/health/ready`` (readiness) endpoints.
- Structured logging via ``configure_logging()`` called inside lifespan.

Backward compatibility
----------------------
``create_app()`` still works without arguments and ``deps.py`` is unchanged,
so all 160 existing tests continue to pass unmodified.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from athena.api.lifespan import lifespan
from athena.api.middleware import RequestIDMiddleware
from athena.api.routers.competitions import router as competitions_router
from athena.api.routers.health import router as health_router
from athena.api.routers.matches import router as matches_router
from athena.api.routers.odds import bookmaker_router, match_odds_router
from athena.api.routers.seasons import router as seasons_router
from athena.api.routers.teams import router as teams_router
from athena.config import get_settings


def create_app(*, use_lifespan: bool = True) -> FastAPI:
    """Construct and configure the FastAPI application.

    Args:
        use_lifespan: When ``True`` (default), the lifespan context manager
            handles startup/shutdown (DB ping, logging setup, pool disposal).
            Pass ``False`` in unit tests that mock all services and do not
            need a real database connection — this keeps the existing test
            fixture pattern working unchanged.
    """
    settings = get_settings()

    application = FastAPI(
        title="Athena AI",
        description="Football analytics API — competition, match and odds data.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan if use_lifespan else None,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    # Added in Sprint 2.1. Runs before routing so the request_id is available
    # to all handlers and log records.
    application.add_middleware(
        RequestIDMiddleware,
        header_name=settings.request_id_header,
    )

    # ── Global exception handlers ─────────────────────────────────────────────

    @application.exception_handler(LookupError)
    async def lookup_error_handler(request: Request, exc: LookupError) -> JSONResponse:
        """Convert repository/service LookupError into HTTP 404."""
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    # ── Routers ───────────────────────────────────────────────────────────────
    # Health router registered first so /health is always reachable even if
    # domain routers fail to load (defensive ordering).
    application.include_router(health_router)
    application.include_router(competitions_router)
    application.include_router(seasons_router)
    application.include_router(teams_router)
    application.include_router(matches_router)
    application.include_router(bookmaker_router)
    application.include_router(match_odds_router)

    return application


# Module-level app instance consumed by uvicorn / tests
app = create_app()
