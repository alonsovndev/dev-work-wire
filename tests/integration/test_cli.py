import pytest
import respx
import httpx
from typer.testing import CliRunner
from devworkwire.presentation.cli.main import app, container
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider
from devworkwire.infrastructure.external.jira.settings import JiraSettings

runner = CliRunner()

@pytest.fixture
def mock_config():
    container._jira_provider = JiraProvider(
        JiraSettings(
            base_url="https://jira.test",
            project_key="PROJ",
            username="u",
            api_token="fake-token",
            max_retries=1,
        )
    )
    yield
    container._jira_provider = None

@respx.mock
def test_fetch_epic_cmd(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1",
            "fields": {"summary": "Test Epic", "description": "Desc"}
        })
    )
    result = runner.invoke(app, ["fetch-epic", "PROJ-1"])
    assert result.exit_code == 0
    assert "Epic: PROJ-1" in result.stdout
    assert "Test Epic" in result.stdout
    assert "Desc" in result.stdout
    assert "╔" in result.stdout

@respx.mock
def test_create_epic_cmd(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text(
        "# Epic: New Epic\n**Epic Description:**\nDesc\n"
    )

    respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-2"})
    )

    result = runner.invoke(app, ["create-epic", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully created epic: PROJ-2" in result.stdout


@respx.mock
def test_create_epic_cmd_with_stories(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text(
        "# Epic: New Epic\n**Epic Description:**\nDesc\n"
    )
    (tmp_path / "stories.md").write_text(
        "# Stories for Epic: New Epic\n\n"
        "### US-1: First Story\n"
        "**Priority**: High\n"
        "**As a** user,\n"
        "**I want to** log in,\n"
        "**So that** I can access my account.\n\n"
        "**Acceptance Criteria**:\n\n"
        "- [ ] Given valid credentials, when I log in, then I am authenticated.\n"
    )

    respx.post("https://jira.test/rest/api/3/issue").mock(
        side_effect=[
            httpx.Response(200, json={"key": "PROJ-2"}),
            httpx.Response(200, json={"key": "PROJ-3"}),
        ]
    )

    result = runner.invoke(app, ["create-epic", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully created epic: PROJ-2" in result.stdout
    assert "Successfully created story: PROJ-3 (First Story)" in result.stdout

@respx.mock
def test_fetch_epic_cmd_reports_error_when_jira_is_unavailable(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-9").mock(
        return_value=httpx.Response(500)
    )
    result = runner.invoke(app, ["fetch-epic", "PROJ-9"])
    assert result.exit_code == 0
    assert "Error fetching epic:" in result.output

@respx.mock
def test_create_epic_cmd_reports_error_for_missing_folder(mock_config):
    result = runner.invoke(app, ["create-epic", "does-not-exist"])
    assert result.exit_code == 0
    assert "Error creating epic:" in result.output
    assert "Folder not found" in result.output


@respx.mock
def test_create_epic_cmd_reports_error_when_folder_has_no_epic_file(mock_config, tmp_path):
    result = runner.invoke(app, ["create-epic", str(tmp_path)])
    assert result.exit_code == 0
    assert "Error creating epic:" in result.output
