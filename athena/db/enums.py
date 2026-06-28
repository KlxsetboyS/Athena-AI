"""Domain enumerations for Athena AI."""
import enum


class CompetitionType(str, enum.Enum):
    LEAGUE = "league"
    CUP = "cup"
    INTERNATIONAL = "international"
    PLAYOFF = "playoff"
    FRIENDLY = "friendly"


class CompetitionGender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    MIXED = "mixed"


class SeasonStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    FINISHED = "finished"
    SUSPENDED = "suspended"


class TeamGender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    MIXED = "mixed"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    LIVE = "live"
    HALF_TIME = "half_time"
    FINISHED = "finished"
    ABANDONED = "abandoned"
    AWARDED = "awarded"


class ResultType(str, enum.Enum):
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"


class MatchResultStatus(str, enum.Enum):
    FINISHED = "finished"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"
    ABANDONED = "abandoned"
    AWARDED = "awarded"


# ── Sprint 1.5 ──────────────────────────────────────────────────────────────

class OddsMarket(str, enum.Enum):
    """Betting market type. Extensible for future markets."""
    MATCH_WINNER = "match_winner"   # 1X2
    OVER_UNDER = "over_under"       # reserved
    BTTS = "btts"                   # reserved
    ASIAN_HANDICAP = "asian_handicap"  # reserved
    DOUBLE_CHANCE = "double_chance"    # reserved


class SelectionType(str, enum.Enum):
    """1X2 selection labels (plus future generic labels)."""
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"
    OVER = "over"       # reserved
    UNDER = "under"     # reserved
    YES = "yes"         # reserved (BTTS)
    NO = "no"           # reserved (BTTS)


class OddsFormat(str, enum.Enum):
    DECIMAL = "decimal"
    FRACTIONAL = "fractional"
    AMERICAN = "american"
