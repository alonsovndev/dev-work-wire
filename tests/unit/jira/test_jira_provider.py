import pytest
import respx
import httpx
from devworkwire.infrastructure.external.jira.jira_provider import JiraProvider
from devworkwire.core.domain import Epic, Priority

@pytest.fixture
def provider():
    return JiraProvider("https://jira.example.com", "user", "token", "PROJ")

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
                    "labels": ["lbl1"]
                }
            }
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
