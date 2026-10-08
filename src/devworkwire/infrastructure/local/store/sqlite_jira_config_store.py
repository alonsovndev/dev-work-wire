import os
import sqlite3
import stat
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from devworkwire.config.paths import Paths
from devworkwire.core.domain.exceptions import BusinessRuleViolation
from devworkwire.core.ports.jira_config_store import (
    JiraConfigStore,
    JiraCredentials,
    JiraProject,
    normalize_project_key,
)

_SCHEMA_VERSION = 1
_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS jira_connection (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        base_url TEXT NOT NULL,
        email TEXT NOT NULL,
        api_token TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jira_projects (
        project_key TEXT PRIMARY KEY,
        is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
        added_at TEXT NOT NULL
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS one_default_project "
    "ON jira_projects (is_default) WHERE is_default = 1",
)


class SqliteJiraConfigStore(JiraConfigStore):
    """Jira connection and project list in a user-private SQLite file.

    The token is stored in plaintext; protection is file mode 0600 inside a 0700
    directory, the same trust level as a ``.env`` file.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path

    @property
    def db_path(self) -> Path:
        return self._db_path or Paths.jira_credentials_db_path()

    def load_credentials(self) -> Optional[JiraCredentials]:
        if not self.db_path.exists():
            return None
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT base_url, email, api_token FROM jira_connection WHERE id = 1"
            ).fetchone()
        return JiraCredentials(*row) if row else None

    def save_credentials(self, credentials: JiraCredentials) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO jira_connection (id, base_url, email, api_token, updated_at) "
                "VALUES (1, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET base_url = excluded.base_url, "
                "email = excluded.email, api_token = excluded.api_token, "
                "updated_at = excluded.updated_at",
                (credentials.base_url, credentials.email, credentials.api_token, _now()),
            )

    def list_projects(self) -> list[JiraProject]:
        if not self.db_path.exists():
            return []
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT project_key, is_default FROM jira_projects ORDER BY added_at, rowid"
            ).fetchall()
        return [JiraProject(key, bool(is_default)) for key, is_default in rows]

    def add_project(self, project_key: str, make_default: bool = False) -> None:
        key = normalize_project_key(project_key)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT OR IGNORE INTO jira_projects (project_key, is_default, added_at) "
                "VALUES (?, 0, ?)",
                (key, _now()),
            )
            has_default = connection.execute(
                "SELECT 1 FROM jira_projects WHERE is_default = 1"
            ).fetchone()
            if make_default or not has_default:
                _mark_default(connection, key)

    def set_default_project(self, project_key: str) -> None:
        key = normalize_project_key(project_key)
        with closing(self._connect()) as connection, connection:
            _require_project(connection, key)
            _mark_default(connection, key)

    def remove_project(self, project_key: str) -> None:
        key = normalize_project_key(project_key)
        with closing(self._connect()) as connection, connection:
            was_default = _require_project(connection, key)
            connection.execute("DELETE FROM jira_projects WHERE project_key = ?", (key,))
            if was_default:
                oldest = connection.execute(
                    "SELECT project_key FROM jira_projects ORDER BY added_at, rowid LIMIT 1"
                ).fetchone()
                if oldest:
                    _mark_default(connection, oldest[0])

    def clear(self) -> None:
        if not self.db_path.exists():
            return
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM jira_connection")
            connection.execute("DELETE FROM jira_projects")

    def _connect(self) -> sqlite3.Connection:
        path = self.db_path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if stat.S_IMODE(path.parent.stat().st_mode) & 0o077:
            path.parent.chmod(0o700)
        if path.is_symlink():
            raise BusinessRuleViolation(f"Refusing to use symlinked config database: {path}")
        if not path.exists():
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        elif stat.S_IMODE(path.stat().st_mode) != 0o600:
            path.chmod(0o600)
        connection = sqlite3.connect(path)
        try:
            # Deleted tokens must not linger in free pages of the file.
            connection.execute("PRAGMA secure_delete = ON")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > _SCHEMA_VERSION:
                raise BusinessRuleViolation(
                    f"Config database {path} was written by a newer DevWorkWire version"
                )
            for statement in _SCHEMA:
                connection.execute(statement)
            if version == 0:
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        except BaseException:
            connection.close()
            raise
        return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_project(connection: sqlite3.Connection, key: str) -> bool:
    row = connection.execute(
        "SELECT is_default FROM jira_projects WHERE project_key = ?", (key,)
    ).fetchone()
    if row is None:
        raise BusinessRuleViolation(f"Project {key} is not configured. Add it with `dwire config add-project {key}`.")
    return bool(row[0])


def _mark_default(connection: sqlite3.Connection, key: str) -> None:
    connection.execute("UPDATE jira_projects SET is_default = 0 WHERE is_default = 1")
    connection.execute("UPDATE jira_projects SET is_default = 1 WHERE project_key = ?", (key,))
