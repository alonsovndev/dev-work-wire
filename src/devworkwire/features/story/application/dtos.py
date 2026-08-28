from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StoryDtoResponse(BaseModel):
    """Data Transfer Object for User Story responses."""

    key: str
    numeric_id: int
    summary: str
    description: str
    status: str
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    priority: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    story_points: Optional[int] = None
    epic_key: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    sprint: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateStoryDtoRequest(BaseModel):
    """Data Transfer Object for creating a User Story."""

    summary: str
    description: str
    epic_key: str
    story_points: Optional[int] = None
    labels: List[str] = Field(default_factory=list)
    assignee: Optional[str] = None
    priority: Optional[str] = "Medium"
