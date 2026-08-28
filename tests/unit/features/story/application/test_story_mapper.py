from datetime import datetime

from devworkwire.core.domain.issue import IssueStatus
from devworkwire.features.story.application.mappers import StoryDataMapper
from devworkwire.features.story.domain import StoryStatus, UserStory


def test_to_dto_maps_all_fields():
    created = datetime(2026, 1, 1, 10, 0, 0)
    updated = datetime(2026, 1, 2, 11, 0, 0)
    story = UserStory.create(
        key="PROJ-2",
        numeric_id=2001,
        summary="Login with Google",
        description="OAuth login",
        status=IssueStatus.IN_PROGRESS,
        created_at=created,
        updated_at=updated,
        assignee="user1",
        reporter="user2",
        priority="High",
        labels=["frontend", "auth"],
        story_points=5,
        epic_key="PROJ-1",
        acceptance_criteria=["User can login", "Session persists"],
        sprint="Sprint 1",
        story_status=StoryStatus.OPEN,
    )

    dto = StoryDataMapper.to_dto(story)

    assert dto.key == "PROJ-2"
    assert dto.numeric_id == 2001
    assert dto.summary == "Login with Google"
    assert dto.description == "OAuth login"
    assert dto.status == "In Progress"
    assert dto.assignee == "user1"
    assert dto.reporter == "user2"
    assert dto.priority == "High"
    assert dto.labels == ["frontend", "auth"]
    assert dto.story_points == 5
    assert dto.epic_key == "PROJ-1"
    assert dto.acceptance_criteria == ["User can login", "Session persists"]
    assert dto.sprint == "Sprint 1"
    assert dto.created_at == created
    assert dto.updated_at == updated


def test_to_dto_handles_missing_optional_fields():
    created = datetime(2026, 1, 1)
    story = UserStory.create(
        key="PROJ-3",
        numeric_id=3,
        summary="Bare story",
        description="Desc",
        status=IssueStatus.TODO,
        created_at=created,
        updated_at=created,
    )

    dto = StoryDataMapper.to_dto(story)

    assert dto.assignee is None
    assert dto.reporter is None
    assert dto.priority is None
    assert dto.labels == []
    assert dto.story_points is None
    assert dto.epic_key is None
    assert dto.acceptance_criteria == []
    assert dto.sprint is None
