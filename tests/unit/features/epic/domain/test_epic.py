import pytest
from datetime import datetime

from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.core.domain.issue import IssueStatus
from devworkwire.features.epic.domain import Epic


class TestEpicCreation:
    def test_create_with_required_fields(self):
        epic = Epic.create(
            key="PROJ-1",
            numeric_id=1001,
            summary="Authentication Epic",
            description="Implement OAuth2 authentication",
            status=IssueStatus.TODO,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 2),
        )
        assert epic.key == "PROJ-1"
        assert epic.numeric_id == 1001
        assert epic.summary == "Authentication Epic"
        assert epic.description == "Implement OAuth2 authentication"
        assert epic.status == IssueStatus.TODO

    def test_create_with_optional_fields(self):
        epic = Epic.create(
            key="PROJ-1",
            numeric_id=1001,
            summary="Authentication Epic",
            description="Implement OAuth2",
            status=IssueStatus.IN_PROGRESS,
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 2),
            assignee="user1",
            reporter="user2",
            priority="High",
            labels=["backend", "security"],
            story_points=13,
            parent_key="PROJ-0",
        )
        assert epic.assignee == "user1"
        assert epic.reporter == "user2"
        assert epic.priority.name == "High"
        assert len(epic.labels) == 2
        assert epic.story_points.value == 13
        assert epic.parent.key == "PROJ-0"


class TestEpicValidation:
    def test_empty_key_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            Epic.create(
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
            Epic.create(
                key="PROJ-1",
                numeric_id=1,
                summary="",
                description="Desc",
                status=IssueStatus.TODO,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

    def test_whitespace_summary_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            Epic.create(
                key="PROJ-1",
                numeric_id=1,
                summary="   ",
                description="Desc",
                status=IssueStatus.TODO,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

    def test_negative_numeric_id_raises(self):
        with pytest.raises(BusinessRuleViolationException):
            Epic.create(
                key="PROJ-1",
                numeric_id=-1,
                summary="Summary",
                description="Desc",
                status=IssueStatus.TODO,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )


class TestEpicDirectInstantiationBlocked:
    def test_direct_init_raises(self):
        with pytest.raises(TypeError):
            Epic()


class TestEpicBehavior:
    def test_is_completed_when_done(self):
        epic = Epic.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Summary",
            description="Desc",
            status=IssueStatus.DONE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert epic.is_completed()

    def test_is_not_completed_when_in_progress(self):
        epic = Epic.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Summary",
            description="Desc",
            status=IssueStatus.IN_PROGRESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert not epic.is_completed()

    def test_string_representation(self):
        epic = Epic.create(
            key="PROJ-1",
            numeric_id=1,
            summary="Auth Epic",
            description="Desc",
            status=IssueStatus.TODO,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert str(epic) == "Epic(PROJ-1: Auth Epic)"
