"""Import state domain models.

Represents persisted import records stored in the local SQLite database.
Used for deduplication on re-run and for the ``import status`` view.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class WorkItemRef:
    """Reference to a provider-created work item (epic or story)."""

    item_key: str
    item_type: str  # "epic" or "story"
    provider_key: str  # Jira issue key after creation
    provider_id: str | None = None  # Jira numeric ID


@dataclass(frozen=True)
class ImportRecord:
    """A completed import, persisted in the state database."""

    source_path: str
    source_hash: str
    epic_key: str
    imported_at: datetime
    work_items: list[WorkItemRef] = field(default_factory=list)

    @property
    def story_keys(self) -> list[str]:
        return [ref.provider_key for ref in self.work_items if ref.item_type == "story"]
