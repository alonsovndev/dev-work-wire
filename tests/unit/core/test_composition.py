from unittest.mock import MagicMock

import pytest

from devworkwire.config.project_config import ProjectConfig
from devworkwire.core.composition import Container
from devworkwire.core.domain.exceptions import BusinessRuleViolation
from devworkwire.core.ports.jira_config_store import JiraCredentials
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider

_CONFIG = {
    "jira.api_version": "3",
    "jira.timeout": 15,
    "jira.max_retries": 2,
}
CREDENTIALS = JiraCredentials("https://jira.test", "user@example.com", "token")


def _patch_config(monkeypatch, project_config=None):
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    fake_app_config = MagicMock()
    fake_app_config.get_config.side_effect = lambda key, default=None: _CONFIG.get(key, default)
    monkeypatch.setattr("devworkwire.core.composition.AppConfig.instance", lambda: fake_app_config)
    monkeypatch.setattr(
        "devworkwire.core.composition.ProjectConfig.load_if_present", lambda: project_config
    )


def test_get_jira_provider_builds_settings_from_stored_config(monkeypatch, fake_store):
    _patch_config(monkeypatch, ProjectConfig("jira", None, {"story_points": "customfield_99999"}))

    provider = Container(fake_store(CREDENTIALS, ["PROJ"])).get_jira_provider()

    assert isinstance(provider, JiraProvider)
    assert provider.settings.base_url == "https://jira.test"
    assert provider.settings.username == "user@example.com"
    assert provider.settings.project_key == "PROJ"
    assert provider.settings.timeout == 15
    assert provider.settings.max_retries == 2
    assert provider.settings.story_points_field == "customfield_99999"


def test_get_jira_provider_uses_default_story_points_field_without_project_file(monkeypatch, fake_store):
    _patch_config(monkeypatch)

    provider = Container(fake_store(CREDENTIALS, ["PROJ"])).get_jira_provider()

    assert provider.settings.story_points_field == "customfield_10011"


def test_select_project_overrides_the_default(monkeypatch, fake_store):
    _patch_config(monkeypatch)
    container = Container(fake_store(CREDENTIALS, ["PROJ", "OTHER"]))
    assert container.get_jira_provider().settings.project_key == "PROJ"

    container.select_project("other")

    assert container.get_jira_provider().settings.project_key == "OTHER"


def test_select_project_rejects_unconfigured_project(monkeypatch, fake_store):
    _patch_config(monkeypatch)
    container = Container(fake_store(CREDENTIALS, ["PROJ"]))
    container.select_project("NOPE")

    with pytest.raises(BusinessRuleViolation, match="add-project NOPE"):
        container.get_jira_provider()


def test_get_jira_provider_takes_project_key_from_project_file_when_no_projects_stored(
    monkeypatch, fake_store
):
    _patch_config(monkeypatch, ProjectConfig("jira", "FILE"))
    monkeypatch.setenv("JIRA_BASE_URL", "https://jira.test")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")

    provider = Container(fake_store()).get_jira_provider()

    assert provider.settings.project_key == "FILE"


def test_get_jira_provider_reports_missing_configuration(monkeypatch, fake_store):
    _patch_config(monkeypatch)

    with pytest.raises(BusinessRuleViolation, match="dwire config setup"):
        Container(fake_store()).get_jira_provider()


def test_get_jira_provider_is_cached(monkeypatch, fake_store):
    _patch_config(monkeypatch)

    container = Container(fake_store(CREDENTIALS, ["PROJ"]))
    first = container.get_jira_provider()
    second = container.get_jira_provider()

    assert first is second
