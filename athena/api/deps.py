"""FastAPI dependency providers.

All application dependencies are declared here so that routers stay
clean and dependency overrides in tests touch a single file.

Session lifecycle
-----------------
A new :class:`AsyncSession` is created per request, committed on success,
and rolled back on any exception.  This matches the Unit-of-Work pattern
used by the repository layer.

Service construction
--------------------
Each ``get_*_service`` function creates the required repositories from the
session and injects them into the service.  Services are request-scoped:
no shared state between requests.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from athena.db.session import build_async_engine, build_async_session_factory
from athena.repositories.competition import CompetitionRepository
from athena.repositories.match import MatchRepository
from athena.repositories.odds import BookmakerRepository, OddsRepository
from athena.repositories.season import SeasonRepository
from athena.repositories.team import TeamRepository
from athena.services.competition_service import CompetitionService
from athena.services.match_service import MatchService
from athena.services.odds_service import OddsService
from athena.services.season_service import SeasonService
from athena.services.team_service import TeamService

# ── Engine (process-scoped singleton) ─────────────────────────────────────────

_DEFAULT_DB_URL = "sqlite+aiosqlite:///./athena.db"


@lru_cache(maxsize=1)
def _get_engine():
    url = os.environ.get("DATABASE_URL", _DEFAULT_DB_URL)
    return build_async_engine(url, echo=False)


@lru_cache(maxsize=1)
def _get_session_factory():
    return build_async_session_factory(_get_engine())


# ── Session (request-scoped) ──────────────────────────────────────────────────


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a managed :class:`AsyncSession` for the duration of one request."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Service providers (request-scoped) ───────────────────────────────────────


async def get_competition_service(
    session: AsyncSession = Depends(get_session),
) -> CompetitionService:
    return CompetitionService(CompetitionRepository(session))


async def get_season_service(
    session: AsyncSession = Depends(get_session),
) -> SeasonService:
    return SeasonService(SeasonRepository(session))


async def get_team_service(
    session: AsyncSession = Depends(get_session),
) -> TeamService:
    return TeamService(TeamRepository(session))


async def get_match_service(
    session: AsyncSession = Depends(get_session),
) -> MatchService:
    return MatchService(MatchRepository(session))


async def get_odds_service(
    session: AsyncSession = Depends(get_session),
) -> OddsService:
    return OddsService(OddsRepository(session), BookmakerRepository(session))


# ── Provider access (request-scoped) ─────────────────────────────────────────


async def get_provider(
    name: str,
    request: "Request",
):
    """Return a registered provider by name, or raise 503 if unavailable.

    Args:
        name:    Provider name (e.g. ``"football-data"``).
        request: FastAPI Request — used to read ``app.state.providers``.

    Raises:
        HTTPException(503): If the provider registry is not initialised.
        HTTPException(404): If no provider with *name* is registered.
    """
    from fastapi import HTTPException, Request  # local to avoid circular at module level

    providers = getattr(request.app.state, "providers", None)
    if providers is None:
        raise HTTPException(503, detail="Provider registry not initialised")
    provider = providers.get(name)
    if provider is None:
        raise HTTPException(404, detail=f"Provider '{name}' not registered")
    return provider
