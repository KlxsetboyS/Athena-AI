"""Tests for IngestionService — provider and repositories are mocked."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from athena.db.enums import (
    CompetitionGender,
    CompetitionType,
    MatchStatus,
    OddsMarket,
    SelectionType,
)
from athena.providers.exceptions import ProviderConnectionError
from athena.providers.models import (
    CompetitionDTO,
    MatchDTO,
    OddsSelectionDTO,
    OddsSnapshotDTO,
)
from athena.services.ingestion_service import (
    IngestionResult,
    IngestionService,
    RepositoryBundle,
)

_NOW = datetime(2024, 8, 16, 19, 0, tzinfo=timezone.utc)


# ── Factories ─────────────────────────────────────────────────────────────────

def _fake_competition_dto(**kwargs) -> CompetitionDTO:
    return CompetitionDTO(
        external_id=kwargs.get("external_id", "fd.2021"),
        name=kwargs.get("name", "Premier League"),
        competition_type=kwargs.get("competition_type", CompetitionType.LEAGUE),
        gender=kwargs.get("gender", CompetitionGender.MALE),
        country_code=kwargs.get("country_code", "ENG"),
    )


def _fake_match_dto(**kwargs) -> MatchDTO:
    return MatchDTO(
        external_id=kwargs.get("external_id", "fd.419126"),
        competition_external_id=kwargs.get("competition_external_id", "fd.2021"),
        home_team_external_id=kwargs.get("home_team_external_id", "fd.57"),
        away_team_external_id=kwargs.get("away_team_external_id", "fd.328"),
        kickoff_time_utc=kwargs.get("kickoff_time_utc", _NOW),
        status=kwargs.get("status", MatchStatus.SCHEDULED),
    )


def _fake_odds_dto(**kwargs) -> OddsSnapshotDTO:
    sel = OddsSelectionDTO(
        selection_type=SelectionType.HOME,
        decimal_odd=Decimal("1.65"),
    )
    return OddsSnapshotDTO(
        match_external_id=kwargs.get("match_external_id", "fd.419126"),
        bookmaker_slug=kwargs.get("bookmaker_slug", "bet365"),
        bookmaker_name=kwargs.get("bookmaker_name", "Bet365"),
        market=kwargs.get("market", OddsMarket.MATCH_WINNER),
        captured_at=kwargs.get("captured_at", _NOW),
        source="test",
        selections=(sel,),
        external_ref=kwargs.get("external_ref", "ref.001"),
    )


def _make_repos() -> RepositoryBundle:
    return RepositoryBundle(
        competitions=AsyncMock(),
        seasons=AsyncMock(),
        teams=AsyncMock(),
        matches=AsyncMock(),
        odds=AsyncMock(),
        bookmakers=AsyncMock(),
    )


def _make_service(provider=None, repos=None):
    if provider is None:
        provider = AsyncMock()
        provider.name = "test-provider"
    if repos is None:
        repos = _make_repos()
    return IngestionService(provider, repos), provider, repos


# ── RepositoryBundle ──────────────────────────────────────────────────────────

class TestRepositoryBundle:
    def test_has_all_six_repos(self):
        repos = _make_repos()
        assert repos.competitions is not None
        assert repos.seasons is not None
        assert repos.teams is not None
        assert repos.matches is not None
        assert repos.odds is not None
        assert repos.bookmakers is not None


# ── IngestCompetitions ────────────────────────────────────────────────────────

class TestIngestCompetitions:
    async def test_creates_new_competition(self):
        svc, provider, repos = _make_service()
        dto = _fake_competition_dto()
        provider.get_competitions.return_value = [dto]
        repos.competitions.get_by_external_id.return_value = None

        result = await svc.ingest_competitions()

        repos.competitions.create.assert_awaited_once()
        assert result.created == 1
        assert result.updated == 0

    async def test_skips_unchanged_competition(self):
        svc, provider, repos = _make_service()
        dto = _fake_competition_dto(name="Premier League")
        existing = MagicMock()
        existing.name = "Premier League"
        existing.country_code = "ENG"
        provider.get_competitions.return_value = [dto]
        repos.competitions.get_by_external_id.return_value = existing

        result = await svc.ingest_competitions()

        repos.competitions.create.assert_not_awaited()
        repos.competitions.update.assert_not_awaited()
        assert result.skipped == 1

    async def test_updates_changed_competition(self):
        svc, provider, repos = _make_service()
        dto = _fake_competition_dto(name="New Name")
        existing = MagicMock()
        existing.name = "Old Name"
        existing.country_code = "ENG"
        provider.get_competitions.return_value = [dto]
        repos.competitions.get_by_external_id.return_value = existing

        result = await svc.ingest_competitions()

        repos.competitions.update.assert_awaited_once()
        assert result.updated == 1

    async def test_provider_error_returns_error_result(self):
        svc, provider, repos = _make_service()
        provider.get_competitions.side_effect = ProviderConnectionError(
            "timeout", provider="test"
        )
        result = await svc.ingest_competitions()
        assert result.errors == 1
        assert result.created == 0

    async def test_country_filter_forwarded_to_provider(self):
        svc, provider, repos = _make_service()
        provider.get_competitions.return_value = []
        await svc.ingest_competitions(country_code="ENG")
        provider.get_competitions.assert_awaited_once_with(country_code="ENG")


# ── IngestMatches ─────────────────────────────────────────────────────────────

class TestIngestMatches:
    async def test_skips_match_when_competition_not_found(self):
        svc, provider, repos = _make_service()
        dto = _fake_match_dto()
        provider.get_matches.return_value = [dto]
        repos.matches.get_by_external_id.return_value = None
        repos.competitions.get_by_external_id.return_value = None

        result = await svc.ingest_matches("fd.2021")

        repos.matches.create.assert_not_awaited()
        assert result.skipped == 1

    async def test_skips_match_when_team_not_found(self):
        svc, provider, repos = _make_service()
        dto = _fake_match_dto()
        fake_comp = MagicMock()
        fake_comp.id = uuid.uuid4()
        provider.get_matches.return_value = [dto]
        repos.matches.get_by_external_id.return_value = None
        repos.competitions.get_by_external_id.return_value = fake_comp
        repos.teams.get_by_external_id.return_value = None

        result = await svc.ingest_matches("fd.2021")

        repos.matches.create.assert_not_awaited()
        assert result.skipped == 1

    async def test_updates_status_on_existing_match(self):
        svc, provider, repos = _make_service()
        dto = _fake_match_dto(status=MatchStatus.FINISHED)
        existing = MagicMock()
        existing.status = MatchStatus.SCHEDULED
        provider.get_matches.return_value = [dto]
        repos.matches.get_by_external_id.return_value = existing

        result = await svc.ingest_matches("fd.2021")

        repos.matches.update.assert_awaited_once()
        assert result.updated == 1

    async def test_provider_error_returns_error_result(self):
        svc, provider, repos = _make_service()
        provider.get_matches.side_effect = ProviderConnectionError(
            "timeout", provider="test"
        )
        result = await svc.ingest_matches("fd.2021")
        assert result.errors == 1


# ── IngestOdds ────────────────────────────────────────────────────────────────

class TestIngestOdds:
    async def test_skips_existing_snapshot(self):
        svc, provider, repos = _make_service()
        dto = _fake_odds_dto(external_ref="ref.001")
        provider.get_odds.return_value = [dto]
        repos.odds.snapshot_exists.return_value = True

        result = await svc.ingest_odds("fd.419126")

        repos.odds.create.assert_not_awaited()
        assert result.skipped == 1

    async def test_skips_when_match_not_found(self):
        svc, provider, repos = _make_service()
        dto = _fake_odds_dto()
        provider.get_odds.return_value = [dto]
        repos.odds.snapshot_exists.return_value = False
        bookmaker = MagicMock()
        bookmaker.id = uuid.uuid4()
        repos.bookmakers.get_by_slug.return_value = bookmaker
        repos.matches.get_by_external_id.return_value = None

        result = await svc.ingest_odds("fd.419126")

        repos.odds.create.assert_not_awaited()
        assert result.skipped == 1

    async def test_creates_bookmaker_if_not_exists(self):
        svc, provider, repos = _make_service()
        dto = _fake_odds_dto()
        provider.get_odds.return_value = [dto]
        repos.odds.snapshot_exists.return_value = False
        repos.bookmakers.get_by_slug.return_value = None
        new_bk = MagicMock()
        new_bk.id = uuid.uuid4()
        repos.bookmakers.create.return_value = new_bk
        match = MagicMock()
        match.id = uuid.uuid4()
        repos.matches.get_by_external_id.return_value = match

        result = await svc.ingest_odds("fd.419126")

        repos.bookmakers.create.assert_awaited_once()

    async def test_provider_error_returns_error_result(self):
        svc, provider, repos = _make_service()
        provider.get_odds.side_effect = ProviderConnectionError(
            "timeout", provider="test"
        )
        result = await svc.ingest_odds("fd.419126")
        assert result.errors == 1


# ── IngestionResult ───────────────────────────────────────────────────────────

class TestIngestionResult:
    def test_str_representation(self):
        r = IngestionResult(entity="competitions", provider="test",
                            created=5, updated=2, skipped=1, errors=0)
        s = str(r)
        assert "test" in s
        assert "5" in s
