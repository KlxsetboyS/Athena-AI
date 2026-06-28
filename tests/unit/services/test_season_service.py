"""Unit tests for SeasonService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from athena.services.season_service import SeasonService


def _make_service() -> tuple[SeasonService, AsyncMock]:
    repo = AsyncMock()
    return SeasonService(repo), repo


def _fake_season() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    return s


class TestGetSeason:
    async def test_delegates_to_get_by_id_or_raise(self):
        svc, repo = _make_service()
        season = _fake_season()
        repo.get_by_id_or_raise.return_value = season

        result = await svc.get_season(season.id)

        repo.get_by_id_or_raise.assert_awaited_once_with(season.id)
        assert result is season

    async def test_propagates_lookup_error(self):
        svc, repo = _make_service()
        repo.get_by_id_or_raise.side_effect = LookupError

        with pytest.raises(LookupError):
            await svc.get_season(uuid.uuid4())


class TestGetCurrentSeason:
    async def test_delegates_to_get_current(self):
        svc, repo = _make_service()
        season = _fake_season()
        comp_id = uuid.uuid4()
        repo.get_current.return_value = season

        result = await svc.get_current_season(comp_id)

        repo.get_current.assert_awaited_once_with(comp_id)
        assert result is season

    async def test_returns_none_when_no_active_season(self):
        svc, repo = _make_service()
        repo.get_current.return_value = None

        result = await svc.get_current_season(uuid.uuid4())

        assert result is None


class TestListSeasons:
    async def test_delegates_to_get_by_competition(self):
        svc, repo = _make_service()
        comp_id = uuid.uuid4()
        seasons = [_fake_season(), _fake_season()]
        repo.get_by_competition.return_value = seasons

        result = await svc.list_seasons(comp_id)

        repo.get_by_competition.assert_awaited_once_with(comp_id)
        assert result is seasons


class TestListActiveSeasons:
    async def test_no_filter_calls_get_active_with_none(self):
        svc, repo = _make_service()
        repo.get_active.return_value = []

        await svc.list_active_seasons()

        repo.get_active.assert_awaited_once_with(None)

    async def test_competition_id_forwarded(self):
        svc, repo = _make_service()
        comp_id = uuid.uuid4()
        repo.get_active.return_value = []

        await svc.list_active_seasons(comp_id)

        repo.get_active.assert_awaited_once_with(comp_id)
