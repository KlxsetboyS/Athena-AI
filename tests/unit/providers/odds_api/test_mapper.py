"""Tests for odds_api mapper — pure functions, no I/O."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from athena.db.enums import OddsMarket, SelectionType
from athena.providers.odds_api.mapper import map_odds_event, map_odds_response
from athena.providers.models import OddsSnapshotDTO

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "odds_api"


def _load(filename: str) -> list:
    return json.loads((FIXTURES / filename).read_text())


def _event() -> dict:
    """Minimal valid event dict."""
    return {
        "id": "abc123",
        "sport_key": "soccer_epl",
        "commence_time": "2024-08-16T19:00:00Z",
        "home_team": "Arsenal",
        "away_team": "Wolves",
        "bookmakers": [
            {
                "key": "bet365",
                "title": "Bet365",
                "last_update": "2024-08-16T18:30:00Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2024-08-16T18:30:00Z",
                        "outcomes": [
                            {"name": "Arsenal", "price": 1.65},
                            {"name": "Wolves", "price": 5.50},
                            {"name": "Draw", "price": 4.00},
                        ],
                    }
                ],
            }
        ],
    }


class TestMapOddsEvent:
    def test_returns_one_snapshot_per_bookmaker_per_market(self):
        dtos = map_odds_event(_event())
        assert len(dtos) == 1  # 1 bookmaker × 1 market

    def test_snapshot_match_external_id_prefixed(self):
        dtos = map_odds_event(_event())
        assert dtos[0].match_external_id == "oddsapi.abc123"

    def test_snapshot_bookmaker_slug(self):
        dtos = map_odds_event(_event())
        assert dtos[0].bookmaker_slug == "bet365"

    def test_snapshot_market_is_match_winner(self):
        dtos = map_odds_event(_event())
        assert dtos[0].market == OddsMarket.MATCH_WINNER

    def test_snapshot_has_three_selections(self):
        dtos = map_odds_event(_event())
        assert len(dtos[0].selections) == 3

    def test_home_selection_mapped_correctly(self):
        dtos = map_odds_event(_event())
        home_sel = next(s for s in dtos[0].selections if s.selection_type == SelectionType.HOME)
        assert home_sel.decimal_odd == Decimal("1.65")

    def test_away_selection_mapped_correctly(self):
        dtos = map_odds_event(_event())
        away_sel = next(s for s in dtos[0].selections if s.selection_type == SelectionType.AWAY)
        assert away_sel.decimal_odd == Decimal("5.50")

    def test_draw_selection_mapped_correctly(self):
        dtos = map_odds_event(_event())
        draw_sel = next(s for s in dtos[0].selections if s.selection_type == SelectionType.DRAW)
        assert draw_sel.decimal_odd == Decimal("4.00")

    def test_selections_are_immutable(self):
        dtos = map_odds_event(_event())
        with pytest.raises((AttributeError, TypeError)):
            dtos[0].selections[0].decimal_odd = Decimal("99")  # type: ignore

    def test_unknown_market_key_skipped(self):
        event = _event()
        event["bookmakers"][0]["markets"][0]["key"] = "unknown_market"
        dtos = map_odds_event(event)
        assert len(dtos) == 0

    def test_no_bookmakers_returns_empty(self):
        event = _event()
        event["bookmakers"] = []
        assert map_odds_event(event) == []


class TestMapOddsResponseFromFixture:
    def test_fixture_maps_two_bookmakers(self):
        raw = _load("odds.json")
        dtos = map_odds_response(raw)
        # 1 event × 2 bookmakers × 1 market = 2 snapshots
        assert len(dtos) == 2

    def test_fixture_external_refs_unique(self):
        raw = _load("odds.json")
        dtos = map_odds_response(raw)
        refs = [dto.external_ref for dto in dtos]
        assert len(refs) == len(set(refs))

    def test_fixture_all_snapshots_have_selections(self):
        raw = _load("odds.json")
        dtos = map_odds_response(raw)
        assert all(len(dto.selections) > 0 for dto in dtos)

    def test_empty_list_returns_empty(self):
        assert map_odds_response([]) == []
