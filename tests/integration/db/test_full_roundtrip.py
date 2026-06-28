"""Integration test – full entity creation and retrieval roundtrip.

This test creates the full object graph that a real ingestion pipeline would
produce:
    Competition → Season → Team (x2) → Match → OddsSnapshot → OddsSelections

and then verifies reads across all repositories, ensuring FK constraints, eager
loading, and soft-delete mechanics all work end-to-end in a single transaction.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

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
from athena.db.models.bookmaker import Bookmaker
from athena.db.models.odds_selection import OddsSelection
from athena.db.models.odds_snapshot import OddsSnapshot
from athena.repositories.competition import CompetitionRepository
from athena.repositories.match import MatchRepository
from athena.repositories.odds import BookmakerRepository, OddsRepository
from athena.repositories.season import SeasonRepository
from athena.repositories.team import TeamRepository


# ── Full object-graph fixture ─────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def full_graph(db_session):
    """Build a complete object graph and return all entities as a dict."""
    comp_repo = CompetitionRepository(db_session)
    season_repo = SeasonRepository(db_session)
    team_repo = TeamRepository(db_session)
    match_repo = MatchRepository(db_session)
    book_repo = BookmakerRepository(db_session)
    odds_repo = OddsRepository(db_session)

    competition = await comp_repo.create(
        name="Serie A",
        country_code="ITA",
        competition_type=CompetitionType.LEAGUE,
        gender=CompetitionGender.MALE,
        external_id="ITA.1",
    )

    season = await season_repo.create(
        competition_id=competition.id,
        label="2023/24",
        year_start=2023,
        year_end=2024,
        status=SeasonStatus.FINISHED,
    )

    home_team = await team_repo.create(
        name="Inter Milan",
        short_name="Inter",
        country_code="ITA",
        gender=TeamGender.MALE,
        external_id="t.inter",
    )
    away_team = await team_repo.create(
        name="AC Milan",
        short_name="AC Milan",
        country_code="ITA",
        gender=TeamGender.MALE,
        external_id="t.acmilan",
    )

    match = await match_repo.create(
        competition_id=competition.id,
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        kickoff_time_utc=datetime(2024, 2, 4, 18, 0, tzinfo=timezone.utc),
        venue="San Siro",
        matchday=23,
        status=MatchStatus.FINISHED,
        external_id="m.ita1.240204.inter_acm",
    )

    bookmaker = await book_repo.create(
        name="Betfair",
        slug="betfair",
        is_exchange=True,
        is_active=True,
    )

    # Two snapshots – pre-match and closing line
    snap_pre = OddsSnapshot(
        match_id=match.id,
        bookmaker_id=bookmaker.id,
        market=OddsMarket.MATCH_WINNER,
        odds_format=OddsFormat.DECIMAL,
        captured_at=datetime(2024, 2, 3, 12, 0, tzinfo=timezone.utc),
        is_closing=False,
        source="betfair_api",
        external_ref="bf.pre.inter_acm",
    )
    snap_close = OddsSnapshot(
        match_id=match.id,
        bookmaker_id=bookmaker.id,
        market=OddsMarket.MATCH_WINNER,
        odds_format=OddsFormat.DECIMAL,
        captured_at=datetime(2024, 2, 4, 17, 55, tzinfo=timezone.utc),
        is_closing=True,
        source="betfair_api",
        external_ref="bf.close.inter_acm",
    )
    db_session.add_all([snap_pre, snap_close])
    await db_session.flush()

    # Selections for closing snapshot
    for sel_type, odd in [
        (SelectionType.HOME, Decimal("1.95")),
        (SelectionType.DRAW, Decimal("3.60")),
        (SelectionType.AWAY, Decimal("4.20")),
    ]:
        db_session.add(OddsSelection(
            snapshot_id=snap_close.id,
            selection_type=sel_type,
            decimal_odd=odd,
        ))
    await db_session.flush()

    return {
        "competition": competition,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
        "match": match,
        "bookmaker": bookmaker,
        "snap_pre": snap_pre,
        "snap_close": snap_close,
        "repos": {
            "comp": comp_repo,
            "season": season_repo,
            "team": team_repo,
            "match": match_repo,
            "book": book_repo,
            "odds": odds_repo,
        },
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestFullRoundtrip:
    async def test_competition_retrievable(self, full_graph):
        repos = full_graph["repos"]
        comp = await repos["comp"].get_by_id(full_graph["competition"].id)
        assert comp is not None
        assert comp.name == "Serie A"
        assert comp.country_code == "ITA"

    async def test_competition_get_by_external_id(self, full_graph):
        repos = full_graph["repos"]
        comp = await repos["comp"].get_by_external_id("ITA.1")
        assert comp is not None

    async def test_season_linked_to_competition(self, full_graph):
        repos = full_graph["repos"]
        season = await repos["season"].get_by_id(full_graph["season"].id)
        assert season is not None
        assert season.competition_id == full_graph["competition"].id

    async def test_teams_retrievable(self, full_graph):
        repos = full_graph["repos"]
        home = await repos["team"].get_by_id(full_graph["home_team"].id)
        away = await repos["team"].get_by_id(full_graph["away_team"].id)
        assert home.name == "Inter Milan"
        assert away.name == "AC Milan"

    async def test_match_external_id_lookup(self, full_graph):
        repos = full_graph["repos"]
        match = await repos["match"].get_by_external_id("m.ita1.240204.inter_acm")
        assert match is not None
        assert match.venue == "San Siro"

    async def test_match_get_with_odds_eager_loads_snapshots(self, full_graph):
        repos = full_graph["repos"]
        match = await repos["match"].get_with_odds(full_graph["match"].id)
        assert match is not None
        assert len(match.odds_snapshots) == 2

    async def test_closing_snapshot_retrieved(self, full_graph):
        repos = full_graph["repos"]
        closing = await repos["odds"].get_closing_snapshot(
            full_graph["match"].id,
            full_graph["bookmaker"].id,
        )
        assert closing is not None
        assert closing.is_closing is True
        assert closing.external_ref == "bf.close.inter_acm"

    async def test_closing_snapshot_has_three_selections(self, full_graph):
        repos = full_graph["repos"]
        snap = full_graph["snap_close"]
        selections = await repos["odds"].get_selections(snap.id)
        assert len(selections) == 3

    async def test_implied_probability_sum_near_one(self, full_graph):
        """Margin check: 1/1.95 + 1/3.60 + 1/4.20 ≈ 1.05 (bookmaker margin ~5%)."""
        repos = full_graph["repos"]
        snap = full_graph["snap_close"]
        selections = await repos["odds"].get_selections(snap.id)
        total_prob = sum(1 / float(s.decimal_odd) for s in selections)
        assert 1.0 < total_prob < 1.20  # reasonable overround range

    async def test_odds_history_both_snapshots(self, full_graph):
        repos = full_graph["repos"]
        history = await repos["odds"].get_history(
            full_graph["match"].id,
            bookmaker_id=full_graph["bookmaker"].id,
        )
        assert len(history) == 2
        # oldest first
        assert history[0].captured_at < history[1].captured_at

    async def test_match_in_finished_query(self, full_graph):
        repos = full_graph["repos"]
        finished = await repos["match"].get_finished(
            competition_id=full_graph["competition"].id,
        )
        assert any(m.id == full_graph["match"].id for m in finished)

    async def test_team_search_by_name_fragment(self, full_graph):
        repos = full_graph["repos"]
        results = await repos["team"].search_by_name("Milan")
        names = [t.name for t in results]
        assert "AC Milan" in names

    async def test_bookmaker_active_includes_betfair(self, full_graph):
        repos = full_graph["repos"]
        active = await repos["book"].get_active()
        slugs = [b.slug for b in active]
        assert "betfair" in slugs

    async def test_external_ref_deduplication(self, full_graph):
        repos = full_graph["repos"]
        exists = await repos["odds"].snapshot_exists("bf.pre.inter_acm")
        assert exists is True

    async def test_soft_delete_hides_competition(self, full_graph):
        repos = full_graph["repos"]
        comp = full_graph["competition"]
        await repos["comp"].soft_delete(comp)
        result = await repos["comp"].get_by_id(comp.id)
        assert result is None

    async def test_restore_makes_competition_visible_again(self, full_graph):
        repos = full_graph["repos"]
        comp = full_graph["competition"]
        # comp was soft-deleted in previous test — restore it
        await repos["comp"].restore(comp)
        result = await repos["comp"].get_by_id(comp.id)
        assert result is not None
