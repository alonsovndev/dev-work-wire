from typing import List, Optional

from .exceptions import BusinessRuleViolation
from .value_objects import IssueId, Label, Priority, StoryPoints


class UserStory:
    def __init__(
        self,
        title: str,
        description: str,
        issue_id: Optional[IssueId] = None,
        priority: Optional[Priority] = None,
        story_points: Optional[StoryPoints] = None,
        labels: Optional[List[Label]] = None,
    ):
        if not title or not title.strip():
            raise BusinessRuleViolation("UserStory title cannot be empty")
        self.title = title
        self.description = description
        self.issue_id = issue_id
        self.priority = priority
        self.story_points = story_points
        self.labels = labels or []

    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        priority: Optional[Priority] = None,
        story_points: Optional[StoryPoints] = None,
        labels: Optional[List[Label]] = None,
    ) -> "UserStory":
        return cls(
            title=title,
            description=description,
            priority=priority,
            story_points=story_points,
            labels=labels,
        )


class Epic:
    def __init__(
        self,
        title: str,
        description: str,
        issue_id: Optional[IssueId] = None,
        priority: Optional[Priority] = None,
        stories: Optional[List[UserStory]] = None,
        labels: Optional[List[Label]] = None,
    ):
        if not title or not title.strip():
            raise BusinessRuleViolation("Epic title cannot be empty")
        self.title = title
        self.description = description
        self.issue_id = issue_id
        self.priority = priority
        self.stories = stories or []
        self.labels = labels or []

    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        priority: Optional[Priority] = None,
        labels: Optional[List[Label]] = None,
    ) -> "Epic":
        return cls(
            title=title,
            description=description,
            priority=priority,
            labels=labels,
        )

    def add_story(self, story: UserStory) -> None:
        self.stories.append(story)
