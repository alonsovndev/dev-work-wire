"""Import preview domain models.

Represents the validated, pre-commit state of an import operation.
The preview is persisted to disk so it can be confirmed from a different
interface (CLI or agent session) within the same window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class StoryPreview:
    """A single story extracted from the markdown source, ready for import."""

    key: str
    title: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EpicPreview:
    """Epic-level preview containing its stories."""

    key: str
    title: str
    description: str
    stories: list[StoryPreview] = field(default_factory=list)


@dataclass(frozen=True)
class ValidationReport:
    """Result of structural validation on a parsed markdown document."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


@dataclass(frozen=True)
class ImportPreview:
    """Full preview of an import operation, persisted before commit.

    Stored as JSON at ``.devworkwire/import-preview.json`` so the commit
    command can load it without re-parsing the source markdown.
    """

    source_path: str
    source_hash: str
    epic: EpicPreview
    validation: ValidationReport
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_importable(self) -> bool:
        return self.validation.is_valid
