import httpx
import pytest
import respx

from devworkwire.core.domain import Epic, Priority
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
