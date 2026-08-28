"""Tests for the SqliteStateStore adapter."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from devworkwire.features.work_items.domain.import_state import WorkItemRef
from devworkwire.infrastructure.local.sqlite_state_store import SqliteStateStore


@pytest.fixture
def tmp_db(tmp_path: Path) -> Iterator[SqliteStateStore]:
    """Create a fresh SQLite store in a temp directory."""
    db = SqliteStateStore(tmp_path / "test.db")
    yield db
    db.close()


class TestSqliteStateStore:
    def test_save_and_find_work_item(self, tmp_db: SqliteStateStore):
        ref = WorkItemRef(
            item_key="EPIC-0",
            item_type="epic",
            provider_key="OPH-42",
            provider_id="10042",
        )
        tmp_db.save_import(
            source_path="/tmp/epic.md",
            source_hash="abc123",
            epic_key="EPIC-0",
            work_items=[ref],
        )

        result = tmp_db.find_work_item("abc123", "EPIC-0")
        assert result == "OPH-42"

    def test_find_work_item_returns_none_when_missing(self, tmp_db: SqliteStateStore):
        result = tmp_db.find_work_item("nonexistent", "EPIC-X")
        assert result is None

    def test_list_imports_empty(self, tmp_db: SqliteStateStore):
        assert tmp_db.list_imports() == []

    def test_list_imports_returns_records(self, tmp_db: SqliteStateStore):
        ref = WorkItemRef(
            item_key="EPIC-0",
            item_type="epic",
            provider_key="OPH-42",
        )
        tmp_db.save_import(
            source_path="/tmp/epic.md",
            source_hash="abc123",
            epic_key="EPIC-0",
            work_items=[ref],
        )

        records = tmp_db.list_imports()
        assert len(records) == 1
        assert records[0].epic_key == "EPIC-0"
        assert records[0].source_path == "/tmp/epic.md"
        assert len(records[0].work_items) == 1

    def test_save_import_replaces_existing(self, tmp_db: SqliteStateStore):
        ref1 = WorkItemRef(item_key="EPIC-0", item_type="epic", provider_key="OPH-10")
        tmp_db.save_import(
            source_path="/tmp/epic.md",
            source_hash="abc123",
            epic_key="EPIC-0",
            work_items=[ref1],
        )

        ref2 = WorkItemRef(item_key="EPIC-0", item_type="epic", provider_key="OPH-99")
        tmp_db.save_import(
            source_path="/tmp/epic.md",
            source_hash="abc123",
            epic_key="EPIC-0",
            work_items=[ref2],
        )

        records = tmp_db.list_imports()
        assert len(records) == 1
        assert records[0].work_items[0].provider_key == "OPH-99"

    def test_find_import_by_hash(self, tmp_db: SqliteStateStore):
        ref = WorkItemRef(item_key="EPIC-0", item_type="epic", provider_key="OPH-42")
        tmp_db.save_import(
            source_path="/tmp/epic.md",
            source_hash="abc123",
            epic_key="EPIC-0",
            work_items=[ref],
        )

        record = tmp_db.find_import_by_hash("abc123")
        assert record is not None
        assert record.epic_key == "EPIC-0"

    def test_find_import_by_hash_returns_none(self, tmp_db: SqliteStateStore):
        assert tmp_db.find_import_by_hash("nonexistent") is None

    def test_story_keys_property(self, tmp_db: SqliteStateStore):
        refs = [
            WorkItemRef(item_key="EPIC-0", item_type="epic", provider_key="OPH-1"),
            WorkItemRef(item_key="EPIC-0-1", item_type="story", provider_key="OPH-2"),
            WorkItemRef(item_key="EPIC-0-2", item_type="story", provider_key="OPH-3"),
        ]
        tmp_db.save_import(
            source_path="/tmp/epic.md",
            source_hash="abc123",
            epic_key="EPIC-0",
            work_items=refs,
        )

        records = tmp_db.list_imports()
        assert records[0].story_keys == ["OPH-2", "OPH-3"]
