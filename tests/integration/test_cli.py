import pytest
import respx
import httpx
from typer.testing import CliRunner
from devworkwire.presentation.cli.main import app, container
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider

runner = CliRunner()

@pytest.fixture
def mock_config():
    container._jira_provider = JiraProvider(
        base_url="https://jira.test", project_key="PROJ", username="u", api_token="fake-token"
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
    assert "Epic Found: Test Epic" in result.stdout

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
