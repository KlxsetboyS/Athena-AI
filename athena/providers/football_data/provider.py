"""FootballDataProvider — integration with football-data.org API v4.

API documentation: https://www.football-data.org/documentation/quickstart

Rate limits (free tier): 10 requests/minute.
Authentication: ``X-Auth-Token`` header.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import ClassVar

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
from athena.providers.football_data import mapper

logger = logging.getLogger(__name__)


class FootballDataProvider(BaseProvider):
    """Provider implementation for football-data.org.

    Covers competitions, seasons, teams, and match data.
    Does NOT cover odds (use OddsAPIProvider for that).

    Args:
        client: Configured ``ProviderClient`` with the FD base URL and
                ``X-Auth-Token`` header pre-set.
    """

    name: ClassVar[str] = "football-data"
    supported_leagues: ClassVar[frozenset[str]] = frozenset({
        "PL", "PD", "BL1", "SA", "FL1",  # top-5 European leagues
        "CL", "EL",                         # UEFA competitions
        "WC", "EC",                          # international
    })

    def __init__(self, client: ProviderClient) -> None:
        self._client = client

    # ── BaseProvider implementation ───────────────────────────────────────────

    async def get_competitions(
        self,
        *,
        country_code: str | None = None,
    ) -> list[CompetitionDTO]:
        """Return available competitions, optionally filtered by country."""
        params: dict = {}
        if country_code:
            params["areas"] = country_code

        try:
            raw = await self._client.get("/competitions", params=params or None)
            return mapper.map_competitions(raw)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderParseError(
                f"Unexpected competitions response: {exc}",
                provider=self.name,
            ) from exc

    async def get_seasons(
        self,
        competition_external_id: str,
    ) -> list[SeasonDTO]:
        """Return seasons for a competition.

        football-data.org nests the current season inside the competition
        object.  We return it as a single-item list for consistency.
        """
        fd_id = _strip_prefix(competition_external_id, "fd.")

        try:
            raw = await self._client.get(f"/competitions/{fd_id}")
            current_season = raw.get("currentSeason")
            if current_season is None:
                return []
            return [mapper.map_season(current_season, competition_external_id)]
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderParseError(
                f"Unexpected competition response: {exc}",
                provider=self.name,
            ) from exc

    async def get_teams(
        self,
        season_external_id: str,
    ) -> list[TeamDTO]:
        """Return teams for a season.

        The football-data.org teams endpoint is scoped to a competition
        (not a season), so we derive the competition ID from the season ID.
        Season external IDs follow the pattern ``fd.season.<season_id>``.
        This endpoint is only available on paid tiers for some competitions.
        """
        # season external_id = "fd.season.1564" → use competition endpoint
        # We request teams for the competition in the current season
        fd_season_id = _strip_prefix(season_external_id, "fd.season.")

        try:
            # The teams endpoint requires a competition code or ID
            # We use the competition endpoint with /teams suffix
            raw = await self._client.get(f"/competitions/{fd_season_id}/teams")
            teams_raw = raw.get("teams", [])
            return [mapper.map_team(t) for t in teams_raw]
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderParseError(
                f"Unexpected teams response: {exc}",
                provider=self.name,
            ) from exc

    async def get_matches(
        self,
        competition_external_id: str,
        *,
        season_external_id: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MatchDTO]:
        """Return matches for a competition with optional filters."""
        fd_id = _strip_prefix(competition_external_id, "fd.")
        params: dict = {}

        if from_date:
            params["dateFrom"] = from_date.isoformat()
        if to_date:
            params["dateTo"] = to_date.isoformat()

        try:
            raw = await self._client.get(
                f"/competitions/{fd_id}/matches",
                params=params or None,
            )
            return mapper.map_matches(raw)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderParseError(
                f"Unexpected matches response: {exc}",
                provider=self.name,
            ) from exc

    async def get_odds(
        self,
        match_external_id: str,
        *,
        markets: list[OddsMarket] | None = None,
    ) -> list[OddsSnapshotDTO]:
        """football-data.org does not provide odds on the free tier.

        Returns an empty list.  Use OddsAPIProvider for odds data.
        """
        logger.debug(
            "football-data does not provide odds; returning empty list",
            extra={"match_external_id": match_external_id},
        )
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_prefix(value: str, prefix: str) -> str:
    """Remove a known prefix from an external ID string."""
    if value.startswith(prefix):
        return value[len(prefix):]
    return value
