import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import respx
import httpx
from typer.testing import CliRunner
from devworkwire.presentation.cli import main
from devworkwire.presentation.cli.main import app, container
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider
from devworkwire.infrastructure.external.jira.settings import JiraSettings
from devworkwire.features.import_.application.folder_state import ImportState

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

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])
    assert result.exit_code == 0
    assert "Epic: New Epic" in result.stdout
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

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])
    assert result.exit_code == 0
    assert "Stories (1):" in result.stdout
    assert "points=8" in result.stdout
    assert "Successfully created epic: PROJ-2" in result.stdout
    assert "Successfully created story: PROJ-3 (First Story)" in result.stdout
    assert json.loads(route.calls[1].request.content)["fields"]["customfield_99999"] == 8


@respx.mock
def test_preview_folder_shows_items_without_contacting_jira(monkeypatch, tmp_path):
    (tmp_path / "epic.md").write_text(
        "# Epic: Authentication\n**Priority**: High\n**Labels**: auth\n"
    )
    (tmp_path / "stories.md").write_text(
        "### US-1: Login\n**Effort Estimate**: 5\n**Labels**: auth\n"
    )
    monkeypatch.setattr(container, "get_jira_provider", lambda: pytest.fail("Jira was contacted"))

    result = runner.invoke(app, ["preview-folder", str(tmp_path)])

    assert result.exit_code == 0
    assert "Epic: Authentication" in result.stdout
    assert "priority=High" in result.stdout
    assert "Stories (1):" in result.stdout
    assert "Login (stories.md:1)" in result.stdout
    assert "points=5" in result.stdout
    assert not respx.calls


