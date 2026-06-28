"""Team entity."""
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from athena.db.model import BaseModel
from athena.db.enums import TeamGender

if TYPE_CHECKING:
    from athena.db.models.season_team import SeasonTeam
    from athena.db.models.match import Match


class Team(BaseModel):
    """A football team."""
    __tablename__ = "team"
    __table_args__ = (
        CheckConstraint("length(name) >= 2", name="name_min_length"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    gender: Mapped[TeamGender] = mapped_column(default=TeamGender.MALE, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    season_teams: Mapped[list["SeasonTeam"]] = relationship("SeasonTeam", back_populates="team")
    home_matches: Mapped[list["Match"]] = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches: Mapped[list["Match"]] = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")

    def __repr__(self) -> str:
        return f"<Team id={self.id} name={self.name!r}>"
