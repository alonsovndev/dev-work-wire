import os
import stat

import pytest

from devworkwire.core.domain.exceptions import BusinessRuleViolation
from devworkwire.core.ports.jira_config_store import JiraCredentials
from devworkwire.infrastructure.local.store.sqlite_jira_config_store import (
    SqliteJiraConfigStore,
)

CREDENTIALS = JiraCredentials("https://jira.test", "user@example.com", "secret-token-value")


@pytest.fixture
def store(tmp_path):
    return SqliteJiraConfigStore(tmp_path / "config" / "config.db")


def _keys(store):
    return [(project.key, project.is_default) for project in store.list_projects()]


def test_reads_return_empty_and_create_nothing_when_unconfigured(store):
    assert store.load_credentials() is None
    assert store.list_projects() == []
    assert not store.db_path.exists()


def test_credentials_round_trip_and_replace(store):
    store.save_credentials(CREDENTIALS)
    store.save_credentials(JiraCredentials("https://other.test", "b@example.com", "token-2"))

    assert store.load_credentials().base_url == "https://other.test"


def test_first_project_becomes_default_and_keys_are_uppercased(store):
    store.add_project("proj")
    store.add_project("other")

    assert _keys(store) == [("PROJ", True), ("OTHER", False)]


def test_add_project_with_default_flag_moves_the_default(store):
    store.add_project("PROJ")
    store.add_project("OTHER", make_default=True)

    assert _keys(store) == [("PROJ", False), ("OTHER", True)]


def test_adding_an_existing_project_is_idempotent(store):
    store.add_project("PROJ")
    store.add_project("proj")

    assert _keys(store) == [("PROJ", True)]


def test_set_default_project(store):
    store.add_project("PROJ")
    store.add_project("OTHER")

    store.set_default_project("other")

    assert _keys(store) == [("PROJ", False), ("OTHER", True)]


def test_set_default_requires_a_configured_project(store):
    with pytest.raises(BusinessRuleViolation, match="add-project NOPE"):
        store.set_default_project("NOPE")


def test_removing_the_default_promotes_the_oldest_remaining_project(store):
    for key in ("Z", "A", "M"):
        store.add_project(key)
    store.set_default_project("A")

    store.remove_project("A")

    assert _keys(store) == [("Z", True), ("M", False)]


def test_removing_a_non_default_keeps_the_default(store):
    store.add_project("A")
    store.add_project("B")

    store.remove_project("B")

    assert _keys(store) == [("A", True)]


def test_removing_the_last_project_leaves_none(store):
    store.add_project("A")
    store.remove_project("A")

    assert store.list_projects() == []


def test_database_rejects_a_second_default_project(store):
    import sqlite3

    store.add_project("A")
    store.add_project("B")

    with pytest.raises(sqlite3.IntegrityError):
        with sqlite3.connect(store.db_path) as connection:
            connection.execute("UPDATE jira_projects SET is_default = 1")


def test_invalid_project_key_is_rejected(store):
    with pytest.raises(BusinessRuleViolation):
        store.add_project("1-bad")


def test_clear_removes_everything_including_the_token_bytes(store):
    store.save_credentials(CREDENTIALS)
    store.add_project("PROJ")

    store.clear()
    store.clear()

    assert store.load_credentials() is None
    assert store.list_projects() == []
    assert b"secret-token-value" not in store.db_path.read_bytes()


def test_database_is_private_to_the_user(store):
    store.save_credentials(CREDENTIALS)

    assert stat.S_IMODE(store.db_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.db_path.parent.stat().st_mode) == 0o700


def test_loose_permissions_are_tightened(store):
    store.save_credentials(CREDENTIALS)
    store.db_path.chmod(0o644)
    store.db_path.parent.chmod(0o755)

    store.load_credentials()

    assert stat.S_IMODE(store.db_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.db_path.parent.stat().st_mode) == 0o700


def test_symlinked_database_is_refused(tmp_path):
    target = tmp_path / "real.db"
    target.touch()
    link = tmp_path / "config.db"
    os.symlink(target, link)

    with pytest.raises(BusinessRuleViolation, match="symlink"):
        SqliteJiraConfigStore(link).load_credentials()


def test_corrupt_database_raises_instead_of_being_overwritten(tmp_path):
    path = tmp_path / "config.db"
    path.write_bytes(b"not a database" * 100)

    with pytest.raises(Exception):
        SqliteJiraConfigStore(path).list_projects()

    assert path.read_bytes().startswith(b"not a database")


def test_default_path_follows_config_dir_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVWORKWIRE_CONFIG_DIR", str(tmp_path))

    assert SqliteJiraConfigStore().db_path == tmp_path / "config.db"


@pytest.mark.parametrize("base_url", ["jira.test", "http://jira.test", "ftp://jira.test", "https://"])
def test_credentials_reject_unsafe_base_urls(base_url):
    with pytest.raises(BusinessRuleViolation, match="https"):
        JiraCredentials(base_url, "a@b.c", "token")


def test_credentials_allow_http_for_localhost_and_normalize():
    credentials = JiraCredentials(" http://localhost:8080/ ", " a@b.c ", " token ")

    assert credentials.base_url == "http://localhost:8080"
    assert (credentials.email, credentials.api_token) == ("a@b.c", "token")
