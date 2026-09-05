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
    md_file = tmp_path / "epic.md"
    md_file.write_text("# Epic: New Epic\n**Description**: Desc\n")
    
    respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-2"})
    )
    
    result = runner.invoke(app, ["create-epic", str(md_file)])
    assert result.exit_code == 0
    assert "Successfully created epic: PROJ-2" in result.stdout

@respx.mock
def test_fetch_epic_cmd_reports_error_when_jira_is_unavailable(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-9").mock(
        return_value=httpx.Response(500)
    )
    result = runner.invoke(app, ["fetch-epic", "PROJ-9"])
    assert result.exit_code == 0
    assert "Error fetching epic:" in result.output

@respx.mock
def test_create_epic_cmd_reports_error_for_missing_markdown_file(mock_config):
    result = runner.invoke(app, ["create-epic", "does-not-exist.md"])
    assert result.exit_code == 0
    assert "Error creating epic:" in result.output
