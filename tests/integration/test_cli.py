import json

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
            story_points_field="customfield_99999",
        )
    )
    yield
    container._jira_provider = None

@respx.mock
def test_fetch_epic_cmd(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1",
            "fields": {"issuetype": {"name": "Epic"}, "summary": "Test Epic", "description": "Desc"}
        })
    )
    result = runner.invoke(app, ["fetch-epic", "PROJ-1"])
    assert result.exit_code == 0
    assert "Epic: PROJ-1" in result.stdout
    assert "Test Epic" in result.stdout
    assert "Desc" in result.stdout
    assert "╔" in result.stdout

@respx.mock
def test_import_folder_cmd(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text(
        "# Epic: New Epic\n**Epic Description:**\nDesc\n"
    )

    respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-2"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully created epic: PROJ-2" in result.stdout


@respx.mock
def test_import_folder_cmd_with_stories(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text(
        "# Epic: New Epic\n**Epic Description:**\nDesc\n"
    )
    (tmp_path / "stories.md").write_text(
        "# Stories for Epic: New Epic\n\n"
        "### US-1: First Story\n"
        "**Priority**: High\n"
        "**Effort Estimate**: 8\n"
        "**As a** user,\n"
        "**I want to** log in,\n"
        "**So that** I can access my account.\n\n"
        "**Acceptance Criteria**:\n\n"
        "- [ ] Given valid credentials, when I log in, then I am authenticated.\n"
    )

    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        side_effect=[
            httpx.Response(200, json={"key": "PROJ-2"}),
            httpx.Response(200, json={"key": "PROJ-3"}),
        ]
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path)])
    assert result.exit_code == 0
    assert "Successfully created epic: PROJ-2" in result.stdout
    assert "Successfully created story: PROJ-3 (First Story)" in result.stdout
    assert json.loads(route.calls[1].request.content)["fields"]["customfield_99999"] == 8

@respx.mock
def test_fetch_epic_cmd_reports_error_when_jira_is_unavailable(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-9").mock(
        return_value=httpx.Response(500)
    )
    result = runner.invoke(app, ["fetch-epic", "PROJ-9"])
    assert result.exit_code == 1
    assert "Error fetching epic:" in result.output

@respx.mock
def test_import_folder_cmd_reports_error_for_missing_folder(mock_config):
    result = runner.invoke(app, ["import-folder", "does-not-exist"])
    assert result.exit_code == 1
    assert "Error importing folder:" in result.output
    assert "Folder not found" in result.output


@respx.mock
def test_import_folder_cmd_reports_error_when_folder_has_no_epic_file(mock_config, tmp_path):
    result = runner.invoke(app, ["import-folder", str(tmp_path)])
    assert result.exit_code == 1
    assert "Error importing folder:" in result.output


@respx.mock
def test_create_epic_cmd_creates_only_one_item(mock_config):
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-10"})
    )

    result = runner.invoke(app, [
        "create-epic", "--title", "Authentication", "--description", "Login work",
        "--priority", "High", "--label", "auth", "--label", "backend",
    ])

    assert result.exit_code == 0
    assert "Successfully created epic: PROJ-10" in result.stdout
    assert route.call_count == 1
    fields = json.loads(route.calls.last.request.content)["fields"]
    assert fields["issuetype"] == {"name": "Epic"}
    assert fields["summary"] == "Authentication"
    assert fields["labels"] == ["auth", "backend"]


@respx.mock
def test_create_story_cmd_links_existing_epic_and_sends_points(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1", "fields": {"issuetype": {"name": "Epic"}, "summary": "Authentication"}
        })
    )
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-11"})
    )

    result = runner.invoke(app, [
        "create-story", "PROJ-1", "--title", "Login", "--points", "5",
        "--description", "User can log in",
    ])

    assert result.exit_code == 0
    assert "Successfully created story: PROJ-11" in result.stdout
    fields = json.loads(route.calls.last.request.content)["fields"]
    assert fields["parent"] == {"key": "PROJ-1"}
    assert fields["customfield_99999"] == 5


@respx.mock
def test_create_story_cmd_rejects_missing_epic_without_post(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-99").mock(
        return_value=httpx.Response(404)
    )
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-11"})
    )

    result = runner.invoke(app, ["create-story", "PROJ-99", "--title", "Login"])

    assert result.exit_code == 1
    assert "Epic PROJ-99 not found" in result.output
    assert not route.called


@respx.mock
def test_fetch_story_cmd_displays_details(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-11").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-11",
            "fields": {
                "issuetype": {"name": "Story"}, "summary": "Login", "description": "Login work",
                "parent": {"key": "PROJ-1"}, "status": {"name": "To Do"},
                "customfield_99999": 5, "labels": ["auth"],
            },
        })
    )

    result = runner.invoke(app, ["fetch-story", "PROJ-11"])

    assert result.exit_code == 0
    for expected in ("Story: PROJ-11", "Login", "Login work", "Epic: PROJ-1", "Status: To Do", "Points: 5", "Labels: auth"):
        assert expected in result.stdout


