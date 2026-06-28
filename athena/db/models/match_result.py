"""MatchResult entity – official match outcomes."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum
from athena.db.model import BaseModel
from athena.db.enums import ResultType, MatchResultStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.db.models.match import Match


class MatchResult(BaseModel):
    """Official result for a Match (1:1 relation)."""
    __tablename__ = "match_result"
    __table_args__ = (
        UniqueConstraint("match_id", name="uq_match_result_match"),
        CheckConstraint("home_score >= 0", name="home_score_non_negative"),
        CheckConstraint("away_score >= 0", name="away_score_non_negative"),
        CheckConstraint(
            "(home_score IS NULL) = (away_score IS NULL)",
            name="scores_both_or_neither",
        ),
        CheckConstraint(
            "result_type IS NULL OR match_status = 'finished'",
            name="type_only_when_finished",
        ),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match.id"), nullable=False)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_type: Mapped[ResultType | None] = mapped_column(
        SAEnum(ResultType, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    match_status: Mapped[MatchResultStatus] = mapped_column(
        SAEnum(MatchResultStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    match: Mapped["Match"] = relationship("Match", back_populates="result")

    def __repr__(self) -> str:
        return (
            f"<MatchResult match={self.match_id} "
            f"{self.home_score}-{self.away_score} status={self.match_status}>"
        )
