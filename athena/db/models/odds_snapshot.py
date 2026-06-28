"""OddsSnapshot entity – captures odds state at a specific point in time.

Design rationale:
    A snapshot is an immutable record of all odds offered by a bookmaker
    for a specific match at a given moment.  This preserves the full
    historical timeline of odds movements, which is critical for:
      - Training features (line-movement, closing-line-value, etc.)
      - Audit trails
      - Avoiding survivor-bias in datasets

    Snapshots are NEVER mutated; new data always creates a new row.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from athena.db.enums import OddsFormat, OddsMarket
from athena.db.model import BaseModel

if TYPE_CHECKING:
    from athena.db.models.bookmaker import Bookmaker
    from athena.db.models.match import Match
    from athena.db.models.odds_selection import OddsSelection


class OddsSnapshot(BaseModel):
    """A frozen record of all odds for a match offered by one bookmaker
    at a specific instant in time.

    Relationships:
        match       – the match these odds refer to  (N snapshots per match)
        bookmaker   – the operator who published them (N snapshots per bookmaker)
        selections  – individual outcome odds within this snapshot

    Attributes:
        match_id:       FK → match
        bookmaker_id:   FK → bookmaker
        market:         Betting market (MATCH_WINNER = 1X2, extensible)
        odds_format:    DECIMAL | FRACTIONAL | AMERICAN
        captured_at:    UTC timestamp when these odds were recorded
        is_closing:     True when this snapshot represents the closing line
        source:         Data provider identifier (e.g. "oddsapi", "pinnacle_feed")
        external_ref:   Provider-side snapshot reference (deduplication key)
    """

    __tablename__ = "odds_snapshot"
    __table_args__ = (
        CheckConstraint("length(source) >= 1", name="source_not_empty"),
        # Composite index: fast lookup of all snapshots for a match/bookmaker pair
        Index(
            "ix_odds_snapshot_match_bookmaker_captured",
            "match_id",
            "bookmaker_id",
            "captured_at",
        ),
        # Index for closing-line queries
        Index("ix_odds_snapshot_is_closing", "match_id", "is_closing"),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match.id"), nullable=False
    )
    bookmaker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bookmaker.id"), nullable=False
    )
    market: Mapped[OddsMarket] = mapped_column(
        default=OddsMarket.MATCH_WINNER, nullable=False
    )
    odds_format: Mapped[OddsFormat] = mapped_column(
        default=OddsFormat.DECIMAL, nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_closing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )

    # Relationships
    match: Mapped["Match"] = relationship("Match", back_populates="odds_snapshots")
    bookmaker: Mapped["Bookmaker"] = relationship(
        "Bookmaker", back_populates="odds_snapshots"
    )
    selections: Mapped[list["OddsSelection"]] = relationship(
        "OddsSelection",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<OddsSnapshot id={self.id} "
            f"match={self.match_id} "
            f"bookmaker={self.bookmaker_id} "
            f"market={self.market} "
            f"captured_at={self.captured_at} "
            f"closing={self.is_closing}>"
        )
