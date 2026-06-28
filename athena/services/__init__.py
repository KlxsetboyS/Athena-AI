"""Athena AI – Service Layer public API.

Usage::

    from athena.services import MatchService, OddsService

    # Repositories must be constructed with an active AsyncSession:
    match_service = MatchService(MatchRepository(session))
    odds_service  = OddsService(OddsRepository(session), BookmakerRepository(session))
"""
from athena.services.competition_service import CompetitionService
from athena.services.season_service import SeasonService
from athena.services.team_service import TeamService
from athena.services.match_service import MatchService
from athena.services.odds_service import OddsService

__all__ = [
    "CompetitionService",
    "SeasonService",
    "TeamService",
    "MatchService",
    "OddsService",
]
