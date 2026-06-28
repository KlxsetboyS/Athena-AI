"""Unit tests for CompetitionService.

Strategy
--------
Repositories are replaced with AsyncMock instances.  Tests verify:
- the correct repository method is called,
- arguments are forwarded unchanged,
- the return value is propagated to the caller.

No SQLite, no I/O.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from athena.db.enums import CompetitionGender, CompetitionType
from athena.services.competition_service import CompetitionService


def _make_service() -> tuple[CompetitionService, AsyncMock]:
    """Return (service, mock_repo) pair."""
    repo = AsyncMock()
    return CompetitionService(repo), repo


def _fake_competition(name: str = "Premier League") -> MagicMock:
    comp = MagicMock()
    comp.id = uuid.uuid4()
    comp.name = name
    return comp


class TestGetCompetition:
    async def test_delegates_to_get_by_id_or_raise(self):
        svc, repo = _make_service()
        comp = _fake_competition()
        repo.get_by_id_or_raise.return_value = comp

        result = await svc.get_competition(comp.id)

        repo.get_by_id_or_raise.assert_awaited_once_with(comp.id)
        assert result is comp

    async def test_propagates_lookup_error(self):
        svc, repo = _make_service()
        repo.get_by_id_or_raise.side_effect = LookupError("not found")

        with pytest.raises(LookupError):
            await svc.get_competition(uuid.uuid4())


class TestGetByExternalId:
    async def test_delegates_to_repo(self):
        svc, repo = _make_service()
        comp = _fake_competition()
        repo.get_by_external_id.return_value = comp

        result = await svc.get_by_external_id("ENG.1")

        repo.get_by_external_id.assert_awaited_once_with("ENG.1")
        assert result is comp

    async def test_returns_none_when_not_found(self):
        svc, repo = _make_service()
        repo.get_by_external_id.return_value = None

        result = await svc.get_by_external_id("UNKNOWN")

        assert result is None


class TestListCompetitions:
    async def test_no_filters_calls_list(self):
        svc, repo = _make_service()
        repo.list.return_value = []

        await svc.list_competitions()

        repo.list.assert_awaited_once_with(offset=0, limit=100)

    async def test_pagination_forwarded(self):
        svc, repo = _make_service()
        repo.list.return_value = []

        await svc.list_competitions(offset=20, limit=10)

        repo.list.assert_awaited_once_with(offset=20, limit=10)

    async def test_competition_type_filter_calls_get_by_type(self):
        svc, repo = _make_service()
        repo.get_by_type.return_value = []

        await svc.list_competitions(competition_type=CompetitionType.LEAGUE)

        repo.get_by_type.assert_awaited_once_with(
            CompetitionType.LEAGUE, country_code=None
        )

    async def test_type_and_country_forwarded(self):
        svc, repo = _make_service()
        repo.get_by_type.return_value = []

        await svc.list_competitions(
            competition_type=CompetitionType.CUP, country_code="ENG"
        )

        repo.get_by_type.assert_awaited_once_with(
            CompetitionType.CUP, country_code="ENG"
        )

    async def test_country_only_calls_get_by_country(self):
        svc, repo = _make_service()
        repo.get_by_country.return_value = []

        await svc.list_competitions(country_code="ESP")

        repo.get_by_country.assert_awaited_once_with("ESP")

    async def test_returns_repo_result(self):
        svc, repo = _make_service()
        comps = [_fake_competition("La Liga"), _fake_competition("Segunda")]
        repo.list.return_value = comps

        result = await svc.list_competitions()

        assert result is comps
