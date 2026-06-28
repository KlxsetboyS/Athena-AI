"""TeamService – orchestrates TeamRepository.

Responsibilities
----------------
- Retrieve individual teams by ID or external ID.
- Search teams by name fragment.
- List teams participating in a given season.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from athena.db.models.team import Team
from athena.repositories.team import TeamRepository


class TeamService:
    """Service layer for Team domain operations.

    Args:
        repository: Injected :class:`TeamRepository`.
    """

    def __init__(self, repository: TeamRepository) -> None:
        self._repo = repository

    # ── Lookups ───────────────────────────────────────────────────────────────

    async def get_team(self, team_id: uuid.UUID) -> Team:
        """Return a team by primary key.

        Raises:
            LookupError: If no active team with *team_id* exists.
        """
        return await self._repo.get_by_id_or_raise(team_id)

    async def get_by_external_id(self, external_id: str) -> Team | None:
        """Return a team by provider external ID, or ``None``."""
        return await self._repo.get_by_external_id(external_id)

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_team(self, name_fragment: str) -> Sequence[Team]:
        """Case-insensitive partial search across team names.

        Args:
            name_fragment: Substring to match against ``Team.name``.

        Returns:
            Teams whose name contains *name_fragment*, ordered alphabetically.
        """
        return await self._repo.search_by_name(name_fragment)

    # ── Listings ──────────────────────────────────────────────────────────────

    async def list_teams_in_season(self, season_id: uuid.UUID) -> Sequence[Team]:
        """Return all teams registered for *season_id*."""
        return await self._repo.get_by_season(season_id)
