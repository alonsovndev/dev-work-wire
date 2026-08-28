"""State repository port for import tracking.

Defines the interface for reading and writing import state. The application
layer depends only on this abstraction; the concrete adapter (SQLite) lives
in the infrastructure layer.
"""

from abc import ABC, abstractmethod

from devworkwire.features.work_items.domain.import_state import (
    ImportRecord,
    WorkItemRef,
)


class StateRepository(ABC):
    """Port for persisting import state (dedup and status tracking)."""

    @abstractmethod
    def find_work_item(self, source_hash: str, item_key: str) -> str | None:
        """Return the provider key for an imported item, or None if not found.

        Args:
            source_hash: SHA-256 of the normalised source file path.
            item_key: The key from the markdown source (e.g. ``EPIC-0``).
        """

    @abstractmethod
    def save_import(
        self,
        source_path: str,
        source_hash: str,
        epic_key: str,
        work_items: list[WorkItemRef],
    ) -> None:
        """Persist a completed import with its work-item references.

        If an import with the same ``source_hash`` already exists it is
        replaced atomically (delete + re-insert).
        """

    @abstractmethod
    def list_imports(self) -> list[ImportRecord]:
        """Return all import records, newest first."""

    @abstractmethod
    def find_import_by_hash(self, source_hash: str) -> ImportRecord | None:
        """Return the import record for a given source hash, or None."""
