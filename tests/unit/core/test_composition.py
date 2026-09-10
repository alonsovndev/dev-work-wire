from unittest.mock import MagicMock

from devworkwire.core.composition import Container
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider

_CONFIG = {
    "jira.base_url": "https://jira.test",
    "jira.email": "user@example.com",
    "jira.api_token": "token",
    "jira.api_version": "3",
    "jira.timeout": 15,
    "jira.max_retries": 2,
}


def _patch_config(monkeypatch):
    fake_app_config = MagicMock()
    fake_app_config.get_config.side_effect = lambda key, default=None: _CONFIG.get(key, default)
    monkeypatch.setattr("devworkwire.core.composition.AppConfig.instance", lambda: fake_app_config)

    fake_project_config = MagicMock(project_key="PROJ")
    monkeypatch.setattr(
        "devworkwire.core.composition.ProjectConfig.load", lambda: fake_project_config
    )


def test_get_jira_provider_builds_settings_from_config(monkeypatch):
    _patch_config(monkeypatch)

    provider = Container().get_jira_provider()

    assert isinstance(provider, JiraProvider)
    assert provider.settings.base_url == "https://jira.test"
    assert provider.settings.project_key == "PROJ"
    assert provider.settings.timeout == 15
    assert provider.settings.max_retries == 2


def test_get_jira_provider_is_cached(monkeypatch):
    _patch_config(monkeypatch)

    container = Container()
    first = container.get_jira_provider()
    second = container.get_jira_provider()

    assert first is second
