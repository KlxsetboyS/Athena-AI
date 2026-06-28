"""Tests for OddsAPIProvider — client is mocked, no HTTP."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock


from athena.db.enums import OddsMarket
from athena.providers.odds_api.provider import OddsAPIProvider

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "odds_api"


def _load(filename: str) -> list:
    return json.loads((FIXTURES / filename).read_text())


def _make_provider(return_value=None) -> tuple[OddsAPIProvider, AsyncMock]:
    mock_client = AsyncMock()
    mock_client.get.return_value = return_value if return_value is not None else []
    provider = OddsAPIProvider(mock_client, api_key="test-key", sport_key="soccer_epl")
    return provider, mock_client


class TestUnsupportedMethods:
    async def test_get_competitions_returns_empty(self):
        provider, client = _make_provider()
        result = await provider.get_competitions()
        assert result == []
        client.get.assert_not_awaited()

    async def test_get_seasons_returns_empty(self):
        provider, client = _make_provider()
        result = await provider.get_seasons("comp.1")
        assert result == []
        client.get.assert_not_awaited()

    async def test_get_teams_returns_empty(self):
        provider, client = _make_provider()
        result = await provider.get_teams("season.1")
        assert result == []
        client.get.assert_not_awaited()

    async def test_get_matches_returns_empty(self):
        provider, client = _make_provider()
        result = await provider.get_matches("comp.1")
        assert result == []
        client.get.assert_not_awaited()


class TestGetOdds:
    async def test_calls_correct_endpoint(self):
        provider, client = _make_provider(_load("odds.json"))
        await provider.get_odds("oddsapi.abc123")
        client.get.assert_awaited_once()
        call_path = client.get.call_args.args[0]
        assert call_path == "/sports/soccer_epl/odds"

    async def test_api_key_in_params(self):
        provider, client = _make_provider(_load("odds.json"))
        await provider.get_odds("oddsapi.abc123")
        params = client.get.call_args.kwargs["params"]
        assert params["apiKey"] == "test-key"

    async def test_default_market_is_h2h(self):
        provider, client = _make_provider(_load("odds.json"))
        await provider.get_odds("oddsapi.abc123")
        params = client.get.call_args.kwargs["params"]
        assert "h2h" in params["markets"]

    async def test_returns_snapshot_dtos(self):
        provider, _ = _make_provider(_load("odds.json"))
        dtos = await provider.get_odds("oddsapi.abc123")
        assert len(dtos) == 2  # 2 bookmakers in fixture

    async def test_custom_market_forwarded(self):
        provider, client = _make_provider([])
        await provider.get_odds("oddsapi.abc123", markets=[OddsMarket.OVER_UNDER])
        params = client.get.call_args.kwargs["params"]
        assert "totals" in params["markets"]


class TestProviderName:
    def test_provider_name(self):
        provider, _ = _make_provider()
        assert provider.name == "odds-api"
