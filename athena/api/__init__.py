"""Athena AI – FastAPI application.

Usage (development)::

    uvicorn athena.api:app --reload

Usage (production)::

    DATABASE_URL=postgresql+asyncpg://user:pass@host/db uvicorn athena.api:app
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from athena.api.routers.competitions import router as competitions_router
from athena.api.routers.matches import router as matches_router
from athena.api.routers.odds import bookmaker_router, match_odds_router
from athena.api.routers.seasons import router as seasons_router
from athena.api.routers.teams import router as teams_router


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Kept as a factory function so tests can call ``create_app()`` and
    apply dependency overrides before the first request.
    """
    application = FastAPI(
        title="Athena AI",
        description="Football analytics API — competition, match and odds data.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Global exception handlers ─────────────────────────────────────────────

    @application.exception_handler(LookupError)
    async def lookup_error_handler(request: Request, exc: LookupError) -> JSONResponse:
        """Convert repository/service LookupError into HTTP 404."""
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    # ── Routers ───────────────────────────────────────────────────────────────

    application.include_router(competitions_router)
    application.include_router(seasons_router)
    application.include_router(teams_router)
    application.include_router(matches_router)
    application.include_router(bookmaker_router)
    application.include_router(match_odds_router)

    # ── Health check ──────────────────────────────────────────────────────────

    @application.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "service": "athena-ai"}

    return application


# Module-level app instance consumed by uvicorn / tests
app = create_app()
