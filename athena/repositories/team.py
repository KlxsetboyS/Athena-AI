"""TeamRepository – domain-specific queries for Team."""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from athena.db.models.season_team import SeasonTeam
from athena.db.models.team import Team
from athena.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for :class:`~athena.db.models.team.Team`."""

    model = Team

    async def get_by_external_id(self, external_id: str) -> Team | None:
        """Return a team by its external provider ID, or ``None``."""
        stmt = (
            select(Team)
            .where(Team.external_id == external_id)
            .where(Team.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_season(self, season_id: uuid.UUID) -> Sequence[Team]:
        """Return all teams participating in the given season."""
        stmt = (
            select(Team)
            .join(SeasonTeam, SeasonTeam.team_id == Team.id)
            .where(SeasonTeam.season_id == season_id)
            .where(Team.is_deleted.is_(False))
            .order_by(Team.name)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def search_by_name(self, name_fragment: str) -> Sequence[Team]:
        """Case-insensitive partial name search.

        Args:
            name_fragment: Substring to search for within team names.
        """
        stmt = (
            select(Team)
            .where(Team.name.ilike(f"%{name_fragment}%"))
            .where(Team.is_deleted.is_(False))
            .order_by(Team.name)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_with_matches(self, team_id: uuid.UUID) -> Team | None:
        """Return a team with home and away matches eagerly loaded."""
        stmt = (
            select(Team)
            .where(Team.id == team_id)
            .where(Team.is_deleted.is_(False))
            .options(
                selectinload(Team.home_matches),
                selectinload(Team.away_matches),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
