"""API endpoint tests for all routers.

Each test:
1. Builds a fake domain object (MagicMock with correct field values).
2. Wires it into the mocked service.
3. Makes an HTTP request via the ASGI test client.
4. Asserts the status code and key response fields.
5. Asserts the correct service method was called.

No SQLite, no real HTTP.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock


from athena.db.enums import (
    CompetitionGender,
    CompetitionType,
    MatchStatus,
    OddsFormat,
    OddsMarket,
    SeasonStatus,
    SelectionType,
    TeamGender,
)

# ── Fake object factories ─────────────────────────────────────────────────────

_NOW = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)


def _fake_competition(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.name = kwargs.get("name", "Premier League")
    obj.country_code = kwargs.get("country_code", "ENG")
    obj.competition_type = kwargs.get("competition_type", CompetitionType.LEAGUE)
    obj.gender = kwargs.get("gender", CompetitionGender.MALE)
    obj.external_id = kwargs.get("external_id", "ENG.1")
    obj.created_at = _NOW
    obj.updated_at = _NOW
    return obj


def _fake_season(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.competition_id = kwargs.get("competition_id", uuid.uuid4())
    obj.year_start = kwargs.get("year_start", 2023)
    obj.year_end = kwargs.get("year_end", 2024)
    obj.label = kwargs.get("label", "2023/24")
    obj.status = kwargs.get("status", SeasonStatus.FINISHED)
    obj.created_at = _NOW
    obj.updated_at = _NOW
    return obj


def _fake_team(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.name = kwargs.get("name", "Arsenal FC")
    obj.short_name = kwargs.get("short_name", "Arsenal")
    obj.country_code = kwargs.get("country_code", "ENG")
    obj.gender = kwargs.get("gender", TeamGender.MALE)
    obj.external_id = kwargs.get("external_id", "t.arsenal")
    obj.created_at = _NOW
    obj.updated_at = _NOW
    return obj


def _fake_match(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.competition_id = kwargs.get("competition_id", uuid.uuid4())
    obj.season_id = kwargs.get("season_id", uuid.uuid4())
    obj.home_team_id = kwargs.get("home_team_id", uuid.uuid4())
    obj.away_team_id = kwargs.get("away_team_id", uuid.uuid4())
    obj.kickoff_time_utc = kwargs.get("kickoff_time_utc", _NOW)
    obj.venue = kwargs.get("venue", "Emirates Stadium")
    obj.matchday = kwargs.get("matchday", 21)
    obj.status = kwargs.get("status", MatchStatus.SCHEDULED)
    obj.external_id = kwargs.get("external_id", None)
    obj.created_at = _NOW
    obj.updated_at = _NOW
    return obj


def _fake_selection(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.selection_type = kwargs.get("selection_type", SelectionType.HOME)
    obj.label = kwargs.get("label", None)
    obj.decimal_odd = kwargs.get("decimal_odd", Decimal("1.95"))
    obj.line = kwargs.get("line", None)
    obj.is_suspended = kwargs.get("is_suspended", False)
    return obj


def _fake_snapshot(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.match_id = kwargs.get("match_id", uuid.uuid4())
    obj.bookmaker_id = kwargs.get("bookmaker_id", uuid.uuid4())
    obj.market = kwargs.get("market", OddsMarket.MATCH_WINNER)
    obj.odds_format = kwargs.get("odds_format", OddsFormat.DECIMAL)
    obj.captured_at = kwargs.get("captured_at", _NOW)
    obj.is_closing = kwargs.get("is_closing", False)
    obj.source = kwargs.get("source", "test_feed")
    obj.external_ref = kwargs.get("external_ref", None)
    obj.selections = kwargs.get("selections", [_fake_selection()])
    obj.created_at = _NOW
    obj.updated_at = _NOW
    return obj


def _fake_bookmaker(**kwargs) -> MagicMock:
    obj = MagicMock()
    obj.id = kwargs.get("id", uuid.uuid4())
    obj.name = kwargs.get("name", "Bet365")
    obj.slug = kwargs.get("slug", "bet365")
    obj.country_code = kwargs.get("country_code", "GBR")
    obj.is_exchange = kwargs.get("is_exchange", False)
    obj.is_active = kwargs.get("is_active", True)
    obj.external_id = kwargs.get("external_id", None)
    obj.created_at = _NOW
    obj.updated_at = _NOW
    return obj


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    async def test_health_returns_ok(self, api_client):
        client, *_ = api_client
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Competitions ──────────────────────────────────────────────────────────────

class TestCompetitionsEndpoints:
    async def test_list_competitions_empty(self, api_client):
        client, comp_svc, *_ = api_client
        comp_svc.list_competitions.return_value = []

        resp = await client.get("/competitions")

        assert resp.status_code == 200
        assert resp.json() == []
        comp_svc.list_competitions.assert_awaited_once()

    async def test_list_competitions_returns_items(self, api_client):
        client, comp_svc, *_ = api_client
        comp = _fake_competition()
        comp_svc.list_competitions.return_value = [comp]

        resp = await client.get("/competitions")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Premier League"
        assert data[0]["country_code"] == "ENG"

    async def test_list_competitions_type_filter_forwarded(self, api_client):
        client, comp_svc, *_ = api_client
        comp_svc.list_competitions.return_value = []

        await client.get("/competitions?competition_type=league")

        comp_svc.list_competitions.assert_awaited_once_with(
            competition_type=CompetitionType.LEAGUE,
            country_code=None,
            offset=0,
            limit=100,
        )

    async def test_get_competition_found(self, api_client):
        client, comp_svc, *_ = api_client
        comp = _fake_competition()
        comp_svc.get_competition.return_value = comp

        resp = await client.get(f"/competitions/{comp.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == str(comp.id)

    async def test_get_competition_not_found_returns_404(self, api_client):
        client, comp_svc, *_ = api_client
        comp_svc.get_competition.side_effect = LookupError("not found")

        resp = await client.get(f"/competitions/{uuid.uuid4()}")

        assert resp.status_code == 404

    async def test_list_competition_seasons(self, api_client):
        client, comp_svc, season_svc, *_ = api_client
        season = _fake_season()
        season_svc.list_seasons.return_value = [season]
        comp_id = uuid.uuid4()

        resp = await client.get(f"/competitions/{comp_id}/seasons")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        season_svc.list_seasons.assert_awaited_once_with(comp_id)


# ── Seasons ───────────────────────────────────────────────────────────────────

class TestSeasonsEndpoints:
    async def test_get_season_found(self, api_client):
        client, _, season_svc, *_ = api_client
        season = _fake_season()
        season_svc.get_season.return_value = season

        resp = await client.get(f"/seasons/{season.id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(season.id)
        assert body["year_start"] == 2023
        assert body["label"] == "2023/24"

    async def test_get_season_not_found(self, api_client):
        client, _, season_svc, *_ = api_client
        season_svc.get_season.side_effect = LookupError("not found")

        resp = await client.get(f"/seasons/{uuid.uuid4()}")

        assert resp.status_code == 404

    async def test_list_season_teams(self, api_client):
        client, _, season_svc, team_svc, *_ = api_client
        season = _fake_season()
        team = _fake_team()
        season_svc.get_season.return_value = season
        team_svc.list_teams_in_season.return_value = [team]

        resp = await client.get(f"/seasons/{season.id}/teams")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Arsenal FC"


# ── Teams ─────────────────────────────────────────────────────────────────────

class TestTeamsEndpoints:
    async def test_get_team_found(self, api_client):
        client, _, _, team_svc, *_ = api_client
        team = _fake_team()
        team_svc.get_team.return_value = team

        resp = await client.get(f"/teams/{team.id}")

        assert resp.status_code == 200
        assert resp.json()["name"] == "Arsenal FC"

    async def test_get_team_not_found(self, api_client):
        client, _, _, team_svc, *_ = api_client
        team_svc.get_team.side_effect = LookupError("not found")

        resp = await client.get(f"/teams/{uuid.uuid4()}")

        assert resp.status_code == 404

    async def test_search_teams(self, api_client):
        client, _, _, team_svc, *_ = api_client
        team = _fake_team(name="Arsenal FC")
        team_svc.search_team.return_value = [team]

        resp = await client.get("/teams?q=Arsenal")

        assert resp.status_code == 200
        assert resp.json()[0]["name"] == "Arsenal FC"
        team_svc.search_team.assert_awaited_once_with("Arsenal")

    async def test_search_teams_short_query_rejected(self, api_client):
        client, *_ = api_client
        resp = await client.get("/teams?q=A")
        assert resp.status_code == 422


# ── Matches ───────────────────────────────────────────────────────────────────

class TestMatchesEndpoints:
    async def test_get_match_found(self, api_client):
        client, _, _, _, match_svc, _ = api_client
        match = _fake_match()
        match_svc.get_match.return_value = match

        resp = await client.get(f"/matches/{match.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == str(match.id)
        assert resp.json()["status"] == "scheduled"

    async def test_get_match_not_found(self, api_client):
        client, _, _, _, match_svc, _ = api_client
        match_svc.get_match.side_effect = LookupError("not found")

        resp = await client.get(f"/matches/{uuid.uuid4()}")

        assert resp.status_code == 404

    async def test_get_upcoming_matches(self, api_client):
        client, _, _, _, match_svc, _ = api_client
        match = _fake_match()
        match_svc.get_upcoming_matches.return_value = [match]

        resp = await client.get("/matches/upcoming")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        match_svc.get_upcoming_matches.assert_awaited_once()

    async def test_get_finished_matches(self, api_client):
        client, _, _, _, match_svc, _ = api_client
        match = _fake_match(status=MatchStatus.FINISHED)
        match_svc.get_finished_matches.return_value = [match]

        resp = await client.get("/matches/finished")

        assert resp.status_code == 200
        match_svc.get_finished_matches.assert_awaited_once()

    async def test_upcoming_limit_param_forwarded(self, api_client):
        client, _, _, _, match_svc, _ = api_client
        match_svc.get_upcoming_matches.return_value = []

        await client.get("/matches/upcoming?limit=20")

        call_kwargs = match_svc.get_upcoming_matches.call_args.kwargs
        assert call_kwargs["limit"] == 20


# ── Odds ──────────────────────────────────────────────────────────────────────

class TestOddsEndpoints:
    async def test_list_bookmakers(self, api_client):
        client, _, _, _, _, odds_svc = api_client
        book = _fake_bookmaker()
        odds_svc.list_active_bookmakers.return_value = [book]

        resp = await client.get("/bookmakers")

        assert resp.status_code == 200
        assert resp.json()[0]["slug"] == "bet365"

    async def test_get_bookmaker_not_found(self, api_client):
        client, _, _, _, _, odds_svc = api_client
        odds_svc.get_bookmaker.side_effect = LookupError("not found")

        resp = await client.get(f"/bookmakers/{uuid.uuid4()}")

        assert resp.status_code == 404

    async def test_get_latest_odds(self, api_client):
        client, _, _, _, _, odds_svc = api_client
        snap = _fake_snapshot()
        odds_svc.get_latest_snapshot.return_value = snap
        match_id = uuid.uuid4()
        book_id = uuid.uuid4()

        resp = await client.get(
            f"/matches/{match_id}/odds/latest?bookmaker_id={book_id}"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["is_closing"] is False
        assert len(body["selections"]) == 1
        odds_svc.get_latest_snapshot.assert_awaited_once()

    async def test_get_latest_odds_not_found(self, api_client):
        client, _, _, _, _, odds_svc = api_client
        odds_svc.get_latest_snapshot.return_value = None

        resp = await client.get(
            f"/matches/{uuid.uuid4()}/odds/latest?bookmaker_id={uuid.uuid4()}"
        )

        assert resp.status_code == 404

    async def test_get_closing_odds(self, api_client):
        client, _, _, _, _, odds_svc = api_client
        snap = _fake_snapshot(is_closing=True)
        odds_svc.get_closing_snapshot.return_value = snap
        match_id = uuid.uuid4()
        book_id = uuid.uuid4()

        resp = await client.get(
            f"/matches/{match_id}/odds/closing?bookmaker_id={book_id}"
        )

        assert resp.status_code == 200
        assert resp.json()["is_closing"] is True

    async def test_get_odds_history(self, api_client):
        client, _, _, _, _, odds_svc = api_client
        snaps = [_fake_snapshot(), _fake_snapshot()]
        odds_svc.get_history.return_value = snaps
        match_id = uuid.uuid4()

        resp = await client.get(f"/matches/{match_id}/odds/history")

        assert resp.status_code == 200
        assert len(resp.json()) == 2
        odds_svc.get_history.assert_awaited_once()

    async def test_get_bookmaker_found(self, api_client):
        client, _, _, _, _, odds_svc = api_client
        book = _fake_bookmaker()
        odds_svc.get_bookmaker.return_value = book

        resp = await client.get(f"/bookmakers/{book.id}")

        assert resp.status_code == 200
        assert resp.json()["name"] == "Bet365"
        assert resp.json()["is_exchange"] is False
