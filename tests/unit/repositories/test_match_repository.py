"""Unit tests for MatchRepository domain-specific queries.

Coverage targets
----------------
- get_by_external_id()
- get_with_result()       (eager load)
- get_with_odds()         (eager load)
- get_by_date()           (time-range filter)
- get_by_competition()    (optionally scoped to season)
- get_by_team()           (home OR away)
- get_head_to_head()
- get_upcoming()
- get_finished()
- get_without_result()
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from athena.db.enums import MatchStatus, ResultType, MatchResultStatus, TeamGender, CompetitionType, CompetitionGender, SeasonStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

KICKOFF = datetime(2024, 1, 14, 15, 0, tzinfo=timezone.utc)


async def _make_team(team_repo, name: str, ext_id: str):
    return await team_repo.create(
        name=name,
        short_name=name[:8],
        country_code="ENG",
        gender=TeamGender.MALE,
        external_id=ext_id,
    )


async def _make_match(
    match_repo,
    competition,
    season,
    home_team,
    away_team,
    *,
    kickoff: datetime = KICKOFF,
    status: MatchStatus = MatchStatus.SCHEDULED,
    external_id: str | None = None,
    matchday: int = 1,
):
    return await match_repo.create(
        competition_id=competition.id,
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        kickoff_time_utc=kickoff,
        matchday=matchday,
        status=status,
        external_id=external_id,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGetByExternalId:
    async def test_found(
        self, match_repo, sample_competition, sample_season,
        sample_home_team, sample_away_team,
    ):
        await match_repo.create(
            competition_id=sample_competition.id,
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            kickoff_time_utc=KICKOFF,
            matchday=1,
            status=MatchStatus.SCHEDULED,
            external_id="extid.001",
        )
        result = await match_repo.get_by_external_id("extid.001")
        assert result is not None
        assert result.external_id == "extid.001"

    async def test_not_found(self, match_repo):
        result = await match_repo.get_by_external_id("does-not-exist")
        assert result is None


class TestGetByDate:
    async def test_within_range(
        self, match_repo, team_repo,
        sample_competition, sample_season,
        sample_home_team, sample_away_team,
    ):
        ko = datetime(2024, 3, 10, 15, 0, tzinfo=timezone.utc)
        team_c = await _make_team(team_repo, "Tottenham", "t.tottenham")
        team_d = await _make_team(team_repo, "Liverpool", "t.liverpool")
        await match_repo.create(
            competition_id=sample_competition.id,
            season_id=sample_season.id,
            home_team_id=team_c.id,
            away_team_id=team_d.id,
            kickoff_time_utc=ko,
            matchday=28,
            status=MatchStatus.SCHEDULED,
        )
        results = await match_repo.get_by_date(
            datetime(2024, 3, 9, tzinfo=timezone.utc),
            datetime(2024, 3, 11, tzinfo=timezone.utc),
        )
        # SQLite (aiosqlite) returns naive datetimes; strip tzinfo before comparing
        ko_naive = ko.replace(tzinfo=None)
        assert any(
            r.kickoff_time_utc.replace(tzinfo=None) == ko_naive
            for r in results
        )

    async def test_outside_range_excluded(
        self, match_repo, sample_competition, sample_season,
        sample_home_team, sample_away_team,
    ):
        results = await match_repo.get_by_date(
            datetime(2030, 1, 1, tzinfo=timezone.utc),
            datetime(2030, 12, 31, tzinfo=timezone.utc),
        )
        assert len(results) == 0


class TestGetByTeam:
    async def test_home_team_included(
        self, match_repo, sample_competition, sample_season,
        sample_home_team, sample_away_team,
    ):
        await _make_match(
            match_repo, sample_competition, sample_season,
            sample_home_team, sample_away_team,
            kickoff=datetime(2024, 2, 1, 15, 0, tzinfo=timezone.utc),
        )
        results = await match_repo.get_by_team(sample_home_team.id)
        assert len(results) >= 1
        assert all(
            r.home_team_id == sample_home_team.id or r.away_team_id == sample_home_team.id
            for r in results
        )

    async def test_away_team_included(
        self, match_repo, sample_competition, sample_season,
        sample_home_team, sample_away_team,
    ):
        results = await match_repo.get_by_team(sample_away_team.id)
        assert all(
            r.home_team_id == sample_away_team.id or r.away_team_id == sample_away_team.id
            for r in results
        )

    async def test_unrelated_team_not_included(
        self, match_repo, team_repo,
    ):
        stranger = await _make_team(team_repo, "Stranger FC", "t.stranger.99")
        results = await match_repo.get_by_team(stranger.id)
        assert len(results) == 0


class TestGetHeadToHead:
    async def test_h2h_both_directions(
        self, match_repo, team_repo,
        sample_competition, sample_season,
    ):
        team_a = await _make_team(team_repo, "Alpha United", "t.alpha_h2h")
        team_b = await _make_team(team_repo, "Beta City", "t.beta_h2h")
        ko1 = datetime(2024, 4, 1, 15, 0, tzinfo=timezone.utc)
        ko2 = datetime(2024, 5, 1, 15, 0, tzinfo=timezone.utc)
        await match_repo.create(
            competition_id=sample_competition.id, season_id=sample_season.id,
            home_team_id=team_a.id, away_team_id=team_b.id,
            kickoff_time_utc=ko1, matchday=30, status=MatchStatus.FINISHED,
        )
        await match_repo.create(
            competition_id=sample_competition.id, season_id=sample_season.id,
            home_team_id=team_b.id, away_team_id=team_a.id,
            kickoff_time_utc=ko2, matchday=38, status=MatchStatus.SCHEDULED,
        )
        results = await match_repo.get_head_to_head(team_a.id, team_b.id)
        assert len(results) == 2

    async def test_h2h_empty_for_unplayed(self, match_repo, team_repo):
        t1 = await _make_team(team_repo, "No History A", "t.nohistory_a")
        t2 = await _make_team(team_repo, "No History B", "t.nohistory_b")
        results = await match_repo.get_head_to_head(t1.id, t2.id)
        assert len(results) == 0


class TestGetUpcoming:
    async def test_scheduled_matches_returned(
        self, match_repo, team_repo,
        sample_competition, sample_season,
    ):
        team_e = await _make_team(team_repo, "Everton FC", "t.everton_up")
        team_f = await _make_team(team_repo, "Fulham FC", "t.fulham_up")
        future = datetime(2025, 8, 1, 15, 0, tzinfo=timezone.utc)
        m = await match_repo.create(
            competition_id=sample_competition.id,
            season_id=sample_season.id,
            home_team_id=team_e.id,
            away_team_id=team_f.id,
            kickoff_time_utc=future,
            matchday=1,
            status=MatchStatus.SCHEDULED,
        )
        results = await match_repo.get_upcoming(
            from_time=datetime(2025, 7, 31, tzinfo=timezone.utc)
        )
        assert any(r.id == m.id for r in results)

    async def test_finished_matches_excluded_from_upcoming(
        self, match_repo, team_repo,
        sample_competition, sample_season,
    ):
        team_g = await _make_team(team_repo, "Wolves FC", "t.wolves_up")
        team_h = await _make_team(team_repo, "Burnley FC", "t.burnley_up")
        past = datetime(2023, 12, 1, 15, 0, tzinfo=timezone.utc)
        m = await match_repo.create(
            competition_id=sample_competition.id,
            season_id=sample_season.id,
            home_team_id=team_g.id,
            away_team_id=team_h.id,
            kickoff_time_utc=past,
            matchday=15,
            status=MatchStatus.FINISHED,
        )
        results = await match_repo.get_upcoming()
        assert all(r.id != m.id for r in results)


class TestGetFinished:
    async def test_finished_status_returned(
        self, match_repo, team_repo,
        sample_competition, sample_season,
    ):
        team_i = await _make_team(team_repo, "Brentford", "t.brentford_fin")
        team_j = await _make_team(team_repo, "Nottm Forest", "t.forest_fin")
        ko = datetime(2023, 10, 14, 15, 0, tzinfo=timezone.utc)
        m = await match_repo.create(
            competition_id=sample_competition.id,
            season_id=sample_season.id,
            home_team_id=team_i.id,
            away_team_id=team_j.id,
            kickoff_time_utc=ko,
            matchday=8,
            status=MatchStatus.FINISHED,
        )
        results = await match_repo.get_finished()
        assert any(r.id == m.id for r in results)

    async def test_scheduled_excluded_from_finished(
        self, match_repo, sample_competition, sample_season,
        sample_home_team, sample_away_team,
    ):
        scheduled = await match_repo.create(
            competition_id=sample_competition.id,
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            kickoff_time_utc=datetime(2025, 9, 1, 15, 0, tzinfo=timezone.utc),
            matchday=1,
            status=MatchStatus.SCHEDULED,
        )
        results = await match_repo.get_finished()
        assert all(r.id != scheduled.id for r in results)
