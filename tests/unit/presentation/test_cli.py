import pytest
from pathlib import Path
from typer.testing import CliRunner

from devworkwire.presentation import cli

runner = CliRunner()


@pytest.fixture
def record_fetch(monkeypatch):
    """Replace the epic fetch handler in the shell with a recorder."""
    calls = {}

    def fake_fetch(composition, issue_id: str):
        calls["issue_id"] = issue_id

    monkeypatch.setattr(cli, "fetch_epic", fake_fetch)
    return calls


@pytest.fixture
def record_create(monkeypatch):
    """Replace the epic create handler in the shell with a recorder."""
    calls = {}

    def fake_create(composition, file_path: str):
        calls["file_path"] = file_path

    monkeypatch.setattr(cli, "create_epic", fake_create)
    return calls


class TestDirectCommands:
    def test_help_lists_registered_commands(self):
        result = runner.invoke(cli.app, ["--help"])

        assert result.exit_code == 0
        assert "fetch-epic" in result.output
        assert "create-epic" in result.output

    def test_fetch_epic_delegates_to_handler(self, record_fetch):
        result = runner.invoke(cli.app, ["fetch-epic", "PROJ-123"])

        assert result.exit_code == 0
        assert record_fetch == {"issue_id": "PROJ-123"}

    def test_create_epic_delegates_to_handler(self, record_create):
        result = runner.invoke(cli.app, ["create-epic", "data/epic.md"])

        assert result.exit_code == 0
        assert record_create == {"file_path": "data/epic.md"}

    def test_config_option_sets_config_path(self, record_fetch, monkeypatch):
        monkeypatch.setattr(cli, "_config_path", None)

        result = runner.invoke(
            cli.app, ["--config", "custom.yml", "fetch-epic", "PROJ-123"]
        )

        assert result.exit_code == 0
        assert cli._config_path == Path("custom.yml")
