"""Health check endpoints.

Two endpoints with different semantics:

``GET /health``
    **Liveness probe** — returns 200 if the Python process is alive.
    No I/O.  Safe to call at high frequency from load balancers.

``GET /health/ready``
    **Readiness probe** — returns 200 only if the database responds.
    Returns 503 if the DB is unreachable.  Kubernetes should gate traffic
    on this endpoint, not ``/health``.

Both endpoints are excluded from API authentication (Sprint 2.2) because
infrastructure tooling must be able to call them without credentials.
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from athena.db.session import async_ping

logger = logging.getLogger(__name__)

router = APIRouter(tags=["meta"])


@router.get("/health")
async def liveness() -> dict:
    """Liveness probe — always 200 while the process is running."""
    return {"status": "ok", "service": "athena-ai"}


@router.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe — 200 if DB is reachable, 503 otherwise.

    Reads the engine stored on ``app.state`` by the lifespan context manager.
    Falls back gracefully if the lifespan was not executed (e.g. in tests
    that call ``create_app()`` without the lifespan).
    """
    engine = getattr(request.app.state, "db_engine", None)

    if engine is None:
        # Lifespan not active (test environment or startup not complete)
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "database": "skipped",
                "detail": "lifespan not active",
            },
        )

    start = time.monotonic()
    try:
        await async_ping(engine)
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "database": "ok",
                "latency_ms": latency_ms,
            },
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.warning("Health check: database unreachable — %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "error",
                "latency_ms": latency_ms,
                "detail": str(exc),
            },
        )
