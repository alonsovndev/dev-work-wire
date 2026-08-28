"""Issue concepts shared across all features.

``IssueType`` and ``IssueStatus`` describe any Jira issue regardless of the
feature it belongs to, so they live in the shared kernel rather than in a
specific feature module.
"""

from enum import Enum

from devworkwire.core.domain.exceptions import InvalidStatusTransitionException


class IssueType(str, Enum):
    EPIC = "epic"
    USER_STORY = "story"
    TASK = "task"
    BUG = "bug"


class IssueStatus(str, Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"

    @classmethod
    def from_jira_status(cls, status: str) -> "IssueStatus":
        """Maps Jira status category to IssueStatus."""
        status_lower = status.lower()
        if (
            "done" in status_lower
            or "closed" in status_lower
            or "resolved" in status_lower
        ):
            return cls.DONE
        elif "progress" in status_lower or "review" in status_lower:
            return cls.IN_PROGRESS
        elif (
            "to do" in status_lower
            or "open" in status_lower
            or "backlog" in status_lower
        ):
            return cls.TODO
        raise InvalidStatusTransitionException(
            entity_key="",
            current_status=status,
            target_status=status,
            valid_transitions=[e.value for e in cls],
        )
