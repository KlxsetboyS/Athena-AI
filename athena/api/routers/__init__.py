"""Athena API routers."""
from athena.api.routers.competitions import router as competitions_router
from athena.api.routers.seasons import router as seasons_router
from athena.api.routers.teams import router as teams_router
from athena.api.routers.matches import router as matches_router
from athena.api.routers.odds import bookmaker_router, match_odds_router

__all__ = [
    "competitions_router",
    "seasons_router",
    "teams_router",
    "matches_router",
    "bookmaker_router",
    "match_odds_router",
]
