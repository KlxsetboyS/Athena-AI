"""Abstract base class for all data providers.

Every concrete provider (FootballDataProvider, OddsAPIProvider, …) must
subclass ``BaseProvider`` and implement all abstract methods.

Design constraints
------------------
- ``BaseProvider`` has no I/O of its own — it delegates all HTTP to the
  ``ProviderClient`` it receives at construction time.
- ``BaseProvider`` knows nothing about SQLAlchemy or repositories.
- Return types are always DTOs (``athena.providers.models``), never ORM
  objects.

Adding a new provider
---------------------
1. Create ``athena/providers/<name>/provider.py``.
2. Subclass ``BaseProvider``.
3. Set ``name`` and ``supported_leagues`` class variables.
4. Implement all abstract methods.
5. Register the new provider in ``athena/api/lifespan.py`` if its API key
   is present in Settings.

No existing code needs to change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import ClassVar

from athena.db.enums import OddsMarket
from athena.providers.models import (
    CompetitionDTO,
    MatchDTO,
    OddsSnapshotDTO,
    SeasonDTO,
    TeamDTO,
)


class BaseProvider(ABC):
    """Contract that every external data provider must fulfil.

    Class attributes
    ----------------
    name
        Machine-readable identifier, e.g. ``"football-data"``.
        Must be unique across all registered providers.
    supported_leagues
        Frozenset of league/competition codes this provider covers.
        Used for routing in future multi-provider scenarios.
    """

    name: ClassVar[str]
    supported_leagues: ClassVar[frozenset[str]] = frozenset()

    # ── Abstract methods ──────────────────────────────────────────────────────

    @abstractmethod
    async def get_competitions(
        self,
        *,
        country_code: str | None = None,
    ) -> list[CompetitionDTO]:
        """Return competitions, optionally filtered by country.

        Args:
            country_code: ISO 3166-1 alpha-3 country code filter (optional).
        """

    @abstractmethod
    async def get_seasons(
        self,
        competition_external_id: str,
    ) -> list[SeasonDTO]:
        """Return all seasons for the given competition external ID."""

    @abstractmethod
    async def get_teams(
        self,
        season_external_id: str,
    ) -> list[TeamDTO]:
        """Return all teams participating in the given season."""

    @abstractmethod
    async def get_matches(
        self,
        competition_external_id: str,
        *,
        season_external_id: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MatchDTO]:
        """Return matches for a competition, with optional filters.

        Args:
            competition_external_id: Provider-side competition identifier.
            season_external_id:      Restrict to one season (optional).
            from_date:               Earliest kickoff date (inclusive, optional).
            to_date:                 Latest kickoff date (inclusive, optional).
        """

    @abstractmethod
    async def get_odds(
        self,
        match_external_id: str,
        *,
        markets: list[OddsMarket] | None = None,
    ) -> list[OddsSnapshotDTO]:
        """Return odds snapshots for a match.

        Args:
            match_external_id: Provider-side match identifier.
            markets:           Betting markets to retrieve (optional; defaults
                               to all available markets for the provider).
        """

    # ── Default implementations ───────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Return True if the provider API is reachable.

        Default implementation calls ``get_competitions()`` with no filters.
        Concrete providers may override with a cheaper endpoint.
        """
        try:
            await self.get_competitions()
            return True
        except Exception:  # noqa: BLE001
            return False
