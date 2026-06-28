"""Abstract BaseModel combining all mixins."""
from __future__ import annotations
from sqlalchemy.orm import declared_attr
from athena.db.base import Base
from athena.db.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin


class BaseModel(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __abstract__ = True

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
