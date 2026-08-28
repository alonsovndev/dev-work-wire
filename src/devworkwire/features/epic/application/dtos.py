from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from devworkwire.features.story.application.dtos import StoryDtoResponse


class EpicDtoResponse(BaseModel):
    """Data Transfer Object for Epics, including their stories."""

    key: str
    numeric_id: int
    summary: str
    description: str
    status: str
    assignee: Optional[str]
    reporter: Optional[str]
    priority: Optional[str]
    labels: List[str]
    story_points: Optional[int]
    created_at: datetime
    updated_at: datetime
    user_stories: List[StoryDtoResponse] = Field(default_factory=list)
