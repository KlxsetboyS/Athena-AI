"""Bookmaker entity – represents a betting operator."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from athena.db.model import BaseModel

if TYPE_CHECKING:
    from athena.db.models.odds_snapshot import OddsSnapshot


class Bookmaker(BaseModel):
    """A betting operator that provides odds.

    Attributes:
        name:         Human-readable name (e.g. "Bet365").
        slug:         Unique machine-readable slug (e.g. "bet365").
        country_code: ISO 3166-1 alpha-2 country of origin (optional).
        is_exchange:  True for betting exchanges (e.g. Betfair).
        is_active:    Soft-toggle to disable a bookmaker without deleting it.
        external_id:  Identifier in upstream data provider systems.
    """

    __tablename__ = "bookmaker"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_bookmaker_slug"),
        CheckConstraint("length(name) >= 2", name="name_min_length"),
        CheckConstraint("length(slug) >= 2", name="slug_min_length"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    is_exchange: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship(
        "OddsSnapshot", back_populates="bookmaker"
    )

    def __repr__(self) -> str:
        return (
            f"<Bookmaker id={self.id} slug={self.slug!r} "
            f"exchange={self.is_exchange} active={self.is_active}>"
        )
