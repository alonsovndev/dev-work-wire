from devworkwire.features.story.application.dtos import StoryDtoResponse
from devworkwire.features.story.domain import UserStory


class StoryDataMapper:
    """Maps UserStory domain entities to DTOs."""

    @staticmethod
    def to_dto(story: UserStory) -> StoryDtoResponse:
        return StoryDtoResponse(
            key=story.key,
            numeric_id=story.numeric_id,
            summary=story.summary,
            description=story.description,
            status=story.status.value,
            assignee=story.assignee,
            reporter=story.reporter,
            priority=story.priority.name if story.priority else None,
            labels=[label.name for label in story.labels],
            story_points=story.story_points.value if story.story_points else None,
            epic_key=story.epic_link.key if story.epic_link else None,
            acceptance_criteria=story.acceptance_criteria,
            sprint=story.sprint,
            created_at=story.created_at,
            updated_at=story.updated_at,
        )