@respx.mock
def test_fetch_story_cmd_rejects_wrong_type(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1", "fields": {"issuetype": {"name": "Epic"}, "summary": "Authentication"}
        })
    )

    result = runner.invoke(app, ["fetch-story", "PROJ-1"])

    assert result.exit_code == 1
    assert "not a Story" in result.output


@respx.mock
def test_fetch_story_cmd_returns_failure_when_missing(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-99").mock(
        return_value=httpx.Response(404)
    )

    result = runner.invoke(app, ["fetch-story", "PROJ-99"])

    assert result.exit_code == 1
    assert "Story PROJ-99 not found" in result.output


@respx.mock
def test_list_stories_cmd_shows_all_results(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1", "fields": {"issuetype": {"name": "Epic"}, "summary": "Authentication"}
        })
    )
    respx.post("https://jira.test/rest/api/3/search/jql").mock(
        return_value=httpx.Response(200, json={
            "issues": [
                {"key": "PROJ-2", "fields": {"issuetype": {"name": "Story"}, "summary": "Login", "status": {"name": "To Do"}}},
                {"key": "PROJ-3", "fields": {"issuetype": {"name": "Story"}, "summary": "Logout", "status": {"name": "Done"}}},
            ],
            "isLast": True,
        })
    )

    result = runner.invoke(app, ["list-stories", "PROJ-1"])

    assert result.exit_code == 0
    assert "PROJ-2  Login  [To Do]" in result.stdout
    assert "PROJ-3  Logout  [Done]" in result.stdout


@respx.mock
def test_list_stories_cmd_succeeds_for_empty_epic(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1", "fields": {"issuetype": {"name": "Epic"}, "summary": "Authentication"}
        })
    )
    respx.post("https://jira.test/rest/api/3/search/jql").mock(
        return_value=httpx.Response(200, json={"issues": [], "isLast": True})
    )

    result = runner.invoke(app, ["list-stories", "PROJ-1"])

    assert result.exit_code == 0
    assert "No stories found in epic PROJ-1" in result.stdout


@respx.mock
def test_import_folder_returns_failure_after_partial_story_creation(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n\n### US-2: Second\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(400, json={"errorMessages": ["Invalid story"]}),
        httpx.Response(201, json={"key": "PROJ-3"}),
    ])

    result = runner.invoke(app, ["import-folder", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error creating story 'First'" in result.output
    assert "Successfully created story: PROJ-3 (Second)" in result.output
    assert route.call_count == 3


@respx.mock
def test_list_assigned_cmd_shows_mixed_work_items(mock_config):
    route = respx.post("https://jira.test/rest/api/3/search/jql").mock(
        return_value=httpx.Response(200, json={
            "issues": [
                {"key": "PROJ-8", "fields": {
                    "summary": "Fix login", "issuetype": {"name": "Bug"},
                    "status": {"name": "In Progress"},
                }},
                {"key": "PROJ-9", "fields": {
                    "summary": "Write guide", "issuetype": {"name": "Task"},
                    "status": {"name": "To Do"},
                }},
            ],
            "isLast": True,
        })
    )

    result = runner.invoke(app, ["list-assigned", "--assignee", "557058:abcd-1234"])

    assert result.exit_code == 0
    assert "PROJ-8  Bug  Fix login  [In Progress]" in result.stdout
    assert "PROJ-9  Task  Write guide  [To Do]" in result.stdout
    body = json.loads(route.calls.last.request.content)
    assert 'assignee = "557058:abcd-1234"' in body["jql"]


@respx.mock
def test_list_assigned_cmd_empty_result_succeeds_for_current_user(mock_config):
    route = respx.post("https://jira.test/rest/api/3/search/jql").mock(
        return_value=httpx.Response(200, json={"issues": [], "isLast": True})
    )

    result = runner.invoke(app, ["list-assigned"])

    assert result.exit_code == 0
    assert "No open work items assigned" in result.stdout
    assert "assignee = currentUser()" in json.loads(route.calls.last.request.content)["jql"]


@respx.mock
def test_list_assigned_cmd_returns_failure_for_invalid_account_id(mock_config):
    route = respx.post("https://jira.test/rest/api/3/search/jql").mock(
        return_value=httpx.Response(200, json={"issues": [], "isLast": True})
    )

    result = runner.invoke(app, ["list-assigned", "--assignee", 'user" OR project = OTHER'])

    assert result.exit_code == 1
    assert "Invalid Jira account ID" in result.output
    assert not route.called
