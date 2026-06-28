"""Unit tests for UUIDMixin, TimestampMixin, SoftDeleteMixin.

These tests are purely structural – they verify that the BaseModel class
exposes the expected columns and that the soft-delete helpers work correctly.
No database connection is needed for the structural checks; for the
behaviour checks we use the shared async fixtures from conftest.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from athena.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from athena.db.model import BaseModel
from athena.db.models.competition import Competition


# ── Structural (no DB) ────────────────────────────────────────────────────────

class TestBaseModelStructure:
    """Verify column presence and mixin inheritance."""

    def test_uuid_mixin_inherited(self):
        assert issubclass(BaseModel, UUIDMixin)

    def test_timestamp_mixin_inherited(self):
        assert issubclass(BaseModel, TimestampMixin)

    def test_soft_delete_mixin_inherited(self):
        assert issubclass(BaseModel, SoftDeleteMixin)

    def test_competition_has_id_column(self):
        assert hasattr(Competition, "id")

    def test_competition_has_timestamps(self):
        assert hasattr(Competition, "created_at")
        assert hasattr(Competition, "updated_at")

    def test_competition_has_soft_delete_cols(self):
        assert hasattr(Competition, "is_deleted")
        assert hasattr(Competition, "deleted_at")


# ── SoftDelete behaviour (no DB needed) ───────────────────────────────────────

class TestSoftDeleteBehaviour:
    """soft_delete() and restore() manipulate instance attributes correctly."""

    def _make_obj(self) -> SoftDeleteMixin:
        obj = SoftDeleteMixin()
        obj.is_deleted = False
        obj.deleted_at = None
        return obj

    def test_soft_delete_sets_flag(self):
        obj = self._make_obj()
        obj.soft_delete()
        assert obj.is_deleted is True

    def test_soft_delete_sets_deleted_at(self):
        obj = self._make_obj()
        before = datetime.now(timezone.utc)
        obj.soft_delete()
        after = datetime.now(timezone.utc)
        assert obj.deleted_at is not None
        assert before <= obj.deleted_at <= after

    def test_restore_clears_flag(self):
        obj = self._make_obj()
        obj.soft_delete()
        obj.restore()
        assert obj.is_deleted is False

    def test_restore_clears_deleted_at(self):
        obj = self._make_obj()
        obj.soft_delete()
        obj.restore()
        assert obj.deleted_at is None

    def test_double_soft_delete_is_idempotent(self):
        """Calling soft_delete twice should not raise and flag remains True."""
        obj = self._make_obj()
        obj.soft_delete()
        first_ts = obj.deleted_at
        obj.soft_delete()
        assert obj.is_deleted is True
        # deleted_at is refreshed on each call – just ensure it is still set
        assert obj.deleted_at is not None


# ── UUID default (DB fixture required) ────────────────────────────────────────

class TestUUIDDefault:
    """Persisted rows receive a valid UUID v4 primary key."""

    async def test_uuid_is_assigned_on_create(self, competition_repo):
        comp = await competition_repo.create(
            name="Test League",
            competition_type="league",
            gender="male",
        )
        assert comp.id is not None
        assert isinstance(comp.id, uuid.UUID)

    async def test_two_rows_have_different_ids(self, competition_repo):
        a = await competition_repo.create(
            name="Alpha League",
            competition_type="league",
            gender="male",
        )
        b = await competition_repo.create(
            name="Beta Cup",
            competition_type="cup",
            gender="male",
        )
        assert a.id != b.id
