"""Match entity – structural core of Athena AI."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from athena.db.model import BaseModel
from athena.db.enums import MatchStatus

if TYPE_CHECKING:
    from athena.db.models.competition import Competition
    from athena.db.models.season import Season
    from athena.db.models.team import Team
    from athena.db.models.match_result import MatchResult
    from athena.db.models.odds_snapshot import OddsSnapshot


class Match(BaseModel):
    """A single football match."""
    __tablename__ = "match"
    __table_args__ = (
        CheckConstraint("home_team_id != away_team_id", name="teams_must_differ"),
        CheckConstraint("matchday >= 1", name="matchday_positive"),
        UniqueConstraint("season_id", "home_team_id", "away_team_id", "kickoff_time_utc", name="uq_match_unique"),
    )

    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competition.id"), nullable=False)
    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("season.id"), nullable=False)
    home_team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("team.id"), nullable=False)
    away_team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("team.id"), nullable=False)
    kickoff_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue: Mapped[str | None] = mapped_column(String(120), nullable=True)
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[MatchStatus] = mapped_column(default=MatchStatus.SCHEDULED, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    competition: Mapped["Competition"] = relationship("Competition", back_populates="matches")
    season: Mapped["Season"] = relationship("Season", back_populates="matches")
    home_team: Mapped["Team"] = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped["Team"] = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    result: Mapped["MatchResult | None"] = relationship("MatchResult", back_populates="match", uselist=False)
    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship("OddsSnapshot", back_populates="match")

    def __repr__(self) -> str:
        return f"<Match id={self.id} home={self.home_team_id} away={self.away_team_id} kickoff={self.kickoff_time_utc}>"
