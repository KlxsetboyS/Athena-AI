"""Athena AI – Repository Layer public API.

Usage::

    from athena.repositories import MatchRepository, OddsRepository

    async with async_session() as session:
        match_repo = MatchRepository(session)
        match = await match_repo.get_by_id(some_uuid)
"""
from athena.repositories.base import BaseRepository
from athena.repositories.competition import CompetitionRepository
from athena.repositories.season import SeasonRepository
from athena.repositories.team import TeamRepository
from athena.repositories.match import MatchRepository
from athena.repositories.odds import BookmakerRepository, OddsRepository

__all__ = [
    "BaseRepository",
    "CompetitionRepository",
    "SeasonRepository",
    "TeamRepository",
    "MatchRepository",
    "BookmakerRepository",
    "OddsRepository",
]
