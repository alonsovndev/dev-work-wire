"""DTOs for the import feature."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel


class StoryPreviewDto(BaseModel):
    """DTO for a single story in the import preview."""

    key: str
    title: str
    description: str
    acceptance_criteria: List[str]


class EpicPreviewDto(BaseModel):
    """DTO for the epic-level import preview."""

    key: str
    title: str
    description: str
    stories: List[StoryPreviewDto]


class ValidationDto(BaseModel):
    """DTO for validation results."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ImportPreviewDto(BaseModel):
    """Full import preview DTO returned to the presentation layer."""

    source_path: str
    source_hash: str
    epic: EpicPreviewDto
    validation: ValidationDto
    created_at: datetime

    @property
    def is_importable(self) -> bool:
        return self.validation.is_valid


class WorkItemResultDto(BaseModel):
    """Result of creating/updating a single work item."""

    item_key: str
    item_type: str
    provider_key: str
    provider_id: str | None = None
    action: str  # "created", "updated", "skipped"


class ImportCommitResultDto(BaseModel):
    """Result of the import commit operation."""

    source_path: str
    epic_key: str
    items: List[WorkItemResultDto]
    skipped: bool = False
    skipped_reason: str | None = None
