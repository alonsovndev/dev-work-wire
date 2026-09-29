import json

import httpx
import pytest
import respx

from devworkwire.core.domain import Epic, Label, Priority, StoryPoints, UserStory
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
                    "issuetype": {"name": "Epic"},
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
                    "issuetype": {"name": "Epic"},
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
        return_value=httpx.Response(200, json={"key": "PROJ-9", "fields": {"summary": "S", "issuetype": {"name": "Epic"}}})
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
            httpx.Response(200, json={"key": "PROJ-1", "fields": {"summary": "Recovered", "issuetype": {"name": "Epic"}}}),
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


@pytest.mark.asyncio
@respx.mock
async def test_fetch_epic_rejects_story(provider):
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-8").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-8", "fields": {"issuetype": {"name": "Story"}, "summary": "A story"}
        })
    )

    with pytest.raises(ValueError, match="not an Epic"):
        await provider.fetch_epic("PROJ-8")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_story_maps_parent_status_and_points(settings):
    provider = JiraProvider(JiraSettings(**{
        **settings.__dict__, "story_points_field": "customfield_99999"
    }))
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-8").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-8",
            "fields": {
                "issuetype": {"name": "Story"}, "summary": "Build login",
                "description": {"type": "doc", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Acceptance criteria"}]}
                ]},
                "parent": {"key": "PROJ-1"}, "status": {"name": "In Progress"},
                "priority": {"name": "High"}, "labels": ["auth"],
                "customfield_99999": 5.0,
            },
        })
    )

    story = await provider.fetch_story("PROJ-8")

    assert story.issue_id.key == "PROJ-8"
    assert story.title == "Build login"
    assert story.description == "Acceptance criteria"
    assert story.epic_key == "PROJ-1"
    assert story.status == "In Progress"
    assert story.story_points.value == 5
    assert story.priority.name == "High"
    assert [label.name for label in story.labels] == ["auth"]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_story_rejects_epic(provider):
    respx.get("https://jira.example.com/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={
            "key": "PROJ-1", "fields": {"issuetype": {"name": "Epic"}, "summary": "An epic"}
        })
    )

    with pytest.raises(ValueError, match="not a Story"):
        await provider.fetch_story("PROJ-1")


@pytest.mark.asyncio
@respx.mock
async def test_create_story_sends_configured_points_field(settings):
    provider = JiraProvider(JiraSettings(**{
        **settings.__dict__, "story_points_field": "customfield_99999"
    }))
    route = respx.post("https://jira.example.com/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"key": "PROJ-8"})
    )
    story = UserStory.create(title="Build login", description="", story_points=StoryPoints(0))

    await provider.create_story(story, "PROJ-1")

    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["customfield_99999"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_list_stories_reads_all_pages(settings):
    provider = JiraProvider(JiraSettings(**{
        **settings.__dict__, "story_points_field": "customfield_99999"
    }))
    route = respx.post("https://jira.example.com/rest/api/3/search/jql").mock(
        side_effect=[
            httpx.Response(200, json={
                "issues": [{"key": "PROJ-2", "fields": {
                    "issuetype": {"name": "Story"}, "summary": "First", "status": {"name": "To Do"},
                    "customfield_99999": 0.5,
                }}], "nextPageToken": "page-two", "isLast": False,
            }),
            httpx.Response(200, json={
                "issues": [{"key": "PROJ-3", "fields": {
                    "issuetype": {"name": "Story"}, "summary": "Second", "status": {"name": "Done"}
                }}], "isLast": True,
            }),
        ]
    )

    stories = await provider.list_stories("PROJ-1")

    assert [story.issue_id.key for story in stories] == ["PROJ-2", "PROJ-3"]
    assert stories[0].story_points is None
    assert route.call_count == 2
    first = json.loads(route.calls[0].request.content)
    second = json.loads(route.calls[1].request.content)
    assert first["jql"] == 'parent = "PROJ-1" AND issuetype = Story ORDER BY key ASC'
    assert first["fields"] == ["summary", "issuetype", "status"]
    assert second["nextPageToken"] == "page-two"


@pytest.mark.asyncio
async def test_list_stories_rejects_invalid_key(provider):
    with pytest.raises(ValueError, match="Invalid Jira issue key"):
        await provider.list_stories('PROJ-1" OR project = PROJ')


@pytest.mark.asyncio
@respx.mock
async def test_list_assigned_work_items_defaults_to_current_user(provider):
    route = respx.post("https://jira.example.com/rest/api/3/search/jql").mock(
        return_value=httpx.Response(200, json={"issues": [], "isLast": True})
    )

    work_items = await provider.list_assigned_work_items()

    assert work_items == []
    body = json.loads(route.calls.last.request.content)
    assert body["jql"] == (
        'project = "PROJ" AND assignee = currentUser() '
        "AND statusCategory != Done ORDER BY updated DESC, key ASC"
    )
    assert body["fields"] == ["summary", "issuetype", "status"]


@pytest.mark.asyncio
@respx.mock
async def test_list_assigned_work_items_maps_all_types_across_pages(provider):
    route = respx.post("https://jira.example.com/rest/api/3/search/jql").mock(
        side_effect=[
            httpx.Response(200, json={
                "issues": [{"key": "PROJ-2", "fields": {
                    "summary": "Fix login", "issuetype": {"name": "Bug"},
                    "status": {"name": "In Progress"},
                }}],
                "nextPageToken": "page-two", "isLast": False,
            }),
            httpx.Response(200, json={
                "issues": [{"key": "PROJ-3", "fields": {
                    "summary": "Write guide", "issuetype": {"name": "Task"},
                    "status": {"name": "To Do"},
                }}],
                "isLast": True,
            }),
        ]
    )

    work_items = await provider.list_assigned_work_items("557058:abcd-1234")

    assert [(item.key, item.issue_type, item.title, item.status) for item in work_items] == [
        ("PROJ-2", "Bug", "Fix login", "In Progress"),
        ("PROJ-3", "Task", "Write guide", "To Do"),
    ]
    assert route.call_count == 2
    first = json.loads(route.calls[0].request.content)
    second = json.loads(route.calls[1].request.content)
    assert 'assignee = "557058:abcd-1234"' in first["jql"]
    assert second["nextPageToken"] == "page-two"


@pytest.mark.asyncio
@respx.mock
async def test_list_assigned_work_items_rejects_unsafe_account_id(provider):
    route = respx.post("https://jira.example.com/rest/api/3/search/jql").mock(
        return_value=httpx.Response(200, json={"issues": [], "isLast": True})
    )

    with pytest.raises(ValueError, match="Invalid Jira account ID"):
        await provider.list_assigned_work_items('user" OR project = OTHER')

    assert not route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_assigned_work_items_reports_jira_failure(provider):
    respx.post("https://jira.example.com/rest/api/3/search/jql").mock(
        return_value=httpx.Response(403, json={"errorMessages": ["No permission"]})
    )

    with pytest.raises(httpx.HTTPStatusError, match="No permission"):
        await provider.list_assigned_work_items()
