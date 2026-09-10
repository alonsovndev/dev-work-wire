import json

import httpx
import pytest
import respx

from devworkwire.core.domain import Epic, Label, Priority, UserStory
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider
from devworkwire.infrastructure.external.jira.settings import JiraSettings


@pytest.fixture
def settings():
    return JiraSettings(
        base_url="https://jira.example.com",
        username="user",
        api_token="token",
        project_key="PROJ",
        max_retries=1,
    )


@pytest.fixture
def provider(settings):
    return JiraProvider(settings)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic(provider):
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(
            200,
            json={
                "key": "PROJ-1",
                "fields": {
                    "summary": "Epic summary",
                    "description": "Epic description",
                    "priority": {"name": "High"},
                    "labels": ["lbl1"],
                },
            },
        )
    )

    epic = await provider.fetch_epic("PROJ-1")
    assert epic is not None
    assert epic.title == "Epic summary"
    assert epic.priority.name == "High"
    assert len(epic.labels) == 1
    assert epic.labels[0].name == "lbl1"
    assert epic.issue_id.key == "PROJ-1"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic_extracts_plain_text_from_adf_description(provider):
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-4").mock(
        return_value=httpx.Response(
            200,
            json={
                "key": "PROJ-4",
                "fields": {
                    "summary": "ADF Epic",
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Intro paragraph."}],
                            },
                            {
                                "type": "bulletList",
                                "content": [
                                    {
                                        "type": "listItem",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": "First item"}
                                                ],
                                            }
                                        ],
                                    },
                                    {
                                        "type": "listItem",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": "Second item"}
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                },
            },
        )
    )

    epic = await provider.fetch_epic("PROJ-4")

    assert epic is not None
    assert "{" not in epic.description
    assert "Intro paragraph." in epic.description
    assert "- First item" in epic.description
    assert "- Second item" in epic.description


@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic_not_found(provider):
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-2").mock(
        return_value=httpx.Response(404)
    )
    epic = await provider.fetch_epic("PROJ-2")
    assert epic is None


@pytest.mark.asyncio
@respx.mock
async def test_create_epic(provider):
    respx.post("https://jira.example.com/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-3"})
    )
    epic = Epic.create(title="New Epic", description="Desc", priority=Priority.from_jira_name("Medium"))
    key = await provider.create_epic(epic)
    assert key == "PROJ-3"


@pytest.mark.asyncio
@respx.mock
async def test_create_story_links_to_parent_epic(provider):
    route = respx.post("https://jira.example.com/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-4"})
    )
    story = UserStory.create(
        title="New Story",
        description="Desc",
        priority=Priority.from_jira_name("High"),
        labels=[Label(name="backend")],
    )

    key = await provider.create_story(story, epic_key="PROJ-3")

    assert key == "PROJ-4"
    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["issuetype"] == {"name": "Story"}
    assert body["fields"]["parent"] == {"key": "PROJ-3"}
    assert body["fields"]["summary"] == "New Story"
    assert body["fields"]["priority"] == {"name": "High"}
    assert body["fields"]["labels"] == ["backend"]


@pytest.mark.asyncio
@respx.mock
async def test_create_story_renders_markdown_description_as_rich_text(provider):
    route = respx.post("https://jira.example.com/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-7"})
    )
    story = UserStory.create(
        title="New Story",
        description="**As a** user,\n**So that** I benefit.\n\n**Acceptance Criteria**:\n- [ ] It works.",
    )

    await provider.create_story(story, epic_key="PROJ-3")

    body = json.loads(route.calls.last.request.content)
    description = body["fields"]["description"]
    assert description["type"] == "doc"
    text_nodes = [node for node in description["content"] if node["type"] == "paragraph"]
    assert {"type": "text", "text": "As a", "marks": [{"type": "strong"}]} in text_nodes[0]["content"]
    checklist = next(node for node in description["content"] if node["type"] == "bulletList")
    item_text_nodes = checklist["content"][0]["content"][0]["content"]
    assert item_text_nodes[0] == {"type": "text", "text": "☐ "}
    assert item_text_nodes[1] == {"type": "text", "text": "It works."}
    assert "**" not in json.dumps(description)
    assert "- [ ]" not in json.dumps(description)


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_maps_moscow_priority_to_jira_scheme(provider):
    route = respx.post("https://jira.example.com/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-5"})
    )
    epic = Epic.create(title="New Epic", description="Desc", priority=Priority.from_jira_name("Must Have"))

    await provider.create_epic(epic)

    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["priority"] == {"name": "Highest"}


@pytest.mark.asyncio
@respx.mock
async def test_create_story_maps_moscow_priority_to_jira_scheme(provider):
    route = respx.post("https://jira.example.com/rest/api/3/issue").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-6"})
    )
    story = UserStory.create(title="New Story", description="Desc", priority=Priority.from_jira_name("Could Have"))

    await provider.create_story(story, epic_key="PROJ-5")

    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["priority"] == {"name": "Medium"}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic_uses_configured_api_version():
    settings = JiraSettings(
        base_url="https://jira.example.com",
        username="user",
        api_token="token",
        project_key="PROJ",
        api_version="2",
        max_retries=1,
    )
    route = respx.get("https://jira.example.com/rest/api/2/issue/PROJ-9").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-9", "fields": {"summary": "S"}})
    )

    epic = await JiraProvider(settings).fetch_epic("PROJ-9")

    assert route.called
    assert epic.title == "S"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic_retries_on_transient_error_then_succeeds():
    settings = JiraSettings(
        base_url="https://jira.example.com",
        username="user",
        api_token="token",
        project_key="PROJ",
        max_retries=2,
    )
    route = respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"key": "PROJ-1", "fields": {"summary": "Recovered"}}),
        ]
    )

    epic = await JiraProvider(settings).fetch_epic("PROJ-1")

    assert epic.title == "Recovered"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic_gives_up_after_max_retries(provider):
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(503)
    )

    with pytest.raises(httpx.HTTPStatusError):
        await provider.fetch_epic("PROJ-1")


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_error_includes_jira_field_validation_detail(provider):
    respx.post("https://jira.example.com/rest/api/3/issue").mock(
        return_value=httpx.Response(
            400,
            json={
                "errorMessages": [],
                "errors": {"priority": "Priority name 'Must Have' is not on the appropriate screen, or is not a valid priority."},
            },
        )
    )
    epic = Epic.create(title="New Epic", description="Desc", priority=Priority.from_jira_name("Must Have"))

    with pytest.raises(httpx.HTTPStatusError, match="priority: Priority name 'Must Have'"):
        await provider.create_epic(epic)
