"""SeasonRepository – domain-specific queries for Season."""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from athena.db.enums import SeasonStatus
from athena.db.models.season import Season
from athena.repositories.base import BaseRepository


class SeasonRepository(BaseRepository[Season]):
    """Repository for :class:`~athena.db.models.season.Season`."""

    model = Season

    async def get_by_competition(
        self,
        competition_id: uuid.UUID,
    ) -> Sequence[Season]:
        """Return all seasons for a competition, newest first."""
        stmt = (
            select(Season)
            .where(Season.competition_id == competition_id)
            .where(Season.is_deleted.is_(False))
            .order_by(Season.year_start.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_active(
        self,
        competition_id: uuid.UUID | None = None,
    ) -> Sequence[Season]:
        """Return all currently active seasons.

        Args:
            competition_id: Optionally scope to a single competition.
        """
        stmt = (
            select(Season)
            .where(Season.status == SeasonStatus.ACTIVE)
            .where(Season.is_deleted.is_(False))
        )
        if competition_id is not None:
            stmt = stmt.where(Season.competition_id == competition_id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_current(self, competition_id: uuid.UUID) -> Season | None:
        """Return the most recent active season for a competition, or ``None``."""
        stmt = (
            select(Season)
            .where(Season.competition_id == competition_id)
            .where(Season.status == SeasonStatus.ACTIVE)
            .where(Season.is_deleted.is_(False))
            .order_by(Season.year_start.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_teams(self, season_id: uuid.UUID) -> Season | None:
        """Return a season with its associated teams eagerly loaded."""
        stmt = (
            select(Season)
            .where(Season.id == season_id)
            .where(Season.is_deleted.is_(False))
            .options(selectinload(Season.season_teams))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
