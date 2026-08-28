from devworkwire.application.ports import WorkItemProvider
from devworkwire.core.domain.exceptions import EntityNotFoundException
from devworkwire.core.domain.value_objects import IssueId
from devworkwire.features.epic.application.dtos import EpicDtoResponse
from devworkwire.features.epic.application.mappers import EpicDataMapper


class GetEpicWithStories:
    """
    Use case to retrieve an Epic and all its associated User Stories.

    This use case orchestrates fetching an epic and its child stories and
    mapping them to a data transfer object (DTO). Both reads go through the
    single WorkItemProvider port, reflecting that an epic aggregate is read
    together with its stories.
    """

    def __init__(self, provider: WorkItemProvider):
        """
        Initializes the use case with a work-item provider.

        Args:
            provider: A concrete implementation of the WorkItemProvider port.
        """
        self.provider = provider

    async def execute(self, epic_key: str) -> EpicDtoResponse:
        """
        Executes the use case.

        Args:
            epic_key: The key of the epic to retrieve (e.g., "PROJ-123").

        Returns:
            An EpicDtoResponse containing the epic and its user stories.

        Raises:
            EntityNotFoundException: If the epic with the given key does not exist.
        """
        epic_id = IssueId.from_string(epic_key)

        # 1. Fetch the Epic from the provider
        epic = await self.provider.get_epic(epic_id)

        if not epic:
            raise EntityNotFoundException("Epic", epic_key)

        # 2. Fetch all User Stories linked to the Epic
        stories = await self.provider.get_stories_in_epic(epic.id)

        # 3. Map entities to DTO
        return EpicDataMapper.to_epic_dto(epic, stories)
