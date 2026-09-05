from abc import ABC, abstractmethod
from typing import Optional
from devworkwire.core.domain import Epic

class WorkItemProvider(ABC):
    @abstractmethod
    async def fetch_epic(self, key: str) -> Optional[Epic]:
        """Fetch an Epic by its key."""
        pass

    @abstractmethod
    async def create_epic(self, epic: Epic) -> str:
        """Create an Epic and return its new issue key."""
        pass
