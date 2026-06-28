"""Generic async repository base for all Athena AI domain models.

Usage::

    class MyRepo(BaseRepository[MyModel]):
        pass

    repo = MyRepo(session)
    obj  = await repo.get_by_id(some_uuid)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from athena.db.model import BaseModel

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    """Async CRUD repository backed by SQLAlchemy AsyncSession.

    All mutating operations do NOT call ``session.commit()`` – that is
    the responsibility of the caller (Unit-of-Work pattern).  Use
    ``session.flush()`` internally only when an auto-generated value
    (e.g. ``created_at``) is needed before the transaction is committed.

    Attributes:
        model:   The SQLAlchemy mapped class this repository manages.
        session: Active :class:`AsyncSession` injected at construction time.
    """

    model: type[ModelT]  # set by subclasses

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        if not hasattr(self, "model"):
            raise TypeError(
                f"{self.__class__.__name__} must define a 'model' class attribute."
            )

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> ModelT:
        """Instantiate, add to session, flush and return the new object.

        Args:
            **kwargs: Column values passed directly to the model constructor.

        Returns:
            Flushed (but not committed) model instance.
        """
        obj: ModelT = self.model(**kwargs)
        self._session.add(obj)
        await self._session.flush()
        logger.debug("created %s id=%s", self.model.__name__, obj.id)
        return obj

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, obj_id: uuid.UUID) -> ModelT | None:
        """Return a single instance by primary key, or ``None`` if not found.

        Excludes soft-deleted rows.
        """
        stmt = (
            select(self.model)
            .where(self.model.id == obj_id)
            .where(self.model.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, obj_id: uuid.UUID) -> ModelT:
        """Like :meth:`get_by_id` but raises ``LookupError`` when not found."""
        obj = await self.get_by_id(obj_id)
        if obj is None:
            raise LookupError(
                f"{self.model.__name__} with id={obj_id} not found or is deleted."
            )
        return obj

    async def exists(self, obj_id: uuid.UUID) -> bool:
        """Return True if an active (non-deleted) row with *obj_id* exists."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.id == obj_id)
            .where(self.model.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def count(self, include_deleted: bool = False) -> int:
        """Return the total number of rows.

        Args:
            include_deleted: When True, counts soft-deleted rows too.
        """
        stmt = select(func.count()).select_from(self.model)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> Sequence[ModelT]:
        """Return a page of rows ordered by creation date (newest first).

        Args:
            offset:          Number of rows to skip.
            limit:           Maximum number of rows to return.
            include_deleted: When True, includes soft-deleted rows.
        """
        stmt = select(self.model).order_by(self.model.created_at.desc())
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(self, obj: ModelT, **kwargs: Any) -> ModelT:
        """Apply *kwargs* as attribute updates, flush, and return the object.

        Args:
            obj:     Model instance already tracked by the session.
            **kwargs: Attribute name → new value pairs.
        """
        for attr, value in kwargs.items():
            setattr(obj, attr, value)
        self._session.add(obj)
        await self._session.flush()
        logger.debug("updated %s id=%s attrs=%s", self.model.__name__, obj.id, list(kwargs))
        return obj

    # ── Delete ────────────────────────────────────────────────────────────────

    async def soft_delete(self, obj: ModelT) -> ModelT:
        """Mark *obj* as deleted without removing it from the database."""
        obj.soft_delete()
        self._session.add(obj)
        await self._session.flush()
        logger.debug("soft-deleted %s id=%s", self.model.__name__, obj.id)
        return obj

    async def restore(self, obj: ModelT) -> ModelT:
        """Undo a soft delete on *obj*."""
        obj.restore()
        self._session.add(obj)
        await self._session.flush()
        logger.debug("restored %s id=%s", self.model.__name__, obj.id)
        return obj

    async def delete(self, obj: ModelT) -> None:
        """Permanently delete *obj* from the database.

        .. warning::
            Prefer :meth:`soft_delete` for audit trail preservation.
            Hard delete is provided for test cleanup and data-retention policies.
        """
        await self._session.delete(obj)
        await self._session.flush()
        logger.debug("hard-deleted %s id=%s", self.model.__name__, obj.id)
