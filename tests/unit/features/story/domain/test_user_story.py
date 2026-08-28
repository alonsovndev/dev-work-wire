import pytest
from datetime import datetime

from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.core.domain.issue import IssueStatus
from devworkwire.features.story.domain import StoryStatus, UserStory


class TestUserStoryCreation:
    def test_create_with_required_fields(self):
        story = UserStory.create(
            key="PROJ-2",
            numeric_id=2001,
            summary="Login with Google",
            description="Allow users to login with Google",
            status=IssueStatus.TODO,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 2),
        )
        assert story.key == "PROJ-2"
        assert story.numeric_id == 2001
        assert story.summary == "Login with Google"

    def test_create_with_optional_fields(self):
        story = UserStory.create(
            key="PROJ-2",
            numeric_id=2001,
            summary="Login with Google",
            description="OAuth login",
            status=IssueStatus.IN_PROGRESS,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 2),
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
        assert story.assignee == "user1"
        assert story.priority.name == "High"
        assert len(story.labels) == 2
        assert story.story_points.value == 5
        assert story.epic_link.key == "PROJ-1"
        assert len(story.acceptance_criteria) == 2
        assert story.sprint == "Sprint 1"
        assert story.story_status == StoryStatus.OPEN


class TestUserStoryValidation:
    def test_empty_key_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            UserStory.create(
                key="",
                numeric_id=1,
                summary="Summary",
                description="Desc",
                status=IssueStatus.TODO,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

    def test_empty_summary_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            UserStory.create(
                key="PROJ-1",
                numeric_id=1,
                summary="",
                description="Desc",
                status=IssueStatus.TODO,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

    def test_negative_story_points_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            UserStory.create(
                key="PROJ-1",
                numeric_id=1,
                summary="Summary",
                description="Desc",
                status=IssueStatus.TODO,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                story_points=-1,
            )


class TestUserStoryDirectInstantiationBlocked:
    def test_direct_init_raises(self):
        with pytest.raises(TypeError):
            UserStory()


class TestUserStoryBehavior:
    def test_is_completed_when_done(self):
        story = UserStory.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Summary",
            description="Desc",
            status=IssueStatus.DONE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert story.is_completed()

    def test_is_closed_when_story_status_closed(self):
        story = UserStory.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Summary",
            description="Desc",
            status=IssueStatus.DONE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            story_status=StoryStatus.CLOSED,
        )
        assert story.is_closed()

    def test_has_epic_when_linked(self):
        story = UserStory.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Summary",
            description="Desc",
            status=IssueStatus.TODO,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            epic_key="PROJ-0",
        )
        assert story.has_epic()

    def test_has_no_epic_when_not_linked(self):
        story = UserStory.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Summary",
            description="Desc",
            status=IssueStatus.TODO,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert not story.has_epic()

    def test_string_representation(self):
        story = UserStory.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Login Feature",
            description="Desc",
            status=IssueStatus.TODO,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert str(story) == "UserStory(PROJ-1: Login Feature)"
