import pytest
import respx
from datetime import datetime
from httpx import Response

from devworkwire.config.project_config import ProjectConfig
from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.core.domain.issue import IssueStatus
from devworkwire.core.domain.value_objects import IssueId, Priority
from devworkwire.features.epic.domain import Epic
from devworkwire.features.story.domain import UserStory
from devworkwire.infrastructure.external.jira.settings import JiraSettings
from devworkwire.infrastructure.external.jira.work_item_provider import (
    JiraWorkItemProvider,
)


def make_provider(project_config: ProjectConfig | None = None) -> JiraWorkItemProvider:
    settings = JiraSettings.from_dict(
        {
            "base_url": "https://test-jira.atlassian.net",
            "email": "test@example.com",
            "api_token": "test_key",
        }
    )
    if project_config is None:
        project_config = ProjectConfig(provider="jira", project_key="PROJ")
    return JiraWorkItemProvider(settings, project_config)


@pytest.fixture
def provider():
    """Fixture to create a JiraWorkItemProvider instance for testing."""
    return make_provider()


@pytest.mark.asyncio
@respx.mock
async def test_get_epic_success(provider):
    """
    Test successful retrieval of an Epic from the Jira API.
    """
    # Arrange
    epic_key = "PROJ-1"
    mock_response = {
        "id": "10001",
        "key": epic_key,
        "fields": {
            "summary": "Test Epic from API",
            "description": "A detailed description.",
            "status": {"name": "To Do"},
            "creator": {"displayName": "Test User"},
            "reporter": {"displayName": "Test User"},
            "priority": {"name": "High"},
            "labels": ["backend", "api"],
            "customfield_10011": 8.0,  # Story Points
            "created": "2025-01-01T10:00:00.000-0500",
            "updated": "2025-01-02T11:00:00.000-0500",
        },
    }

    respx.get(f"https://test-jira.atlassian.net/rest/api/3/issue/{epic_key}").mock(
        return_value=Response(200, json=mock_response)
    )

    # Act
    epic = await provider.get_epic(IssueId.from_string(epic_key))

    # Assert
    assert epic is not None
    assert isinstance(epic, Epic)
    assert epic.key == epic_key
    assert epic.summary == "Test Epic from API"
    assert epic.story_points.value == 8
    assert len(epic.labels) == 2
    assert epic.labels.has_label_named("backend")


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_success(provider):
    """
    Test successful creation of an Epic in the Jira API.
    """
    # Arrange
    epic_key = "PROJ-100"

    mock_response = {
        "id": "10001",
        "key": epic_key,
        "fields": {
            "summary": "Test Epic Creation",
            "description": "A test epic for unit testing integration with Jira.",
            "priority": {"name": "High"},
            "status": {"name": "To Do"},
            "created": "2026-01-01T10:00:00.000-0500",
            "updated": "2026-01-01T11:00:00.000-0500",
        },
    }

    respx.post("https://test-jira.atlassian.net/rest/api/3/issue").mock(
        return_value=Response(201, json=mock_response)
    )

    # Act
    epic = await provider.create_epic(
        summary="Test Epic Creation",
        description="A test epic for unit testing integration with Jira.",
    )

    # Assert
    assert epic is not None
    assert isinstance(epic, Epic)
    assert epic.key == epic_key
    assert epic.summary == "Test Epic Creation"
    assert epic.description == "A test epic for unit testing integration with Jira."
    assert epic.priority == Priority.high()
    assert epic.created_at == datetime.fromisoformat("2026-01-01T10:00:00-05:00")
    assert epic.updated_at == datetime.fromisoformat("2026-01-01T11:00:00-05:00")


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_unauthorized(provider):
    """
    Test Epic creation fails with 401 Unauthorized.
    """
    # Arrange
    respx.post("https://test-jira.atlassian.net/rest/api/3/issue").mock(
        return_value=Response(
            401, json={"errorMessages": ["Unauthorized"], "errors": {}}
        )
    )

    # Act & Assert
    with pytest.raises(BusinessRuleViolationException) as exc_info:
        await provider.create_epic(
            summary="Unauthorized Epic",
            description="Testing unauthorized response handling.",
        )

    assert "Unauthorized" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_internal_server_error(provider):
    """
    Test Epic creation fails with 500 Internal Server Error.
    """
    # Arrange
    respx.post("https://test-jira.atlassian.net/rest/api/3/issue").mock(
        return_value=Response(
            500, json={"errorMessages": ["Internal Server Error"], "errors": {}}
        )
    )

    # Act & Assert
    with pytest.raises(BusinessRuleViolationException) as exc_info:
        await provider.create_epic(
            summary="Epic causing 500",
            description="Testing internal server error handling.",
        )

    assert "Internal Server Error" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_create_epic_invalid_payload(provider):
    """
    Test Epic creation fails with 400 Bad Request due to invalid payload.
    """
    # Arrange
    respx.post("https://test-jira.atlassian.net/rest/api/3/issue").mock(
        return_value=Response(
            400,
            json={
                "errorMessages": ["Invalid payload"],
                "errors": {"summary": "Summary is required"},
            },
        )
    )

    # Act & Assert
    with pytest.raises(BusinessRuleViolationException) as exc_info:
        await provider.create_epic(
            summary="",  # Invalid because the summary is empty
            description="Epic with invalid payload.",
        )

    assert "Invalid payload" in str(exc_info.value)
    assert "Summary is required" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_get_stories_in_epic_success(provider):
    """
    Test retrieval of all user stories belonging to an epic.
    """
    # Arrange
    epic_key = "PROJ-1"
    mock_response = {
        "issues": [
            {
                "id": "20001",
                "key": "PROJ-2",
                "fields": {
                    "summary": "First story",
                    "description": "Do things",
                    "status": {"name": "In Progress"},
                    "reporter": {"displayName": "Test User"},
                    "priority": {"name": "High"},
                    "labels": ["backend"],
                    "customfield_10011": 5,
                    "created": "2026-01-01T10:00:00.000-0500",
                    "updated": "2026-01-02T11:00:00.000-0500",
                },
            },
            {
                "id": "20002",
                "key": "PROJ-3",
                "fields": {
                    "summary": "Second story",
                    "description": "Do more things",
                    "status": {"name": "Done"},
                    "created": "2026-01-01T10:00:00.000-0500",
                    "updated": "2026-01-03T11:00:00.000-0500",
                },
            },
        ]
    }

    respx.post("https://test-jira.atlassian.net/rest/api/3/search").mock(
        return_value=Response(200, json=mock_response)
    )

    # Act
    stories = await provider.get_stories_in_epic(IssueId.from_string(epic_key))

    # Assert
    assert [story.key for story in stories] == ["PROJ-2", "PROJ-3"]
    first = stories[0]
    assert isinstance(first, UserStory)
    assert first.summary == "First story"
    assert first.status == IssueStatus.IN_PROGRESS
    assert first.priority == Priority.high()
    assert first.story_points.value == 5
    assert first.epic_link is not None
    assert str(first.epic_link) == epic_key
    assert stories[1].priority is None