@respx.mock
def test_preview_folder_allows_empty_stories_file(tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    (tmp_path / "stories.md").write_text("")

    result = runner.invoke(app, ["preview-folder", str(tmp_path)])

    assert result.exit_code == 0
    assert "Stories (0):" in result.stdout
    assert not respx.calls


@respx.mock
def test_invalid_folder_reports_all_errors_before_any_creation(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic:\n**Labels**: bad label\n")
    (tmp_path / "stories.md").write_text(
        "### US-1: Login\n**Effort Estimate**: -2\n"
        "### US-2:\n**Labels**: bad label\n"
    )
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "Epic: (missing or invalid)" in result.output
    assert "Login (stories.md:1)" in result.output
    assert "epic.md:1: Expected '# Epic: <title>' heading" in result.output
    assert "epic.md:2: Label name cannot contain spaces" in result.output
    assert "stories.md:2: Effort Estimate must be a nonnegative integer" in result.output
    assert "stories.md:3: Expected '### <id>: <title>' heading" in result.output
    assert "stories.md:4: Label name cannot contain spaces" in result.output
    assert not route.called


@respx.mock
def test_preview_rejects_nonempty_stories_without_story_heading(tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    (tmp_path / "stories.md").write_text("## US-1: Login\n")

    result = runner.invoke(app, ["preview-folder", str(tmp_path)])

    assert result.exit_code == 1
    assert "stories.md:1: Expected '### <id>: <title>' story heading" in result.output
    assert not respx.calls


@respx.mock
def test_import_rejects_wrong_level_story_heading_after_valid_story(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    (tmp_path / "stories.md").write_text(
        "### US-1: Login\n## US-2: Logout\n"
    )
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "stories.md:2: Expected '### <id>: <title>' story heading" in result.output
    assert not route.called


@respx.mock
def test_preview_rejects_blank_story_id(tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    (tmp_path / "stories.md").write_text("###  : Login\n")

    result = runner.invoke(app, ["preview-folder", str(tmp_path)])

    assert result.exit_code == 1
    assert "stories.md:1: Expected '### <id>: <title>' heading" in result.output
    assert not respx.calls


@pytest.mark.parametrize("labels", ["", "auth,", ",auth"])
@respx.mock
def test_preview_rejects_empty_label_entries(tmp_path, labels):
    (tmp_path / "epic.md").write_text(f"# Epic: Authentication\n**Labels**: {labels}\n")

    result = runner.invoke(app, ["preview-folder", str(tmp_path)])

    assert result.exit_code == 1
    assert "epic.md:2: Label name cannot be empty" in result.output
    assert not respx.calls


@respx.mock
def test_import_folder_requires_yes_without_terminal(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path)])

    assert result.exit_code == 1
    assert "Epic: Authentication" in result.output
    assert "Use --yes" in result.output
    assert not route.called


@respx.mock
def test_import_folder_interactive_confirmation_creates(mock_config, monkeypatch, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    monkeypatch.setattr(main.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    confirm = MagicMock(return_value=True)
    monkeypatch.setattr(main.typer, "confirm", confirm)
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    assert asyncio.run(main._import_folder(str(tmp_path))) is True
    confirm.assert_called_once()
    assert route.call_count == 1


def test_import_folder_interactive_cancellation_skips_jira(monkeypatch, tmp_path, capsys):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    monkeypatch.setattr(main.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    confirm = MagicMock(return_value=False)
    monkeypatch.setattr(main.typer, "confirm", confirm)
    monkeypatch.setattr(container, "get_jira_provider", lambda: pytest.fail("Jira was contacted"))

    assert asyncio.run(main._import_folder(str(tmp_path))) is True
    confirm.assert_called_once()
    assert "Import cancelled" in capsys.readouterr().out

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
    assert "Folder not found" in result.output


@respx.mock
def test_import_folder_cmd_reports_error_when_folder_has_no_epic_file(mock_config, tmp_path):
    result = runner.invoke(app, ["import-folder", str(tmp_path)])
    assert result.exit_code == 1
    assert "epic.md:" in result.output


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

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "Error creating story 'First'" in result.output
    assert "Successfully created story: PROJ-3 (Second)" in result.output
    assert route.call_count == 3


@respx.mock
def test_import_folder_rerun_skips_every_recorded_item(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(201, json={"key": "PROJ-2"}),
    ])

    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 0
    assert "already uploaded as PROJ-1" in result.stdout
    assert "already uploaded as PROJ-2" in result.stdout
    assert route.call_count == 2
    state = json.loads((tmp_path / ".devworkwire-import.json").read_text())
    assert state["epic"]["key"] == "PROJ-1"
    assert state["stories"]["US-1"]["key"] == "PROJ-2"
    assert runner.invoke(app, ["import-folder", str(tmp_path)]).exit_code == 0
    assert route.call_count == 2


@respx.mock
def test_import_folder_resumes_only_failed_story_after_definite_rejection(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n### US-2: Second\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(400, json={"errorMessages": ["Invalid story"]}),
        httpx.Response(201, json={"key": "PROJ-3"}),
        httpx.Response(201, json={"key": "PROJ-4"}),
    ])

    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 0
    assert "Successfully created story: PROJ-4 (First)" in result.stdout
    assert route.call_count == 4


@respx.mock
def test_changed_uploaded_story_is_skipped_with_warning(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    stories = tmp_path / "stories.md"
    stories.write_text("### US-1: First\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(201, json={"key": "PROJ-2"}),
    ])
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    stories.write_text("### US-1: First changed\n")

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 0
    assert "Markdown changed since recorded attempt" in result.output
    assert route.call_count == 2


@respx.mock
def test_uncertain_story_blocks_rerun_until_resolved(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n### US-2: Second\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(500),
        httpx.Response(201, json={"key": "PROJ-3"}),
        httpx.Response(201, json={"key": "PROJ-4"}),
    ])

    first = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])
    assert first.exit_code == 1
    assert route.call_count == 2
    state = json.loads((tmp_path / ".devworkwire-import.json").read_text())
    assert state["stories"]["US-1"]["status"] == "pending"
    assert runner.invoke(app, ["preview-folder", str(tmp_path)]).exit_code == 1
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    assert route.call_count == 2

    resolved = runner.invoke(app, ["resolve-import", str(tmp_path), "--item", "US-1", "--retry"])
    assert resolved.exit_code == 0
    resumed = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])
    assert resumed.exit_code == 0
    assert route.call_count == 4


@respx.mock
def test_resolve_import_records_verified_story_key(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}), httpx.Response(500),
    ])
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    respx.get("https://jira.test/rest/api/3/issue/PROJ-2").mock(return_value=httpx.Response(
        200, json={"key": "PROJ-2", "fields": {
            "issuetype": {"name": "Story"}, "summary": "First", "parent": {"key": "PROJ-1"},
        }},
    ))

    resolved = runner.invoke(app, [
        "resolve-import", str(tmp_path), "--item", "US-1", "--key", "PROJ-2",
    ])
    assert resolved.exit_code == 0
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    assert route.call_count == 2


