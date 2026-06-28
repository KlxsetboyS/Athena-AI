"""Competition entity."""
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from athena.db.model import BaseModel
from athena.db.enums import CompetitionType, CompetitionGender

if TYPE_CHECKING:
    from athena.db.models.season import Season
    from athena.db.models.match import Match


class Competition(BaseModel):
    """A football competition (league, cup, international tournament)."""
    __tablename__ = "competition"
    __table_args__ = (
        CheckConstraint("length(name) >= 2", name="name_min_length"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    competition_type: Mapped[CompetitionType] = mapped_column(nullable=False)
    gender: Mapped[CompetitionGender] = mapped_column(default=CompetitionGender.MALE, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    seasons: Mapped[list["Season"]] = relationship("Season", back_populates="competition")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="competition")

    def __repr__(self) -> str:
        return f"<Competition id={self.id} name={self.name!r} type={self.competition_type}>"