@pytest.mark.asyncio
@respx.mock
async def test_get_stories_in_epic_empty(provider):
    """
    Test that an epic without stories yields an empty list.
    """
    # Arrange
    respx.post("https://test-jira.atlassian.net/rest/api/3/search").mock(
        return_value=Response(200, json={"issues": []})
    )

    # Act
    stories = await provider.get_stories_in_epic(IssueId.from_string("PROJ-1"))

    # Assert
    assert stories == []


@pytest.mark.asyncio
@respx.mock
async def test_story_points_field_mapping_is_honored():
    """
    Test that a custom story-points field from field_mappings is used.
    """
    # Arrange
    provider = make_provider(
        ProjectConfig(
            provider="jira",
            project_key="PROJ",
            field_mappings={"story_points": "customfield_99999"},
        )
    )
    epic_key = "PROJ-1"
    mock_response = {
        "id": "10001",
        "key": epic_key,
        "fields": {
            "summary": "Mapped Epic",
            "description": "Uses a custom story points field.",
            "status": {"name": "To Do"},
            "customfield_10011": 99,  # default field, must be ignored
            "customfield_99999": 13,  # mapped field, must be used
            "created": "2026-01-01T10:00:00.000-0500",
            "updated": "2026-01-02T11:00:00.000-0500",
        },
    }

    respx.get(f"https://test-jira.atlassian.net/rest/api/3/issue/{epic_key}").mock(
        return_value=Response(200, json=mock_response)
    )

    # Act
    epic = await provider.get_epic(IssueId.from_string(epic_key))

    # Assert
    assert epic is not None
    assert epic.story_points.value == 13
