"""Register all models so SQLAlchemy Metadata is fully populated."""
from athena.db.models.competition import Competition
from athena.db.models.season import Season
from athena.db.models.team import Team
from athena.db.models.season_team import SeasonTeam
from athena.db.models.match import Match
from athena.db.models.match_result import MatchResult
from athena.db.models.bookmaker import Bookmaker
from athena.db.models.odds_snapshot import OddsSnapshot
from athena.db.models.odds_selection import OddsSelection

__all__ = [
    "Competition",
    "Season",
    "Team",
    "SeasonTeam",
    "Match",
    "MatchResult",
    "Bookmaker",
    "OddsSnapshot",
    "OddsSelection",
]
