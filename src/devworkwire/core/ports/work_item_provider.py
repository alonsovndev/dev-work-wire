from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from devworkwire.core.domain import Epic, UserStory


@dataclass(frozen=True)
class WorkItemSummary:
    key: str
    issue_type: str
    title: str
    status: str


class WorkItemProvider(ABC):
    @abstractmethod
    async def fetch_epic(self, key: str) -> Optional[Epic]:
        """Fetch an Epic by its key."""
        pass

    @abstractmethod
    async def create_epic(self, epic: Epic) -> str:
        """Create an Epic and return its new issue key."""
        pass

    @abstractmethod
    async def create_story(self, story: UserStory, epic_key: str) -> str:
        """Create a Story linked to the given Epic key and return its new issue key."""
        pass

    @abstractmethod
    async def fetch_story(self, key: str) -> Optional[UserStory]:
        """Fetch a Story by its key."""
        pass

    @abstractmethod
    async def list_stories(self, epic_key: str) -> list[UserStory]:
        """Fetch all Stories linked to an Epic."""
        pass

    @abstractmethod
    async def list_assigned_work_items(
        self, account_id: str | None = None
    ) -> list[WorkItemSummary]:
        """Fetch open work assigned to a user in the configured project."""
        pass
