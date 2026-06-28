"""OddsAPIProvider — integration with the-odds-api.com v4 API.

API documentation: https://the-odds-api.com/liveodds-api/

Rate limits (free tier): 500 requests/month.
Authentication: ``apiKey`` query parameter.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, ClassVar

from athena.db.enums import OddsMarket
from athena.providers.base import BaseProvider
from athena.providers.client import ProviderClient
from athena.providers.exceptions import ProviderParseError
from athena.providers.models import (
    CompetitionDTO,
    MatchDTO,
    OddsSnapshotDTO,
    SeasonDTO,
    TeamDTO,
)
from athena.providers.odds_api import mapper

logger = logging.getLogger(__name__)

# Mapping from our OddsMarket enum to the-odds-api.com market keys
_MARKET_KEYS: dict[OddsMarket, str] = {
    OddsMarket.MATCH_WINNER: "h2h",
    OddsMarket.OVER_UNDER: "totals",
    OddsMarket.BTTS: "btts",
}

# Sport key for football (soccer)
_DEFAULT_SPORT = "soccer_epl"


class OddsAPIProvider(BaseProvider):
    """Provider implementation for the-odds-api.com.

    Covers odds data only.  Competition, season, and team data should
    come from FootballDataProvider or another structural provider.

    Args:
        client:    Configured ``ProviderClient`` with the-odds-api.com base URL.
        api_key:   API key passed as a query parameter on every request.
        sport_key: Sport identifier (default: ``"soccer_epl"``).
    """

    name: ClassVar[str] = "odds-api"
    supported_leagues: ClassVar[frozenset[str]] = frozenset({
        "soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga",
        "soccer_italy_serie_a", "soccer_france_ligue_one",
    })

    def __init__(
        self,
        client: ProviderClient,
        api_key: str,
        sport_key: str = _DEFAULT_SPORT,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._sport_key = sport_key

    def _auth_params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return base query params including the API key."""
        params = {"apiKey": self._api_key}
        if extra:
            params.update(extra)
        return params

    # ── BaseProvider implementation ───────────────────────────────────────────

    async def get_competitions(
        self,
        *,
        country_code: str | None = None,
    ) -> list[CompetitionDTO]:
        """OddsAPI does not expose competition metadata.  Returns empty list."""
        logger.debug("OddsAPIProvider.get_competitions: not supported, returning []")
        return []

    async def get_seasons(
        self,
        competition_external_id: str,
    ) -> list[SeasonDTO]:
        """OddsAPI does not expose season data.  Returns empty list."""
        logger.debug("OddsAPIProvider.get_seasons: not supported, returning []")
        return []

    async def get_teams(
        self,
        season_external_id: str,
    ) -> list[TeamDTO]:
        """OddsAPI does not expose team data.  Returns empty list."""
        logger.debug("OddsAPIProvider.get_teams: not supported, returning []")
        return []

    async def get_matches(
        self,
        competition_external_id: str,
        *,
        season_external_id: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MatchDTO]:
        """OddsAPI does not expose match schedules.  Returns empty list."""
        logger.debug("OddsAPIProvider.get_matches: not supported, returning []")
        return []

    async def get_odds(
        self,
        match_external_id: str,
        *,
        markets: list[OddsMarket] | None = None,
    ) -> list[OddsSnapshotDTO]:
        """Return odds snapshots for a sport/event.

        The-odds-api.com returns odds for a full sport (e.g. all EPL matches),
        not per individual match.  We fetch the full sport and return all
        snapshots — the caller (IngestionService) filters by match.

        Args:
            match_external_id: Not used for filtering at API level; included
                               for interface compatibility.
            markets:           Markets to request; defaults to h2h (1X2).
        """
        market_keys = [
            _MARKET_KEYS[m]
            for m in (markets or [OddsMarket.MATCH_WINNER])
            if m in _MARKET_KEYS
        ]
        if not market_keys:
            return []

        params = self._auth_params({
            "regions": "eu",
            "markets": ",".join(market_keys),
            "oddsFormat": "decimal",
        })

        try:
            raw = await self._client.get(
                f"/sports/{self._sport_key}/odds",
                params=params,
            )
            if not isinstance(raw, list):
                raise ProviderParseError(
                    "Expected list from odds endpoint",
                    provider=self.name,
                )
            return mapper.map_odds_response(raw)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderParseError(
                f"Unexpected odds response: {exc}",
                provider=self.name,
            ) from exc

    async def health_check(self) -> bool:
        """Lightweight health check using the sports list endpoint."""
        try:
            await self._client.get(
                "/sports",
                params=self._auth_params({"all": "false"}),
            )
            return True
        except Exception:  # noqa: BLE001
            return False
