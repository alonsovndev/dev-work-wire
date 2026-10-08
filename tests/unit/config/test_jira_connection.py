import pytest

from devworkwire.config.jira_connection import resolve_jira_connection
from devworkwire.config.project_config import ProjectConfig
from devworkwire.core.domain.exceptions import BusinessRuleViolation
from devworkwire.core.ports.jira_config_store import JiraCredentials

STORED = JiraCredentials("https://db.test", "db@example.com", "db-token")


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_environment_overrides_stored_connection_values(monkeypatch, fake_store):
    monkeypatch.setenv("JIRA_BASE_URL", "https://env.test")

    connection = resolve_jira_connection(fake_store(STORED, ["DB"]), None)

    assert (connection.base_url.value, connection.base_url.source) == ("https://env.test", "env")
    assert (connection.email.value, connection.email.source) == ("db@example.com", "db")
    assert connection.api_token.source == "db"


def test_jira_project_key_environment_variable_is_ignored(monkeypatch, fake_store):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "PROJ")

    connection = resolve_jira_connection(fake_store(STORED, ["DB"]), ProjectConfig("jira", "FILE"))

    assert (connection.project_key.value, connection.project_key.source) == ("DB", "db")


def test_project_override_beats_default_and_is_normalized(fake_store):
    connection = resolve_jira_connection(fake_store(STORED, ["DB", "OTHER"]), None, "other")

    assert (connection.project_key.value, connection.project_key.source) == ("OTHER", "--project")


def test_project_override_must_be_a_configured_project(fake_store):
    with pytest.raises(BusinessRuleViolation, match="configured: DB"):
        resolve_jira_connection(fake_store(STORED, ["DB"]), None, "NOPE")


def test_blank_project_override_is_rejected_not_ignored(fake_store):
    with pytest.raises(BusinessRuleViolation):
        resolve_jira_connection(fake_store(STORED, ["DB"]), None, "")


def test_project_override_is_accepted_when_no_projects_are_stored(fake_store):
    connection = resolve_jira_connection(fake_store(STORED), None, "ADHOC")

    assert connection.project_key.value == "ADHOC"


def test_default_project_is_used_when_not_the_first(fake_store):
    connection = resolve_jira_connection(fake_store(STORED, ["A", "B"], default="B"), None)

    assert connection.project_key.value == "B"


def test_project_file_supplies_project_key_when_no_projects_stored(fake_store):
    connection = resolve_jira_connection(fake_store(), ProjectConfig("jira", "FILE"))

    assert connection.project_key.source == "devworkwire.yml"
    assert connection.email is None


def test_blank_environment_value_is_treated_as_unset(monkeypatch, fake_store):
    monkeypatch.setenv("JIRA_EMAIL", "  ")

    connection = resolve_jira_connection(fake_store(STORED, ["DB"]), None)

    assert connection.email.source == "db"


def test_unreadable_store_does_not_break_environment_only_setup(monkeypatch, fake_store):
    for name, value in (("JIRA_BASE_URL", "https://env.test"), ("JIRA_EMAIL", "a@b.c"), ("JIRA_API_TOKEN", "t")):
        monkeypatch.setenv(name, value)
    store = fake_store()
    store.load_credentials = lambda: (_ for _ in ()).throw(RuntimeError("file is not a database"))

    connection = resolve_jira_connection(store, ProjectConfig("jira", "FILE"))

    assert connection.base_url.source == "env"
    assert connection.store_error == "file is not a database"
    assert connection.require_complete()[3] == "FILE"


def test_require_complete_lists_missing_fields_and_store_error(fake_store):
    store = fake_store()
    store.list_projects = lambda: (_ for _ in ()).throw(RuntimeError("boom"))

    connection = resolve_jira_connection(store, None)

    with pytest.raises(BusinessRuleViolation) as exc_info:
        connection.require_complete()

    message = str(exc_info.value)
    assert "base URL, email, API token, project key" in message
    assert "boom" in message
    assert "dwire config setup" in message
