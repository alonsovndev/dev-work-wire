import pytest
from devworkwire.config.app_config import AppConfig


@pytest.fixture(autouse=True)
def reset_app_config():
    AppConfig.reset_instance()
    yield
    AppConfig.reset_instance()


def test_instance_returns_singleton():
    first = AppConfig.instance()
    second = AppConfig.instance()
    assert first is second


def test_default_environment_loads_local_config(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    config = AppConfig.instance()
    assert config.env == "local"
    assert config.get_config("logging.level") == "debug"


def test_app_env_test_loads_test_config(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    config = AppConfig.instance()
    assert config.env == "test"
    assert config.get_config("logging.level") == "info"


def test_get_config_resolves_env_interpolation(monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    config = AppConfig.instance()
    assert config.get_config("jira.base_url") == "https://example.atlassian.net"


def test_get_config_missing_key_returns_default():
    config = AppConfig.instance()
    assert config.get_config("missing.key", default="x") == "x"
