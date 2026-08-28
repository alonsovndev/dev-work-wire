from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from devworkwire.core.domain.issue import IssueStatus, IssueType
from devworkwire.core.domain.value_objects import (
    IssueId,
    StoryPoints,
    Priority,
    LabelSet,
)
from devworkwire.core.domain.exceptions import BusinessRuleViolationException


class StoryStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"


@dataclass
class UserStory:
    """
    Domain entity representing a Jira User Story.

    A User Story describes a feature from the end-user's perspective.
    Use the factory method `create()` to instantiate.
    """

    id: IssueId
    summary: str
    description: str
    status: IssueStatus
    created_at: datetime
    updated_at: datetime
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    priority: Optional[Priority] = None
    labels: LabelSet = field(default_factory=LabelSet.empty)
    story_points: Optional[StoryPoints] = None
    epic_link: Optional[IssueId] = None
    acceptance_criteria: List[str] = field(default_factory=list)
    sprint: Optional[str] = None
    story_status: Optional[StoryStatus] = None

    # Prevent direct instantiation
    def __init__(self, *args, **kwargs):
        raise TypeError("Use UserStory.create() to instantiate UserStory")

    @classmethod
    def create(
        cls,
        key: str,
        numeric_id: int,
        summary: str,
        description: str,
        status: IssueStatus,
        created_at: datetime,
        updated_at: datetime,
        assignee: Optional[str] = None,
        reporter: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        story_points: Optional[int] = None,
        epic_key: Optional[str] = None,
        acceptance_criteria: Optional[List[str]] = None,
        sprint: Optional[str] = None,
        story_status: Optional[StoryStatus] = None,
    ) -> "UserStory":
        """
        Factory method to create a UserStory instance.

        Args:
            key: Jira issue key (e.g., "PROJ-124")
            numeric_id: Jira numeric issue ID
            summary: Story title/summary
            description: Story description
            status: Current status
            created_at: Creation timestamp
            updated_at: Last update timestamp
            assignee: Assignee username (optional)
            reporter: Reporter username (optional)
            priority: Priority name from Jira (optional)
            labels: List of label names (optional)
            story_points: Story point estimate (optional)
            epic_key: Parent epic key (optional)
            acceptance_criteria: List of acceptance criteria (optional)
            sprint: Sprint name (optional)
            story_status: Story-specific status (optional)

        Returns:
            New UserStory instance

        Raises:
            BusinessRuleViolationException: If required fields are missing or invalid
        """
        if not key:
            raise BusinessRuleViolationException(
                "UserStory key is required", details="key cannot be empty"
            )
        if not summary or not summary.strip():
            raise BusinessRuleViolationException(
                "UserStory summary is required", entity_key=key
            )
        if numeric_id < 0:
            raise BusinessRuleViolationException(
                "Numeric ID must be non-negative", entity_key=key
            )
        if story_points is not None and story_points < 0:
            raise BusinessRuleViolationException(
                "Story points must be non-negative", entity_key=key
            )

        return cls._create(
            id=IssueId(key=key, numeric_id=numeric_id),
            summary=summary,
            description=description,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            assignee=assignee,
            reporter=reporter,
            priority=Priority.from_jira_name(priority) if priority else None,
            labels=LabelSet.from_list(labels) if labels else LabelSet.empty(),
            story_points=StoryPoints.from_optional(story_points),
            epic_link=IssueId.from_string(epic_key) if epic_key else None,
            acceptance_criteria=acceptance_criteria or [],
            sprint=sprint,
            story_status=story_status,
        )

    @classmethod
    def _create(
        cls,
        id: IssueId,
        summary: str,
        description: str,
        status: IssueStatus,
        created_at: datetime,
        updated_at: datetime,
        assignee: Optional[str] = None,
        reporter: Optional[str] = None,
        priority: Optional[Priority] = None,
        labels: Optional[LabelSet] = None,
        story_points: Optional[StoryPoints] = None,
        epic_link: Optional[IssueId] = None,
        acceptance_criteria: Optional[List[str]] = None,
        sprint: Optional[str] = None,
        story_status: Optional[StoryStatus] = None,
    ) -> "UserStory":
        """Internal factory for pre-constructed value objects."""
        instance = object.__new__(cls)
        instance.id = id
        instance.summary = summary
        instance.description = description
        instance.status = status
        instance.created_at = created_at
        instance.updated_at = updated_at
        instance.assignee = assignee
        instance.reporter = reporter
        instance.priority = priority
        instance.labels = labels if labels is not None else LabelSet.empty()
        instance.story_points = story_points
        instance.epic_link = epic_link
        instance.acceptance_criteria = acceptance_criteria or []
        instance.sprint = sprint
        instance.story_status = story_status
        return instance

    @property
    def key(self) -> str:
        return self.id.key

    @property
    def numeric_id(self) -> int:
        return self.id.numeric_id

    @property
    def issue_type(self) -> IssueType:
        return IssueType.USER_STORY

    def is_completed(self) -> bool:
        return self.status == IssueStatus.DONE

    def is_closed(self) -> bool:
        return self.story_status == StoryStatus.CLOSED

    def has_epic(self) -> bool:
        return self.epic_link is not None

    def __str__(self) -> str:
        return f"UserStory({self.key}: {self.summary})"
