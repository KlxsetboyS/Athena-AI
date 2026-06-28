"""Season entity."""
from __future__ import annotations
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from athena.db.model import BaseModel
from athena.db.enums import SeasonStatus

if TYPE_CHECKING:
    from athena.db.models.competition import Competition
    from athena.db.models.season_team import SeasonTeam
    from athena.db.models.match import Match


class Season(BaseModel):
    """A competition season (e.g. 2024/2025)."""
    __tablename__ = "season"
    __table_args__ = (
        UniqueConstraint("competition_id", "year_start", name="uq_season_competition_year"),
        CheckConstraint("year_end >= year_start", name="year_order"),
    )

    competition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competition.id"), nullable=False)
    year_start: Mapped[int] = mapped_column(Integer, nullable=False)
    year_end: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[SeasonStatus] = mapped_column(default=SeasonStatus.UPCOMING, nullable=False)

    competition: Mapped["Competition"] = relationship("Competition", back_populates="seasons")
    season_teams: Mapped[list["SeasonTeam"]] = relationship("SeasonTeam", back_populates="season")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="season")

    def __repr__(self) -> str:
        return f"<Season id={self.id} label={self.label!r} status={self.status}>"
