"""Unit tests for BaseRepository generic CRUD operations.

Uses CompetitionRepository as the concrete implementation under test
(Competition is the simplest entity with no mandatory FKs).

Coverage targets
----------------
- create()
- get_by_id() / get_by_id_or_raise()
- exists()
- count()
- list()  (pagination and ordering)
- update()
- soft_delete() / restore()
- delete()  (hard delete)
"""
from __future__ import annotations

import uuid

import pytest

from athena.db.enums import CompetitionGender, CompetitionType
from athena.repositories.competition import CompetitionRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _make_comp(repo: CompetitionRepository, name: str = "Test League") -> object:
    return await repo.create(
        name=name,
        competition_type=CompetitionType.LEAGUE,
        gender=CompetitionGender.MALE,
    )


# ── CREATE ────────────────────────────────────────────────────────────────────

class TestCreate:
    async def test_create_returns_instance(self, competition_repo):
        comp = await _make_comp(competition_repo)
        assert comp is not None
        assert comp.id is not None

    async def test_created_instance_has_correct_attributes(self, competition_repo):
        comp = await competition_repo.create(
            name="La Liga",
            competition_type=CompetitionType.LEAGUE,
            gender=CompetitionGender.MALE,
            external_id="ESP.1",
        )
        assert comp.name == "La Liga"
        assert comp.competition_type == CompetitionType.LEAGUE
        assert comp.external_id == "ESP.1"

    async def test_create_sets_is_deleted_false(self, competition_repo):
        comp = await _make_comp(competition_repo)
        assert comp.is_deleted is False
        assert comp.deleted_at is None


# ── READ ──────────────────────────────────────────────────────────────────────

class TestRead:
    async def test_get_by_id_returns_object(self, competition_repo):
        comp = await _make_comp(competition_repo)
        fetched = await competition_repo.get_by_id(comp.id)
        assert fetched is not None
        assert fetched.id == comp.id

    async def test_get_by_id_missing_returns_none(self, competition_repo):
        result = await competition_repo.get_by_id(uuid.uuid4())
        assert result is None

    async def test_get_by_id_or_raise_returns_object(self, competition_repo):
        comp = await _make_comp(competition_repo)
        fetched = await competition_repo.get_by_id_or_raise(comp.id)
        assert fetched.id == comp.id

    async def test_get_by_id_or_raise_missing_raises(self, competition_repo):
        with pytest.raises(LookupError):
            await competition_repo.get_by_id_or_raise(uuid.uuid4())

    async def test_get_by_id_excludes_soft_deleted(self, competition_repo):
        comp = await _make_comp(competition_repo)
        await competition_repo.soft_delete(comp)
        result = await competition_repo.get_by_id(comp.id)
        assert result is None

    async def test_exists_true_for_present(self, competition_repo):
        comp = await _make_comp(competition_repo)
        assert await competition_repo.exists(comp.id) is True

    async def test_exists_false_for_missing(self, competition_repo):
        assert await competition_repo.exists(uuid.uuid4()) is False

    async def test_exists_false_for_soft_deleted(self, competition_repo):
        comp = await _make_comp(competition_repo)
        await competition_repo.soft_delete(comp)
        assert await competition_repo.exists(comp.id) is False


# ── COUNT ─────────────────────────────────────────────────────────────────────

class TestCount:
    async def test_count_increases_after_create(self, competition_repo):
        before = await competition_repo.count()
        await _make_comp(competition_repo, "Counted League A")
        await _make_comp(competition_repo, "Counted League B")
        after = await competition_repo.count()
        assert after == before + 2

    async def test_count_excludes_soft_deleted_by_default(self, competition_repo):
        comp = await _make_comp(competition_repo, "Deleted League")
        before = await competition_repo.count()
        await competition_repo.soft_delete(comp)
        after = await competition_repo.count()
        assert after == before - 1

    async def test_count_include_deleted_flag(self, competition_repo):
        comp = await _make_comp(competition_repo, "Include-Deleted League")
        await competition_repo.soft_delete(comp)
        total_with = await competition_repo.count(include_deleted=True)
        total_without = await competition_repo.count(include_deleted=False)
        assert total_with >= total_without


# ── LIST ──────────────────────────────────────────────────────────────────────

class TestList:
    async def test_list_returns_sequence(self, competition_repo):
        await _make_comp(competition_repo, "List Test League")
        results = await competition_repo.list()
        assert isinstance(results, (list, tuple)) or hasattr(results, "__iter__")
        assert len(results) >= 1

    async def test_list_respects_limit(self, competition_repo):
        for i in range(5):
            await _make_comp(competition_repo, f"Limit Test {i}")
        results = await competition_repo.list(limit=3)
        assert len(results) <= 3

    async def test_list_excludes_soft_deleted(self, competition_repo):
        comp = await _make_comp(competition_repo, "Hidden League")
        await competition_repo.soft_delete(comp)
        results = await competition_repo.list()
        ids = [r.id for r in results]
        assert comp.id not in ids


# ── UPDATE ────────────────────────────────────────────────────────────────────

class TestUpdate:
    async def test_update_changes_attribute(self, competition_repo):
        comp = await _make_comp(competition_repo, "Old Name")
        updated = await competition_repo.update(comp, name="New Name")
        assert updated.name == "New Name"

    async def test_update_returns_same_id(self, competition_repo):
        comp = await _make_comp(competition_repo, "Same ID League")
        original_id = comp.id
        updated = await competition_repo.update(comp, name="Same ID Updated")
        assert updated.id == original_id

    async def test_update_multiple_fields(self, competition_repo):
        comp = await _make_comp(competition_repo, "Multi Update")
        updated = await competition_repo.update(
            comp,
            name="Bundesliga",
            competition_type=CompetitionType.LEAGUE,
        )
        assert updated.name == "Bundesliga"
        assert updated.competition_type == CompetitionType.LEAGUE


# ── SOFT DELETE / RESTORE ─────────────────────────────────────────────────────

class TestSoftDeleteAndRestore:
    async def test_soft_delete_marks_deleted(self, competition_repo):
        comp = await _make_comp(competition_repo, "To Soft Delete")
        await competition_repo.soft_delete(comp)
        assert comp.is_deleted is True
        assert comp.deleted_at is not None

    async def test_restore_unmarks_deleted(self, competition_repo):
        comp = await _make_comp(competition_repo, "To Restore")
        await competition_repo.soft_delete(comp)
        await competition_repo.restore(comp)
        assert comp.is_deleted is False
        assert comp.deleted_at is None

    async def test_restored_object_appears_in_list(self, competition_repo):
        comp = await _make_comp(competition_repo, "Restored League")
        await competition_repo.soft_delete(comp)
        await competition_repo.restore(comp)
        result = await competition_repo.get_by_id(comp.id)
        assert result is not None


# ── HARD DELETE ───────────────────────────────────────────────────────────────

class TestHardDelete:
    async def test_hard_delete_removes_row(self, competition_repo):
        comp = await _make_comp(competition_repo, "To Hard Delete")
        comp_id = comp.id
        await competition_repo.delete(comp)
        result = await competition_repo.get_by_id(comp_id)
        assert result is None

    async def test_hard_delete_reduces_count(self, competition_repo):
        comp = await _make_comp(competition_repo, "Hard Delete Count")
        before = await competition_repo.count(include_deleted=True)
        await competition_repo.delete(comp)
        after = await competition_repo.count(include_deleted=True)
        assert after == before - 1
