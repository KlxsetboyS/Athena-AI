"""Unit tests for MatchService."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from athena.services.match_service import MatchService


def _make_service() -> tuple[MatchService, AsyncMock]:
    repo = AsyncMock()
    return MatchService(repo), repo


def _fake_match() -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    return m


class TestGetMatch:
    async def test_delegates_to_get_by_id_or_raise(self):
        svc, repo = _make_service()
        match = _fake_match()
        repo.get_by_id_or_raise.return_value = match

        result = await svc.get_match(match.id)

        repo.get_by_id_or_raise.assert_awaited_once_with(match.id)
        assert result is match

    async def test_propagates_lookup_error(self):
        svc, repo = _make_service()
        repo.get_by_id_or_raise.side_effect = LookupError

        with pytest.raises(LookupError):
            await svc.get_match(uuid.uuid4())


class TestGetMatchWithResult:
    async def test_delegates_to_get_with_result(self):
        svc, repo = _make_service()
        match = _fake_match()
        repo.get_with_result.return_value = match

        result = await svc.get_match_with_result(match.id)

        repo.get_with_result.assert_awaited_once_with(match.id)
        assert result is match

    async def test_returns_none_when_not_found(self):
        svc, repo = _make_service()
        repo.get_with_result.return_value = None

        result = await svc.get_match_with_result(uuid.uuid4())

        assert result is None


class TestGetMatchWithOdds:
    async def test_delegates_to_get_with_odds(self):
        svc, repo = _make_service()
        match = _fake_match()
        repo.get_with_odds.return_value = match

        result = await svc.get_match_with_odds(match.id)

        repo.get_with_odds.assert_awaited_once_with(match.id)
        assert result is match


class TestGetMatchHistory:
    async def test_delegates_to_get_by_team_with_defaults(self):
        svc, repo = _make_service()
        team_id = uuid.uuid4()
        repo.get_by_team.return_value = []

        await svc.get_match_history(team_id)

        repo.get_by_team.assert_awaited_once_with(
            team_id, season_id=None, limit=50
        )

    async def test_season_id_and_limit_forwarded(self):
        svc, repo = _make_service()
        team_id = uuid.uuid4()
        season_id = uuid.uuid4()
        repo.get_by_team.return_value = []

        await svc.get_match_history(team_id, season_id=season_id, limit=10)

        repo.get_by_team.assert_awaited_once_with(
            team_id, season_id=season_id, limit=10
        )

    async def test_returns_repo_result(self):
        svc, repo = _make_service()
        matches = [_fake_match(), _fake_match()]
        repo.get_by_team.return_value = matches

        result = await svc.get_match_history(uuid.uuid4())

        assert result is matches


class TestGetHeadToHead:
    async def test_delegates_to_repo_with_defaults(self):
        svc, repo = _make_service()
        a_id, b_id = uuid.uuid4(), uuid.uuid4()
        repo.get_head_to_head.return_value = []

        await svc.get_head_to_head(a_id, b_id)

        repo.get_head_to_head.assert_awaited_once_with(a_id, b_id, limit=10)

    async def test_custom_limit_forwarded(self):
        svc, repo = _make_service()
        a_id, b_id = uuid.uuid4(), uuid.uuid4()
        repo.get_head_to_head.return_value = []

        await svc.get_head_to_head(a_id, b_id, limit=5)

        repo.get_head_to_head.assert_awaited_once_with(a_id, b_id, limit=5)


class TestGetUpcomingMatches:
    async def test_defaults_forwarded(self):
        svc, repo = _make_service()
        repo.get_upcoming.return_value = []

        await svc.get_upcoming_matches()

        repo.get_upcoming.assert_awaited_once_with(
            competition_id=None, from_time=None, limit=50
        )

    async def test_all_params_forwarded(self):
        svc, repo = _make_service()
        comp_id = uuid.uuid4()
        from_time = datetime(2025, 8, 1, tzinfo=timezone.utc)
        repo.get_upcoming.return_value = []

        await svc.get_upcoming_matches(
            competition_id=comp_id, from_time=from_time, limit=20
        )

        repo.get_upcoming.assert_awaited_once_with(
            competition_id=comp_id, from_time=from_time, limit=20
        )

    async def test_returns_repo_result(self):
        svc, repo = _make_service()
        matches = [_fake_match()]
        repo.get_upcoming.return_value = matches

        result = await svc.get_upcoming_matches()

        assert result is matches


class TestGetFinishedMatches:
    async def test_defaults_forwarded(self):
        svc, repo = _make_service()
        repo.get_finished.return_value = []

        await svc.get_finished_matches()

        repo.get_finished.assert_awaited_once_with(
            competition_id=None, season_id=None, limit=100
        )

    async def test_all_params_forwarded(self):
        svc, repo = _make_service()
        comp_id = uuid.uuid4()
        season_id = uuid.uuid4()
        repo.get_finished.return_value = []

        await svc.get_finished_matches(
            competition_id=comp_id, season_id=season_id, limit=50
        )

        repo.get_finished.assert_awaited_once_with(
            competition_id=comp_id, season_id=season_id, limit=50
        )
