"""SQLite-backed implementation of the StateRepository port.

Stores import state in a local ``devworkwire-state.db`` file.  The database
is created automatically on first access.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from devworkwire.features.work_items.application.ports import StateRepository
from devworkwire.features.work_items.domain.import_state import (
    ImportRecord,
    WorkItemRef,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS imports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT    NOT NULL,
    source_hash TEXT    NOT NULL UNIQUE,
    epic_key    TEXT    NOT NULL,
    imported_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS work_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id    INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
    source_hash  TEXT    NOT NULL,
    item_key     TEXT    NOT NULL,
    item_type    TEXT    NOT NULL,
    provider_key TEXT    NOT NULL,
    provider_id  TEXT,
    UNIQUE(source_hash, item_key)
);
"""


class SqliteStateStore(StateRepository):
    """SQLite adapter for import state persistence."""

    def __init__(self, db_path: Path | str = "devworkwire-state.db"):
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── StateRepository implementation ─────────────────────────────────

    def find_work_item(self, source_hash: str, item_key: str) -> str | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT provider_key FROM work_items "
            "WHERE source_hash = ? AND item_key = ?",
            (source_hash, item_key),
        ).fetchone()
        return row["provider_key"] if row else None

    def save_import(
        self,
        source_path: str,
        source_hash: str,
        epic_key: str,
        work_items: list[WorkItemRef],
    ) -> None:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            # Delete existing import for this source hash (if any).
            old = conn.execute(
                "SELECT id FROM imports WHERE source_hash = ?", (source_hash,)
            ).fetchone()
            if old is not None:
                conn.execute("DELETE FROM work_items WHERE import_id = ?", (old["id"],))
                conn.execute("DELETE FROM imports WHERE id = ?", (old["id"],))

            cursor = conn.execute(
                "INSERT INTO imports (source_path, source_hash, epic_key, imported_at) "
                "VALUES (?, ?, ?, ?)",
                (source_path, source_hash, epic_key, now),
            )
            import_id = cursor.lastrowid

            for ref in work_items:
                conn.execute(
                    "INSERT INTO work_items "
                    "(import_id, source_hash, item_key, item_type, provider_key, provider_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        import_id,
                        source_hash,
                        ref.item_key,
                        ref.item_type,
                        ref.provider_key,
                        ref.provider_id,
                    ),
                )

    def list_imports(self) -> list[ImportRecord]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, source_path, source_hash, epic_key, imported_at "
            "FROM imports ORDER BY imported_at DESC"
        ).fetchall()

        records: list[ImportRecord] = []
        for row in rows:
            item_rows = conn.execute(
                "SELECT item_key, item_type, provider_key, provider_id "
                "FROM work_items WHERE import_id = ?",
                (row["id"],),
            ).fetchall()
            work_items = [
                WorkItemRef(
                    item_key=r["item_key"],
                    item_type=r["item_type"],
                    provider_key=r["provider_key"],
                    provider_id=r["provider_id"],
                )
                for r in item_rows
            ]
            records.append(
                ImportRecord(
                    source_path=row["source_path"],
                    source_hash=row["source_hash"],
                    epic_key=row["epic_key"],
                    imported_at=datetime.fromisoformat(row["imported_at"]),
                    work_items=work_items,
                )
            )
        return records

    def find_import_by_hash(self, source_hash: str) -> ImportRecord | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, source_path, source_hash, epic_key, imported_at "
            "FROM imports WHERE source_hash = ?",
            (source_hash,),
        ).fetchone()
        if row is None:
            return None

        item_rows = conn.execute(
            "SELECT item_key, item_type, provider_key, provider_id "
            "FROM work_items WHERE import_id = ?",
            (row["id"],),
        ).fetchall()
        work_items = [
            WorkItemRef(
                item_key=r["item_key"],
                item_type=r["item_type"],
                provider_key=r["provider_key"],
                provider_id=r["provider_id"],
            )
            for r in item_rows
        ]
        return ImportRecord(
            source_path=row["source_path"],
            source_hash=row["source_hash"],
            epic_key=row["epic_key"],
            imported_at=datetime.fromisoformat(row["imported_at"]),
            work_items=work_items,
        )
