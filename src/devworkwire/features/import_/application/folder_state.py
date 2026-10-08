"""Durable local record for resumable folder imports."""

import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

STATE_FILE = ".devworkwire-import.json"
LOCK_FILE = ".devworkwire-import.lock"
_ISSUE_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*-\d+\Z")
_PROJECT_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")


@dataclass
class ItemRecord:
    status: str
    source_hash: str
    key: str | None = None


@dataclass
class ImportState:
    folder: Path
    base_url: str | None = None
    project_key: str | None = None
    epic: ItemRecord | None = None
    stories: dict[str, ItemRecord] = field(default_factory=dict)

    @classmethod
    def load(cls, folder: Path) -> "ImportState":
        path = folder / STATE_FILE
        if path.is_symlink():
            raise ValueError(f"Refusing symbolic link: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls(folder)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Cannot read {path}: {error}") from error

        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError(f"Invalid {path}: unsupported state format")
        jira = data.get("jira")
        if not isinstance(jira, dict) or not all(
            isinstance(jira.get(name), str) and jira[name]
            for name in ("base_url", "project_key")
        ) or not _PROJECT_KEY.fullmatch(jira["project_key"]):
            raise ValueError(f"Invalid {path}: missing Jira destination")
        stories = data.get("stories")
        if not isinstance(stories, dict) or not all(
            isinstance(story_id, str) and story_id.strip() for story_id in stories
        ):
            raise ValueError(f"Invalid {path}: stories must be keyed by story ID")
        epic = _read_record(data.get("epic"), path) if data.get("epic") is not None else None
        if stories and (epic is None or epic.status != "created"):
            raise ValueError(f"Invalid {path}: stories require a created epic")
        story_records = {
            story_id: _read_record(record, path) for story_id, record in stories.items()
        }
        for record in ([epic] if epic is not None else []) + list(story_records.values()):
            if record.key is not None and not record.key.startswith(f"{jira['project_key']}-"):
                raise ValueError(f"Invalid {path}: issue key belongs to another project")
        _require_unique_keys(epic, story_records, path)
        return cls(
            folder, jira["base_url"], jira["project_key"], epic,
            story_records,
        )

    def require_destination(self, base_url: str, project_key: str) -> None:
        if self.base_url is None:
            self.base_url = base_url.rstrip("/")
            self.project_key = project_key
        elif (self.base_url, self.project_key) != (base_url.rstrip("/"), project_key):
            raise ValueError(
                "Import state belongs to a different Jira destination; "
                "use the original destination or a different folder"
            )

    def save(self) -> None:
        if self.base_url is None or self.project_key is None:
            raise ValueError("Jira destination is required before saving import state")
        path = self.folder / STATE_FILE
        if path.is_symlink():
            raise ValueError(f"Refusing symbolic link: {path}")
        for record in ([self.epic] if self.epic is not None else []) + list(self.stories.values()):
            _read_record(_write_record(record), path)
            if record.key is not None and not record.key.startswith(f"{self.project_key}-"):
                raise ValueError(f"Invalid {path}: issue key belongs to another project")
        _require_unique_keys(self.epic, self.stories, path)
        payload = {
            "version": 1,
            "jira": {"base_url": self.base_url, "project_key": self.project_key},
            "epic": _write_record(self.epic),
            "stories": {
                story_id: _write_record(record)
                for story_id, record in self.stories.items()
            },
        }
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.folder,
                prefix=".devworkwire-import-", suffix=".tmp", delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(payload, temporary, indent=2)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
            if os.name != "nt":
                directory = os.open(self.folder, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def _read_record(value: object, path: Path) -> ItemRecord:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid {path}: item record must be an object")
    status = value.get("status")
    source_hash = value.get("source_hash")
    key = value.get("key")
    if (
        status not in ("pending", "created")
        or not isinstance(source_hash, str)
        or not _HASH.fullmatch(source_hash)
        or (status == "pending" and key is not None)
        or (status == "created" and (not isinstance(key, str) or not _ISSUE_KEY.fullmatch(key)))
    ):
        raise ValueError(f"Invalid {path}: malformed item record")
    return ItemRecord(status, source_hash, key)


def _write_record(record: ItemRecord | None) -> dict | None:
    if record is None:
        return None
    return {"status": record.status, "source_hash": record.source_hash, "key": record.key}


def _require_unique_keys(
    epic: ItemRecord | None, stories: dict[str, ItemRecord], path: Path
) -> None:
    records = ([epic] if epic is not None else []) + list(stories.values())
    keys = [record.key for record in records if record.key is not None]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Invalid {path}: Jira issue keys must be unique")


@contextmanager
def lock_folder(folder: Path) -> Iterator[None]:
    path = folder / LOCK_FILE
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError(
            f"Folder import is locked: {path}. If no import is running, "
            "inspect Jira and the state file before removing the stale lock."
        ) from error
    try:
        with os.fdopen(descriptor, "w") as lock:
            lock.write(f"{os.getpid()}\n")
            lock.flush()
            os.fsync(lock.fileno())
        yield
    finally:
        path.unlink(missing_ok=True)
