"""OddsSelection entity – a single outcome's odds within an OddsSnapshot.

Design rationale:
    Each OddsSnapshot contains N selections, one per outcome in the market.
    For 1X2: HOME, DRAW, AWAY  → 3 selections per snapshot.
    For Over/Under 2.5: OVER, UNDER → 2 selections per snapshot.

    Storing odds as DECIMAL internally simplifies:
      - Mathematical comparisons
      - Feature engineering (implied probability = 1 / decimal_odd)
      - Normalization / margin stripping

    The implied_probability column is NULLABLE and intentionally NOT computed
    here; it belongs in the Feature Engineering layer (future sprint).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from athena.db.enums import SelectionType
from athena.db.model import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.db.models.odds_snapshot import OddsSnapshot


class OddsSelection(BaseModel):
    """A single outcome (selection) and its decimal odd within a snapshot.

    Attributes:
        snapshot_id:    FK → odds_snapshot
        selection_type: HOME | DRAW | AWAY | OVER | UNDER | YES | NO
        label:          Optional free-text label (e.g. "Over 2.5", "AH -0.5")
        decimal_odd:    Odds in decimal format (≥ 1.01).  REQUIRED.
        line:           Handicap or total line value for spread/OU markets.
        is_suspended:   True when the bookmaker suspended betting on this line.
    """

    __tablename__ = "odds_selection"
    __table_args__ = (
        # Each selection type must appear at most once per snapshot
        UniqueConstraint(
            "snapshot_id", "selection_type", "line",
            name="uq_odds_selection_snapshot_type_line",
        ),
        CheckConstraint("decimal_odd >= 1.01", name="decimal_odd_minimum"),
        CheckConstraint(
            "line IS NULL OR line > 0",
            name="line_positive_when_set",
        ),
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("odds_snapshot.id"), nullable=False
    )
    selection_type: Mapped[SelectionType] = mapped_column(nullable=False)
    label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    decimal_odd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=4), nullable=False
    )
    line: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=6, scale=2), nullable=True
    )
    is_suspended: Mapped[bool] = mapped_column(default=False, nullable=False)

    snapshot: Mapped["OddsSnapshot"] = relationship(
        "OddsSnapshot", back_populates="selections"
    )

    def __repr__(self) -> str:
        return (
            f"<OddsSelection snapshot={self.snapshot_id} "
            f"type={self.selection_type} "
            f"odd={self.decimal_odd} "
            f"line={self.line} "
            f"suspended={self.is_suspended}>"
        )
