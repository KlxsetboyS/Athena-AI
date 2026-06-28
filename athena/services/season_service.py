"""SeasonService – orchestrates SeasonRepository.

Responsibilities
----------------
- Retrieve individual seasons by ID.
- List seasons for a competition.
- Retrieve the current (active) season for a competition.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from athena.db.models.season import Season
from athena.repositories.season import SeasonRepository


class SeasonService:
    """Service layer for Season domain operations.

    Args:
        repository: Injected :class:`SeasonRepository`.
    """

    def __init__(self, repository: SeasonRepository) -> None:
        self._repo = repository

    # ── Lookups ───────────────────────────────────────────────────────────────

    async def get_season(self, season_id: uuid.UUID) -> Season:
        """Return a season by primary key.

        Raises:
            LookupError: If no active season with *season_id* exists.
        """
        return await self._repo.get_by_id_or_raise(season_id)

    async def get_current_season(self, competition_id: uuid.UUID) -> Season | None:
        """Return the active season for *competition_id*, or ``None``."""
        return await self._repo.get_current(competition_id)

    # ── Listings ──────────────────────────────────────────────────────────────

    async def list_seasons(self, competition_id: uuid.UUID) -> Sequence[Season]:
        """Return all seasons for a competition, newest first."""
        return await self._repo.get_by_competition(competition_id)

    async def list_active_seasons(
        self, competition_id: uuid.UUID | None = None
    ) -> Sequence[Season]:
        """Return all currently active seasons.

        Args:
            competition_id: Optionally restrict to a single competition.
        """
        return await self._repo.get_active(competition_id)
