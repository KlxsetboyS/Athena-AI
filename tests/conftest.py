"""Shared pytest fixtures for Athena AI test suite.

Fixture hierarchy
-----------------
engine         – async SQLite engine, function-scoped (new DB per test)
db_session     – AsyncSession, function-scoped, always rolled back
repositories   – convenience fixtures that inject db_session into each repo

Design decisions for pytest-asyncio 1.x compatibility
------------------------------------------------------
- ALL async fixtures use pytest_asyncio.fixture with explicit
  loop_scope="function". This is mandatory in pytest-asyncio 1.x:
  mixing scopes (e.g. module-scoped async fixture with function-scoped
  test loop) raises ScopeMismatch.

- Engine is function-scoped: each test gets a fresh in-memory SQLite DB.
  This eliminates cross-test state leakage without needing rollbacks, and
  avoids the ScopeMismatch that comes from module-scoped async fixtures.

- We bypass Alembic and use metadata.create_all() directly for speed.

- Python 3.14 compatibility: no explicit event_loop fixture needed; let
  pytest-asyncio manage the loop lifecycle automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import Base so create_all picks up every mapped model
from athena.db.base import Base  # noqa: F401
import athena.db.models  # registers all models via __init__.py  # noqa: F401
from athena.db.enums import (
    CompetitionGender,
    CompetitionType,
    MatchStatus,
    SeasonStatus,
    TeamGender,
)
from athena.repositories.competition import CompetitionRepository
from athena.repositories.match import MatchRepository
from athena.repositories.odds import OddsRepository
from athena.repositories.season import SeasonRepository
from athena.repositories.team import TeamRepository


# ── Database engine (function-scoped — one fresh SQLite per test) ─────────────
# IMPORTANT: loop_scope="function" is required in pytest-asyncio 1.x.
# Without it, the fixture inherits its SQLAlchemy scope as the loop scope,
# causing ScopeMismatch when the test runner uses a function-scoped event loop.

@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def engine():
    """Async SQLite in-memory engine. Created fresh for every test."""
    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


# ── Per-test session ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session for a single test. Rolled back on teardown."""
    factory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ── Repository fixtures ────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def competition_repo(db_session: AsyncSession) -> CompetitionRepository:
    return CompetitionRepository(db_session)


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def team_repo(db_session: AsyncSession) -> TeamRepository:
    return TeamRepository(db_session)


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def season_repo(db_session: AsyncSession) -> SeasonRepository:
    return SeasonRepository(db_session)


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def match_repo(db_session: AsyncSession) -> MatchRepository:
    return MatchRepository(db_session)


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def odds_repo(db_session: AsyncSession) -> OddsRepository:
    return OddsRepository(db_session)


# ── Domain object factories ────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def sample_competition(competition_repo: CompetitionRepository):
    """A persisted Competition for use in other fixtures."""
    return await competition_repo.create(
        name="Premier League",
        country_code="ENG",
        competition_type=CompetitionType.LEAGUE,
        gender=CompetitionGender.MALE,
        external_id="ENG.1",
    )


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def sample_season(season_repo: SeasonRepository, sample_competition):
    """A persisted Season linked to sample_competition."""
    return await season_repo.create(
        competition_id=sample_competition.id,
        label="2023/24",
        year_start=2023,
        year_end=2024,
        status=SeasonStatus.FINISHED,
    )


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def sample_home_team(team_repo: TeamRepository):
    """A persisted home team."""
    return await team_repo.create(
        name="Arsenal FC",
        short_name="Arsenal",
        country_code="ENG",
        gender=TeamGender.MALE,
        external_id="t.arsenal",
    )


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def sample_away_team(team_repo: TeamRepository):
    """A persisted away team."""
    return await team_repo.create(
        name="Chelsea FC",
        short_name="Chelsea",
        country_code="ENG",
        gender=TeamGender.MALE,
        external_id="t.chelsea",
    )


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def sample_match(
    match_repo: MatchRepository,
    sample_competition,
    sample_season,
    sample_home_team,
    sample_away_team,
):
    """A persisted Match between home and away sample teams."""
    return await match_repo.create(
        competition_id=sample_competition.id,
        season_id=sample_season.id,
        home_team_id=sample_home_team.id,
        away_team_id=sample_away_team.id,
        kickoff_time_utc=datetime(2024, 1, 14, 15, 0, tzinfo=timezone.utc),
        venue="Emirates Stadium",
        matchday=21,
        status=MatchStatus.SCHEDULED,
        external_id="m.eng1.240114.ars_che",
    )
