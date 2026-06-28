"""Unit tests for TeamService."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from athena.services.team_service import TeamService


def _make_service() -> tuple[TeamService, AsyncMock]:
    repo = AsyncMock()
    return TeamService(repo), repo


def _fake_team(name: str = "Arsenal FC") -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.name = name
    return t


class TestGetTeam:
    async def test_delegates_to_get_by_id_or_raise(self):
        svc, repo = _make_service()
        team = _fake_team()
        repo.get_by_id_or_raise.return_value = team

        result = await svc.get_team(team.id)

        repo.get_by_id_or_raise.assert_awaited_once_with(team.id)
        assert result is team

    async def test_propagates_lookup_error(self):
        svc, repo = _make_service()
        repo.get_by_id_or_raise.side_effect = LookupError

        with pytest.raises(LookupError):
            await svc.get_team(uuid.uuid4())


class TestGetByExternalId:
    async def test_delegates_to_repo(self):
        svc, repo = _make_service()
        team = _fake_team()
        repo.get_by_external_id.return_value = team

        result = await svc.get_by_external_id("t.arsenal")

        repo.get_by_external_id.assert_awaited_once_with("t.arsenal")
        assert result is team

    async def test_returns_none_when_not_found(self):
        svc, repo = _make_service()
        repo.get_by_external_id.return_value = None

        result = await svc.get_by_external_id("t.unknown")

        assert result is None


class TestSearchTeam:
    async def test_delegates_to_search_by_name(self):
        svc, repo = _make_service()
        teams = [_fake_team("Arsenal FC"), _fake_team("Arsenal Women")]
        repo.search_by_name.return_value = teams

        result = await svc.search_team("Arsenal")

        repo.search_by_name.assert_awaited_once_with("Arsenal")
        assert result is teams

    async def test_empty_result_propagated(self):
        svc, repo = _make_service()
        repo.search_by_name.return_value = []

        result = await svc.search_team("Nonexistent FC")

        assert result == []


class TestListTeamsInSeason:
    async def test_delegates_to_get_by_season(self):
        svc, repo = _make_service()
        season_id = uuid.uuid4()
        teams = [_fake_team("Arsenal"), _fake_team("Chelsea")]
        repo.get_by_season.return_value = teams

        result = await svc.list_teams_in_season(season_id)

        repo.get_by_season.assert_awaited_once_with(season_id)
        assert result is teams
