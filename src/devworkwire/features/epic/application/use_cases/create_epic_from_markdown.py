from devworkwire.application.ports import WorkItemProvider
from devworkwire.features.epic.application.dtos import EpicDtoResponse
from devworkwire.features.epic.application.mappers import EpicDataMapper
from devworkwire.features.epic.application.markdown_parser import EpicMarkdownParser


class CreateEpicFromMarkdown:
    """
    Use case to create an Epic in the tracker from the project's markdown format.

    Orchestrates parsing of the markdown document and delegation to the
    work-item provider, returning the created epic as a DTO.
    """

    def __init__(self, provider: WorkItemProvider):
        """
        Initializes the use case with a work-item provider.

        Args:
            provider: A concrete implementation of the WorkItemProvider port.
        """
        self.provider = provider

    async def execute(self, markdown_content: str) -> EpicDtoResponse:
        """
        Parses the markdown content and creates the Epic in the tracker.

        Args:
            markdown_content: Full text of an Epic markdown document.

        Returns:
            An EpicDtoResponse for the newly created epic.

        Raises:
            BusinessRuleViolationException: If required fields are missing
                from the markdown or the provider rejects the creation.
        """
        summary, description = EpicMarkdownParser.parse(markdown_content)

        epic = await self.provider.create_epic(summary=summary, description=description)

        return EpicDataMapper.to_epic_dto(epic, stories=[])
