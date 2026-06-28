"""CompetitionRepository – domain-specific queries for Competition."""
from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from athena.db.enums import CompetitionType
from athena.db.models.competition import Competition
from athena.repositories.base import BaseRepository


class CompetitionRepository(BaseRepository[Competition]):
    """Repository for :class:`~athena.db.models.competition.Competition`."""

    model = Competition

    async def get_by_external_id(self, external_id: str) -> Competition | None:
        """Return the competition matching *external_id*, or ``None``."""
        stmt = (
            select(Competition)
            .where(Competition.external_id == external_id)
            .where(Competition.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_type(
        self,
        competition_type: CompetitionType,
        *,
        country_code: str | None = None,
    ) -> Sequence[Competition]:
        """Return all competitions of a given type, optionally filtered by country.

        Args:
            competition_type: League, cup, international, etc.
            country_code:     ISO 3166-1 alpha-3 country filter (optional).
        """
        stmt = (
            select(Competition)
            .where(Competition.competition_type == competition_type)
            .where(Competition.is_deleted.is_(False))
        )
        if country_code is not None:
            stmt = stmt.where(Competition.country_code == country_code)
        stmt = stmt.order_by(Competition.name)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_country(self, country_code: str) -> Sequence[Competition]:
        """Return all active competitions for a given country code."""
        stmt = (
            select(Competition)
            .where(Competition.country_code == country_code)
            .where(Competition.is_deleted.is_(False))
            .order_by(Competition.name)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
