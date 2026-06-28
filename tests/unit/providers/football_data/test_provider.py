"""Tests for FootballDataProvider — client is mocked, no HTTP."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from athena.providers.exceptions import ProviderParseError
from athena.providers.football_data.provider import FootballDataProvider

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "football_data"


def _load(filename: str) -> dict:
    return json.loads((FIXTURES / filename).read_text())


def _make_provider(return_value=None, side_effect=None) -> tuple[FootballDataProvider, AsyncMock]:
    mock_client = AsyncMock()
    if side_effect:
        mock_client.get.side_effect = side_effect
    else:
        mock_client.get.return_value = return_value or {}
    provider = FootballDataProvider(mock_client)
    return provider, mock_client


class TestGetCompetitions:
    async def test_calls_correct_endpoint(self):
        provider, client = _make_provider(_load("competitions.json"))
        await provider.get_competitions()
        client.get.assert_awaited_once_with("/competitions", params=None)

    async def test_returns_competition_dtos(self):
        provider, _ = _make_provider(_load("competitions.json"))
        dtos = await provider.get_competitions()
        assert len(dtos) == 2

    async def test_country_filter_forwarded(self):
        provider, client = _make_provider({"competitions": []})
        await provider.get_competitions(country_code="ENG")
        client.get.assert_awaited_once_with("/competitions", params={"areas": "ENG"})

    async def test_bad_response_raises_parse_error(self):
        provider, _ = _make_provider(None)

        # None response: None.get("competitions") → AttributeError → ProviderParseError
        provider._client.get.return_value = None
        with pytest.raises(ProviderParseError):
            await provider.get_competitions()


class TestGetMatches:
    async def test_calls_correct_endpoint(self):
        provider, client = _make_provider(_load("matches.json"))
        await provider.get_matches("fd.2021")
        client.get.assert_awaited_once_with(
            "/competitions/2021/matches", params=None
        )

    async def test_returns_match_dtos(self):
        provider, _ = _make_provider(_load("matches.json"))
        dtos = await provider.get_matches("fd.2021")
        assert len(dtos) == 2

    async def test_date_filters_forwarded(self):
        from datetime import date
        provider, client = _make_provider({"matches": []})
        await provider.get_matches(
            "fd.2021",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31),
        )
        call_params = client.get.call_args.kwargs["params"]
        assert call_params["dateFrom"] == "2024-01-01"
        assert call_params["dateTo"] == "2024-12-31"


class TestGetOdds:
    async def test_returns_empty_list(self):
        """football-data.org does not provide odds."""
        provider, client = _make_provider()
        result = await provider.get_odds("fd.419126")
        assert result == []
        client.get.assert_not_awaited()


class TestProviderName:
    def test_provider_name(self):
        provider, _ = _make_provider()
        assert provider.name == "football-data"
