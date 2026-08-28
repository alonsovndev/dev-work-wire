from devworkwire.features.epic.application.dtos import EpicDtoResponse
from devworkwire.features.epic.domain import Epic
from devworkwire.features.story.application.mappers import StoryDataMapper
from devworkwire.features.story.domain import UserStory


class EpicDataMapper:
    """Maps Epic domain entities to DTOs."""

    @staticmethod
    def to_epic_dto(epic: Epic, stories: list[UserStory]) -> EpicDtoResponse:
        return EpicDtoResponse(
            key=epic.key,
            numeric_id=epic.numeric_id,
            summary=epic.summary,
            description=epic.description,
            status=epic.status.value,
            assignee=epic.assignee,
            reporter=epic.reporter,
            priority=epic.priority.name if epic.priority else None,
            labels=[label.name for label in epic.labels],
            story_points=epic.story_points.value if epic.story_points else None,
            created_at=epic.created_at,
            updated_at=epic.updated_at,
            user_stories=[StoryDataMapper.to_dto(story) for story in stories],
        )
