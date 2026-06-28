"""Shared fixtures for API unit tests.

Strategy
--------
- Never touch a real database: all Service deps are overridden with AsyncMock.
- Use httpx.AsyncClient + ASGITransport to exercise the full ASGI stack
  (routing, request parsing, response serialization) without a live server.
- Each test module imports `client` from here; the override teardown is
  handled automatically by the fixture's `finally` block.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from athena.api import create_app
from athena.api.deps import (
    get_competition_service,
    get_match_service,
    get_odds_service,
    get_season_service,
    get_team_service,
)


def _make_app_with_overrides(**overrides):
    """Return (app, client_factory) with dependency overrides applied."""
    application = create_app()
    for dep, mock in overrides.items():
        application.dependency_overrides[dep] = lambda m=mock: m
    return application


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def competition_mock():
    return AsyncMock()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def season_mock():
    return AsyncMock()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def team_mock():
    return AsyncMock()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def match_mock():
    return AsyncMock()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def odds_mock():
    return AsyncMock()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def api_client(
    competition_mock, season_mock, team_mock, match_mock, odds_mock
):
    """AsyncClient wired to the full FastAPI app with all services mocked."""
    app = create_app()
    app.dependency_overrides[get_competition_service] = lambda: competition_mock
    app.dependency_overrides[get_season_service] = lambda: season_mock
    app.dependency_overrides[get_team_service] = lambda: team_mock
    app.dependency_overrides[get_match_service] = lambda: match_mock
    app.dependency_overrides[get_odds_service] = lambda: odds_mock

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, competition_mock, season_mock, team_mock, match_mock, odds_mock
