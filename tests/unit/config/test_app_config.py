from pathlib import Path

import pytest
from devworkwire.config.app_config import AppConfig
from devworkwire.config.paths import Paths


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
    monkeypatch.setattr(Paths, "ENV_FILE_PATH", Path("/nonexistent/.env"))
    config = AppConfig.instance()
    assert config.env == "local"
    assert config.get_config("logging.level") == "DEBUG"


def test_app_env_test_loads_test_config(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    config = AppConfig.instance()
    assert config.env == "test"
    assert config.get_config("logging.level") == "INFO"


def test_get_config_resolves_env_interpolation(monkeypatch, tmp_path):
    (tmp_path / "config_local.yml").write_text(
        "jira:\n  base_url: !ENV ${JIRA_BASE_URL}\n", encoding="utf-8"
    )
    monkeypatch.setattr(Paths, "CONFIG_DIR", tmp_path)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(Paths, "ENV_FILE_PATH", Path("/nonexistent/.env"))
    monkeypatch.setenv("JIRA_BASE_URL", "https://example.atlassian.net")
    config = AppConfig.instance()
    assert config.get_config("jira.base_url") == "https://example.atlassian.net"


def test_default_config_loads_without_jira_environment_variables(monkeypatch):
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(Paths, "ENV_FILE_PATH", Path("/nonexistent/.env"))
    assert AppConfig.instance().get_config("jira.timeout") == 30


def test_get_config_missing_key_returns_default():
    config = AppConfig.instance()
    assert config.get_config("missing.key", default="x") == "x"
