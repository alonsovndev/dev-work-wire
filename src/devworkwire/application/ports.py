"""Application-level ports shared across features.

``WorkItemProvider`` is DevWorkWire's single provider boundary: every
tracker adapter (Jira today; Linear and Azure DevOps later) implements this
port, so the core service, CLI, and MCP server never need to know which
provider sits behind it.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from devworkwire.core.domain.value_objects import IssueId
from devworkwire.features.epic.domain import Epic
from devworkwire.features.story.domain import UserStory


class WorkItemProvider(ABC):
    """
    Port for reading and writing work items in a project-tracking system.

    Implemented by provider adapters (e.g. the Jira REST adapter). The
    application layer depends only on this abstraction, never on a concrete
    client.
    """

    @abstractmethod
    async def get_epic(self, issue_id: IssueId) -> Optional[Epic]:
        """
        Retrieves an Epic by its IssueId.

        Args:
            issue_id: The identifier of the Epic.

        Returns:
            The Epic entity, or None if not found.
        """

    @abstractmethod
    async def create_epic(self, summary: str, description: str) -> Epic:
        """
        Creates a new Epic in the configured project.

        Args:
            summary: The epic summary/title.
            description: The epic description.

        Returns:
            The created Epic entity, including the new ID from the provider.
        """

    @abstractmethod
    async def find_epics_by_project(self, project_key: str) -> List[Epic]:
        """
        Finds all Epics within a given project.

        Args:
            project_key: The provider project key.

        Returns:
            A list of Epic entities.
        """

    @abstractmethod
    async def get_stories_in_epic(self, epic_id: IssueId) -> List[UserStory]:
        """
        Retrieves all User Stories belonging to a specific Epic.

        Args:
            epic_id: The IssueId of the parent epic.

        Returns:
            A list of UserStory entities (empty when the epic has no stories).
        """

    @abstractmethod
    async def find_epic_by_key(self, key: str) -> Optional[Epic]:
        """Find an Epic by its provider key (e.g. ``PROJECT-123``).

        Used by the import flow to check whether an epic already exists
        before creating a duplicate.
        """

    @abstractmethod
    async def create_user_story(
        self, epic_key: str, summary: str, description: str
    ) -> UserStory:
        """Create a User Story under the given epic.

        Args:
            epic_key: Provider key of the parent epic.
            summary: Story summary/title.
            description: Story description.
        """

    @abstractmethod
    async def update_epic(
        self, issue_id: IssueId, summary: str, description: str
    ) -> Epic:
        """Update an existing Epic's summary and description.

        Args:
            issue_id: The identifier of the Epic to update.
            summary: New summary.
            description: New description.
        """
