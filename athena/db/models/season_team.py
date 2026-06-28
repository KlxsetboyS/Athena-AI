"""Season ↔ Team M2M association."""
from __future__ import annotations
import uuid
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from athena.db.model import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.db.models.season import Season
    from athena.db.models.team import Team


class SeasonTeam(BaseModel):
    __tablename__ = "season_team"
    __table_args__ = (
        UniqueConstraint("season_id", "team_id", name="uq_season_team"),
    )

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("season.id"), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("team.id"), nullable=False)

    season: Mapped["Season"] = relationship("Season", back_populates="season_teams")
    team: Mapped["Team"] = relationship("Team", back_populates="season_teams")

    def __repr__(self) -> str:
        return f"<SeasonTeam season={self.season_id} team={self.team_id}>"
