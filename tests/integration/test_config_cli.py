import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from devworkwire.config.app_config import AppConfig
from devworkwire.config.paths import Paths
from devworkwire.presentation.cli import main
from devworkwire.presentation.cli.main import app

runner = CliRunner()
TOKEN = "super-secret-token-1234"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    # tests/conftest.py already points DEVWORKWIRE_CONFIG_DIR at a fresh temp dir.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Paths, "ENV_FILE_PATH", tmp_path / "missing.env")
    AppConfig.reset_instance()
    for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"):
        monkeypatch.delenv(name, raising=False)
    main.container.select_project(None)
    yield
    AppConfig.reset_instance()
    main.container.select_project(None)


def _setup(project_key="proj", token=TOKEN):
    return runner.invoke(
        app,
        ["config", "setup", "--base-url", "https://jira.test/", "--email", "me@example.com",
         "--project-key", project_key],
        input=f"{token}\n",
    )


def _show(*root_options):
    result = runner.invoke(app, ["--format", "json", *root_options, "config", "show"])
    return json.loads(result.stdout)


def test_setup_stores_connection_and_first_project_and_never_echoes_the_token():
    result = _setup()

    assert result.exit_code == 0, result.output
    assert "me@example.com" in result.output
    assert TOKEN not in result.output
    assert [(p.key, p.is_default) for p in main.container.config_store.list_projects()] == [("PROJ", True)]


def test_show_masks_token_and_reports_sources_and_projects():
    _setup()

    result = runner.invoke(app, ["--format", "json", "config", "show"])

    data = json.loads(result.stdout)["data"]
    assert data["api_token"] == {"value": "****1234", "source": "db"}
    assert data["base_url"] == {"value": "https://jira.test", "source": "db"}
    assert data["project_key"] == {"value": "PROJ", "source": "db"}
    assert data["projects"] == [{"key": "PROJ", "default": True}]
    assert TOKEN not in result.output


def test_multiple_projects_default_and_removal():
    _setup()

    added = runner.invoke(app, ["--format", "json", "config", "add-project", "other"])
    assert json.loads(added.stdout)["data"]["projects"] == [
        {"key": "PROJ", "default": True}, {"key": "OTHER", "default": False},
    ]

    runner.invoke(app, ["config", "set-default", "OTHER"])
    assert _show()["data"]["project_key"]["value"] == "OTHER"

    result = runner.invoke(app, ["config", "remove-project", "other"])
    assert "PROJ (default)" in result.stdout
    assert _show()["data"]["project_key"]["value"] == "PROJ"


def test_project_option_selects_a_configured_project_for_one_run():
    _setup()
    runner.invoke(app, ["config", "add-project", "OTHER"])

    selected = _show("--project", "other")["data"]["project_key"]
    assert selected == {"value": "OTHER", "source": "--project"}

    assert _show()["data"]["project_key"]["value"] == "PROJ"


def test_project_option_rejects_unconfigured_project():
    _setup()

    payload = _show("--project", "NOPE")

    assert payload["status"] == "error"
    assert "add-project NOPE" in payload["error"]["message"]


def test_set_default_for_unknown_project_reports_validation_error():
    _setup()

    result = runner.invoke(app, ["--format", "json", "config", "set-default", "NOPE"])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_FAILED"


def test_jira_project_key_environment_variable_does_not_override(monkeypatch):
    _setup()
    monkeypatch.setenv("JIRA_PROJECT_KEY", "ENV")

    assert _show()["data"]["project_key"] == {"value": "PROJ", "source": "db"}


def test_show_when_unconfigured_points_to_setup():
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "not set" in result.output
    assert "Projects: none configured." in result.output
    assert "dwire config setup" in result.output


def test_setup_rejects_invalid_values_without_saving():
    result = runner.invoke(
        app,
        ["config", "setup", "--base-url", "not-a-url", "--email", "me@example.com",
         "--project-key", "PROJ"],
        input=f"{TOKEN}\n",
    )

    assert result.exit_code == 1
    assert "https" in result.output
    assert main.container.config_store.load_credentials() is None
    assert main.container.config_store.list_projects() == []


def test_setup_rejects_invalid_project_key_without_saving():
    result = _setup(project_key="1-bad")

    assert result.exit_code == 1
    assert main.container.config_store.load_credentials() is None


def test_setup_keeps_stored_token_and_projects_when_rerun_with_blank_token():
    _setup()
    runner.invoke(app, ["config", "add-project", "OTHER"])

    result = _setup(project_key="third", token="")

    assert result.exit_code == 0, result.output
    assert main.container.config_store.load_credentials().api_token == TOKEN
    assert [p.key for p in main.container.config_store.list_projects()] == ["PROJ", "OTHER", "THIRD"]


def test_setup_without_token_fails_when_nothing_is_stored():
    result = _setup(token="")

    assert result.exit_code == 1
    assert main.container.config_store.load_credentials() is None


def test_setup_in_json_mode_is_refused():
    result = runner.invoke(app, ["--format", "json", "config", "setup"])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_ARGUMENT"


def test_clear_requires_confirmation_in_json_mode_and_deletes_with_yes():
    _setup()

    refused = runner.invoke(app, ["--format", "json", "config", "clear"])
    assert json.loads(refused.stdout)["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert main.container.config_store.load_credentials() is not None

    cleared = runner.invoke(app, ["--format", "json", "config", "clear", "--yes"])
    assert json.loads(cleared.stdout)["status"] == "completed"
    assert main.container.config_store.load_credentials() is None
    assert main.container.config_store.list_projects() == []


def test_clear_confirmation_declined_keeps_settings(monkeypatch, capsys):
    _setup()
    # CliRunner swaps stdin for a non-tty, so exercise the interactive branch directly.
    monkeypatch.setattr(main.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(main.typer, "confirm", lambda *args, **kwargs: False)

    assert main._config_clear(yes=False) is True

    assert "Nothing was deleted" in capsys.readouterr().out
    assert main.container.config_store.load_credentials() is not None


def test_unconfigured_command_explains_how_to_fix_it():
    result = runner.invoke(app, ["--format", "json", "fetch-epic", "PROJ-1"])

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert "dwire config setup" in payload["error"]["message"]


def test_corrupt_database_is_reported_without_crashing_show():
    main.container.config_store.db_path.parent.mkdir(parents=True, exist_ok=True)
    main.container.config_store.db_path.write_bytes(b"not a database" * 100)

    result = runner.invoke(app, ["--format", "json", "config", "show"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["data"]["base_url"] is None
    assert "could not be read" in result.stderr


def test_setup_aborted_at_a_prompt_saves_nothing_and_reports_it():
    result = runner.invoke(app, ["config", "setup"], input="")

    assert result.exit_code == 1
    assert "Aborted" in result.output
    assert main.container.config_store.load_credentials() is None
