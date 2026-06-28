"""Reusable SQLAlchemy mixins: UUID, Timestamps, SoftDelete."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = _utcnow()

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