@respx.mock
def test_resolve_import_rejects_wrong_story_parent(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n")
    respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}), httpx.Response(500),
    ])
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    respx.get("https://jira.test/rest/api/3/issue/PROJ-2").mock(return_value=httpx.Response(
        200, json={"key": "PROJ-2", "fields": {
            "issuetype": {"name": "Story"}, "summary": "First", "parent": {"key": "PROJ-9"},
        }},
    ))

    result = runner.invoke(app, [
        "resolve-import", str(tmp_path), "--item", "US-1", "--key", "PROJ-2",
    ])
    assert result.exit_code == 1
    assert "not linked to the recorded epic" in result.output
    state = json.loads((tmp_path / ".devworkwire-import.json").read_text())
    assert state["stories"]["US-1"]["status"] == "pending"


@respx.mock
def test_bad_state_blocks_creation(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    state_path = tmp_path / ".devworkwire-import.json"
    state_path.write_text("not json")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "Cannot read" in result.output
    assert not route.called


@respx.mock
def test_duplicate_story_ids_block_creation(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n### US-1: Second\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "Duplicate story ID: US-1" in result.output
    assert not route.called


@respx.mock
def test_state_write_failure_prevents_jira_creation(mock_config, monkeypatch, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )
    def fail_save(self):
        raise OSError("disk full")

    monkeypatch.setattr(ImportState, "save", fail_save)

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "disk full" in result.output
    assert not route.called


@respx.mock
def test_failed_key_save_leaves_attempt_unresolved(mock_config, monkeypatch, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )
    original_save = ImportState.save
    save_count = 0

    def fail_after_creation(self):
        nonlocal save_count
        save_count += 1
        if save_count == 2:
            raise OSError("disk full")
        original_save(self)

    monkeypatch.setattr(ImportState, "save", fail_after_creation)

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert route.call_count == 1
    state = json.loads((tmp_path / ".devworkwire-import.json").read_text())
    assert state["epic"]["status"] == "pending"
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    assert route.call_count == 1


@respx.mock
def test_different_jira_destination_blocks_resume(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    container._jira_provider = JiraProvider(JiraSettings(
        base_url="https://other.test", project_key="PROJ", username="u", api_token="fake",
    ))
    other_route = respx.post("https://other.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-2"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "different Jira destination" in result.output
    assert not other_route.called


@respx.mock
def test_renamed_story_id_requires_rebind_before_import(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    stories = tmp_path / "stories.md"
    stories.write_text("### US-1: First\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(201, json={"key": "PROJ-2"}),
    ])
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    stories.write_text("### US-2: First\n")

    preview = runner.invoke(app, ["preview-folder", str(tmp_path)])
    blocked = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert preview.exit_code == 1
    assert "US-1: PROJ-2" in preview.output
    assert blocked.exit_code == 1
    assert "Rebind or retire" in blocked.output
    assert route.call_count == 2

    rebound = runner.invoke(app, [
        "rebind-import-story", str(tmp_path), "US-1", "US-2",
    ])
    assert rebound.exit_code == 0
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    assert route.call_count == 2


@respx.mock
def test_removed_recorded_story_can_be_retired(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    stories = tmp_path / "stories.md"
    stories.write_text("### US-1: First\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(201, json={"key": "PROJ-2"}),
        httpx.Response(201, json={"key": "PROJ-3"}),
    ])
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    stories.write_text("### US-2: Second\n")

    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    retired = runner.invoke(app, ["retire-import-story", str(tmp_path), "US-1"])
    assert retired.exit_code == 0
    resumed = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert resumed.exit_code == 0
    assert "Successfully created story: PROJ-3" in resumed.output
    assert route.call_count == 3


@respx.mock
def test_removed_pending_story_is_shown_and_can_be_cleared(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    stories = tmp_path / "stories.md"
    stories.write_text("### US-1: First\n")
    respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}), httpx.Response(500),
    ])
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    stories.write_text("")

    preview = runner.invoke(app, ["preview-folder", str(tmp_path)])
    assert preview.exit_code == 1
    assert "US-1: unresolved attempt" in preview.output
    assert runner.invoke(app, [
        "resolve-import", str(tmp_path), "--item", "US-1", "--retry",
    ]).exit_code == 0
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0


@respx.mock
def test_uncertain_epic_can_be_resolved_with_verified_key(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(500)
    )

    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    assert route.call_count == 1
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(return_value=httpx.Response(
        200, json={"key": "PROJ-1", "fields": {
            "issuetype": {"name": "Epic"}, "summary": "New Epic",
        }},
    ))

    resolved = runner.invoke(app, [
        "resolve-import", str(tmp_path), "--item", "epic", "--key", "PROJ-1",
    ])

    assert resolved.exit_code == 0
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 0
    assert route.call_count == 1


@respx.mock
def test_existing_lock_blocks_creation(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / ".devworkwire-import.lock").write_text("another process\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    result = runner.invoke(app, ["import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    assert "Folder import is locked" in result.output
    assert not route.called


@respx.mock
def test_resolution_rejects_key_already_recorded_for_another_story(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: New Epic\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n### US-2: Second\n")
    respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(201, json={"key": "PROJ-2"}),
        httpx.Response(500),
    ])
    assert runner.invoke(app, ["import-folder", str(tmp_path), "--yes"]).exit_code == 1
    respx.get("https://jira.test/rest/api/3/issue/PROJ-2").mock(return_value=httpx.Response(
        200, json={"key": "PROJ-2", "fields": {
            "issuetype": {"name": "Story"}, "summary": "First",
            "parent": {"key": "PROJ-1"},
        }},
    ))

    result = runner.invoke(app, [
        "resolve-import", str(tmp_path), "--item", "US-2", "--key", "PROJ-2",
    ])

    assert result.exit_code == 1
    assert "Jira issue keys must be unique" in result.output
    state = json.loads((tmp_path / ".devworkwire-import.json").read_text())
    assert state["stories"]["US-2"]["status"] == "pending"


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


@respx.mock
def test_json_fetch_epic_returns_structured_item(mock_config):
    respx.get("https://jira.test/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1",
            "fields": {"issuetype": {"name": "Epic"}, "summary": "Authentication"},
        })
    )

    result = runner.invoke(app, ["--format", "json", "fetch-epic", "PROJ-1"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "command": "fetch-epic", "status": "completed",
        "data": {"epic": {
            "key": "PROJ-1", "title": "Authentication", "description": "",
            "priority": None, "labels": [],
        }}, "error": None,
    }


@respx.mock
def test_json_create_epic_returns_key(mock_config):
    respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-5"})
    )

    result = runner.invoke(app, ["--format", "json", "create-epic", "--title", "Login"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["data"] == {"key": "PROJ-5", "type": "epic"}


def test_json_preview_reports_validation_errors(tmp_path):
    result = runner.invoke(app, ["--format", "json", "preview-folder", str(tmp_path)])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "VALIDATION_FAILED"
    assert payload["data"]["errors"][0]["file"] == "epic.md"


def test_json_preview_includes_content_without_jira(monkeypatch, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n**Epic Description:**\nLogin scope\n")
    monkeypatch.setattr(container, "get_jira_provider", lambda: pytest.fail("Jira was contacted"))

    result = runner.invoke(app, ["--format", "json", "preview-folder", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "preview"
    assert payload["data"]["epic"]["action"] == "create"
    assert payload["data"]["epic"]["item"]["description"] == "Login scope"
    assert payload["error"] is None


@respx.mock
def test_json_import_reports_created_and_no_change(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    route = respx.post("https://jira.test/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-1"})
    )

    first = runner.invoke(app, ["--format", "json", "import-folder", str(tmp_path), "--yes"])
    second = runner.invoke(app, ["--format", "json", "import-folder", str(tmp_path), "--yes"])

    assert first.exit_code == second.exit_code == 0
    assert json.loads(first.stdout)["status"] == "completed"
    assert json.loads(first.stdout)["data"]["created"] == [{"type": "epic", "key": "PROJ-1"}]
    assert json.loads(second.stdout)["status"] == "no_change"
    assert route.call_count == 1


@respx.mock
def test_json_import_reports_partial_result(mock_config, tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")
    (tmp_path / "stories.md").write_text("### US-1: First\n")
    respx.post("https://jira.test/rest/api/3/issue").mock(side_effect=[
        httpx.Response(201, json={"key": "PROJ-1"}),
        httpx.Response(400, json={"errorMessages": ["Invalid story"]}),
    ])

    result = runner.invoke(app, ["--format", "json", "import-folder", str(tmp_path), "--yes"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["data"]["created"] == [{"type": "epic", "key": "PROJ-1"}]
    assert payload["error"]["message"].startswith("Error creating story")


def test_json_import_requires_explicit_yes(tmp_path):
    (tmp_path / "epic.md").write_text("# Epic: Authentication\n")

    result = runner.invoke(app, ["--format", "json", "import-folder", str(tmp_path)])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "CONFIRMATION_REQUIRED"
    assert payload["data"]["epic"]["action"] == "create"


def test_json_mode_reports_argument_errors():
    result = runner.invoke(app, ["--format", "json", "create-epic"])

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "create-epic"
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert "--title" in payload["error"]["message"]
