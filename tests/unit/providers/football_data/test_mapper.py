"""Tests for football_data mapper — pure functions, no I/O."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from athena.db.enums import CompetitionType, MatchStatus, SeasonStatus
from athena.providers.football_data.mapper import (
    map_competition,
    map_competitions,
    map_match,
    map_matches,
    map_season,
    map_team,
)
from athena.providers.models import CompetitionDTO, MatchDTO, SeasonDTO, TeamDTO

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "football_data"


def _load(filename: str) -> dict:
    return json.loads((FIXTURES / filename).read_text())


class TestMapCompetition:
    def test_maps_external_id_with_prefix(self):
        raw = {"id": 2021, "name": "Premier League", "type": "LEAGUE",
               "area": {"code": "ENG"}}
        dto = map_competition(raw)
        assert dto.external_id == "fd.2021"

    def test_maps_name(self):
        raw = {"id": 2021, "name": "Premier League", "type": "LEAGUE",
               "area": {"code": "ENG"}}
        assert map_competition(raw).name == "Premier League"

    def test_maps_country_code(self):
        raw = {"id": 2021, "name": "PL", "type": "LEAGUE",
               "area": {"code": "ENG"}}
        assert map_competition(raw).country_code == "ENG"

    def test_maps_league_type(self):
        raw = {"id": 2021, "name": "PL", "type": "LEAGUE", "area": {}}
        assert map_competition(raw).competition_type == CompetitionType.LEAGUE

    def test_maps_cup_type(self):
        raw = {"id": 2001, "name": "UCL", "type": "CUP", "area": {}}
        assert map_competition(raw).competition_type == CompetitionType.CUP

    def test_missing_area_code_gives_none(self):
        raw = {"id": 2021, "name": "PL", "type": "LEAGUE", "area": {}}
        assert map_competition(raw).country_code is None

    def test_result_is_frozen(self):
        raw = {"id": 2021, "name": "PL", "type": "LEAGUE", "area": {}}
        dto = map_competition(raw)
        with pytest.raises((AttributeError, TypeError)):
            dto.name = "changed"  # type: ignore


class TestMapCompetitionsFromFixture:
    def test_fixture_maps_two_competitions(self):
        raw = _load("competitions.json")
        dtos = map_competitions(raw)
        assert len(dtos) == 2

    def test_fixture_external_ids_prefixed(self):
        raw = _load("competitions.json")
        dtos = map_competitions(raw)
        assert all(dto.external_id.startswith("fd.") for dto in dtos)

    def test_fixture_names_present(self):
        raw = _load("competitions.json")
        dtos = map_competitions(raw)
        names = {dto.name for dto in dtos}
        assert "Premier League" in names


class TestMapSeason:
    def test_maps_year_start_from_start_date(self):
        raw = {"id": 1564, "startDate": "2024-08-16", "endDate": "2025-05-25",
               "currentMatchday": 20, "winner": None}
        dto = map_season(raw, "fd.2021")
        assert dto.year_start == 2024

    def test_maps_year_end_from_end_date(self):
        raw = {"id": 1564, "startDate": "2024-08-16", "endDate": "2025-05-25",
               "currentMatchday": 20, "winner": None}
        dto = map_season(raw, "fd.2021")
        assert dto.year_end == 2025

    def test_active_when_current_matchday_set(self):
        raw = {"id": 1564, "startDate": "2024-08-16", "endDate": "2025-05-25",
               "currentMatchday": 20, "winner": None}
        assert map_season(raw, "fd.2021").status == SeasonStatus.ACTIVE

    def test_finished_when_winner_set(self):
        raw = {"id": 1563, "startDate": "2023-08-11", "endDate": "2024-05-19",
               "currentMatchday": None, "winner": {"id": 57, "name": "Arsenal FC"}}
        assert map_season(raw, "fd.2021").status == SeasonStatus.FINISHED

    def test_external_id_prefixed(self):
        raw = {"id": 1564, "startDate": "2024-08-16", "endDate": "2025-05-25",
               "currentMatchday": 20, "winner": None}
        dto = map_season(raw, "fd.2021")
        assert dto.external_id == "fd.season.1564"


class TestMapMatch:
    def _raw_match(self, **overrides) -> dict:
        base = {
            "id": 419126,
            "utcDate": "2024-08-16T19:00:00Z",
            "status": "FINISHED",
            "matchday": 1,
            "competition": {"id": 2021, "name": "PL"},
            "season": {"id": 1564},
            "homeTeam": {"id": 57, "name": "Arsenal FC", "shortName": "Arsenal"},
            "awayTeam": {"id": 328, "name": "Wolves FC", "shortName": "Wolves"},
        }
        base.update(overrides)
        return base

    def test_maps_external_id(self):
        dto = map_match(self._raw_match())
        assert dto.external_id == "fd.419126"

    def test_maps_finished_status(self):
        assert map_match(self._raw_match(status="FINISHED")).status == MatchStatus.FINISHED

    def test_maps_scheduled_status(self):
        assert map_match(self._raw_match(status="SCHEDULED")).status == MatchStatus.SCHEDULED

    def test_maps_timed_as_scheduled(self):
        assert map_match(self._raw_match(status="TIMED")).status == MatchStatus.SCHEDULED

    def test_maps_home_and_away_team_ids(self):
        dto = map_match(self._raw_match())
        assert dto.home_team_external_id == "fd.57"
        assert dto.away_team_external_id == "fd.328"

    def test_maps_kickoff_utc(self):
        from datetime import timezone
        dto = map_match(self._raw_match())
        assert dto.kickoff_time_utc.tzinfo is not None
        assert dto.kickoff_time_utc.tzinfo.utcoffset(None).total_seconds() == 0

    def test_maps_matchday(self):
        assert map_match(self._raw_match()).matchday == 1


class TestMapMatchesFromFixture:
    def test_fixture_maps_two_matches(self):
        raw = _load("matches.json")
        dtos = map_matches(raw)
        assert len(dtos) == 2

    def test_fixture_statuses_correct(self):
        raw = _load("matches.json")
        dtos = map_matches(raw)
        statuses = {dto.status for dto in dtos}
        assert MatchStatus.FINISHED in statuses
        assert MatchStatus.SCHEDULED in statuses
