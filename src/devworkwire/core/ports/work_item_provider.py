from abc import ABC, abstractmethod
from typing import Optional
from devworkwire.core.domain import Epic, UserStory

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
