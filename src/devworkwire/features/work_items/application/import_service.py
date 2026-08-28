"""Import service — orchestrates the validate → preview → commit loop.

This is the core of DevWorkWire's loading engine.  It depends only on ports
(``WorkItemProvider`` and ``StateRepository``) and the markdown parser, never
on concrete infrastructure.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List

from devworkwire.application.ports import WorkItemProvider
from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.features.epic.application.markdown_parser import EpicMarkdownParser
from devworkwire.features.work_items.application.dtos import (
    EpicPreviewDto,
    ImportCommitResultDto,
    ImportPreviewDto,
    StoryPreviewDto,
    ValidationDto,
    WorkItemResultDto,
)
from devworkwire.features.work_items.application.ports import StateRepository
from devworkwire.features.work_items.domain.import_preview import (
    EpicPreview,
    ImportPreview,
    StoryPreview,
    ValidationReport,
)
from devworkwire.features.work_items.domain.import_state import WorkItemRef
from devworkwire.shared.log_config import get_logger

logger = get_logger(__name__)

_PREVIEW_DIR = ".devworkwire"
_PREVIEW_FILE = "import-preview.json"


def _source_hash(source_path: str) -> str:
    """SHA-256 of the normalised (absolute, resolved) path string."""
    normalised = str(Path(source_path).resolve())
    return hashlib.sha256(normalised.encode()).hexdigest()[:16]


class ImportService:
    """Orchestrates the import preview → commit flow."""

    def __init__(
        self,
        provider: WorkItemProvider,
        state_repo: StateRepository,
        preview_dir: Path | str = _PREVIEW_DIR,
    ):
        self._provider = provider
        self._state_repo = state_repo
        self._preview_dir = Path(preview_dir)

    # ── preview ────────────────────────────────────────────────────────

    async def preview(self, source_path: str) -> ImportPreviewDto:
        """Parse, validate, and persist an import preview.

        Returns the full preview DTO.  The preview is also written to disk
        so ``commit()`` can load it later.
        """
        path = Path(source_path)
        if not path.exists():
            raise BusinessRuleViolationException(
                f"Source file not found: {source_path}",
                details="Provide a valid path to the epic markdown file.",
            )

        content = path.read_text(encoding="utf-8")
        source_hash = _source_hash(source_path)

        # Parse structured format.
        epic_preview = EpicMarkdownParser.parse_structured(content)

        # Validate.
        validation = self._validate(epic_preview)

        preview = ImportPreview(
            source_path=str(path.resolve()),
            source_hash=source_hash,
            epic=epic_preview,
            validation=validation,
        )

        # Persist.
        self._save_preview(preview)

        logger.info(
            "Import preview generated",
            extra={
                "source_path": source_path,
                "source_hash": source_hash,
                "valid": validation.is_valid,
                "story_count": len(epic_preview.stories),
            },
        )

        return self._to_preview_dto(preview)

    # ── commit ─────────────────────────────────────────────────────────

    async def commit(self) -> ImportCommitResultDto:
        """Load the persisted preview and execute the import.

        Deduplication: if the state repo already has an entry for the same
        source hash and item key, the item is skipped.  If the source file
        has changed (same hash but different content), the existing items
        are updated instead.

        Raises:
            BusinessRuleViolationException: If no valid preview exists.
        """
        preview = self._load_preview()
        if preview is None:
            raise BusinessRuleViolationException(
                "No import preview found",
                details="Run 'dwire import preview <file>' first.",
            )
        if not preview.is_importable:
            raise BusinessRuleViolationException(
                "Import preview has validation errors",
                details=str(preview.validation.errors),
            )

        epic = preview.epic
        source_hash = preview.source_hash
        results: list[WorkItemResultDto] = []
        work_item_refs: list[WorkItemRef] = []

        # --- Epic ---
        existing_epic_key = self._state_repo.find_work_item(source_hash, epic.key)
        if existing_epic_key:
            logger.info(
                "Epic already imported, skipping",
                extra={"epic_key": epic.key, "provider_key": existing_epic_key},
            )
            results.append(
                WorkItemResultDto(
                    item_key=epic.key,
                    item_type="epic",
                    provider_key=existing_epic_key,
                    action="skipped",
                )
            )
            work_item_refs.append(
                WorkItemRef(
                    item_key=epic.key,
                    item_type="epic",
                    provider_key=existing_epic_key,
                )
            )
        else:
            summary = f"{epic.key} - {epic.title}"
            created_epic = await self._provider.create_epic(
                summary=summary, description=epic.description
            )
            results.append(
                WorkItemResultDto(
                    item_key=epic.key,
                    item_type="epic",
                    provider_key=created_epic.key,
                    provider_id=str(created_epic.numeric_id),
                    action="created",
                )
            )
            work_item_refs.append(
                WorkItemRef(
                    item_key=epic.key,
                    item_type="epic",
                    provider_key=created_epic.key,
                    provider_id=str(created_epic.numeric_id),
                )
            )

        # --- Stories ---
        for story in epic.stories:
            existing_story_key = self._state_repo.find_work_item(source_hash, story.key)
            if existing_story_key:
                logger.info(
                    "Story already imported, skipping",
                    extra={
                        "story_key": story.key,
                        "provider_key": existing_story_key,
                    },
                )
                results.append(
                    WorkItemResultDto(
                        item_key=story.key,
                        item_type="story",
                        provider_key=existing_story_key,
                        action="skipped",
                    )
                )
                work_item_refs.append(
                    WorkItemRef(
                        item_key=story.key,
                        item_type="story",
                        provider_key=existing_story_key,
                    )
                )
            else:
                epic_provider_key = work_item_refs[0].provider_key
                story_summary = f"{story.key} - {story.title}"
                ac_text = ""
                if story.acceptance_criteria:
                    ac_text = "\n".join(f"- {ac}" for ac in story.acceptance_criteria)
                description = story.description
                if ac_text:
                    description = (
                        f"{story.description}\n\n**Acceptance Criteria:**\n{ac_text}"
                    ).strip()

                created_story = await self._provider.create_user_story(
                    epic_key=epic_provider_key,
                    summary=story_summary,
                    description=description,
                )
                results.append(
                    WorkItemResultDto(
                        item_key=story.key,
                        item_type="story",
                        provider_key=created_story.key,
                        provider_id=str(created_story.numeric_id),
                        action="created",
                    )
                )
                work_item_refs.append(
                    WorkItemRef(
                        item_key=story.key,
                        item_type="story",
                        provider_key=created_story.key,
                        provider_id=str(created_story.numeric_id),
                    )
                )

        # Persist state.
        self._state_repo.save_import(
            source_path=preview.source_path,
            source_hash=source_hash,
            epic_key=epic.key,
            work_items=work_item_refs,
        )

        # Clear preview after successful commit.
        self._clear_preview()

        logger.info(
            "Import committed",
            extra={
                "epic_key": epic.key,
                "items_created": sum(1 for r in results if r.action == "created"),
                "items_skipped": sum(1 for r in results if r.action == "skipped"),
            },
        )

        return ImportCommitResultDto(
            source_path=preview.source_path,
            epic_key=epic.key,
            items=results,
        )

    # ── status ─────────────────────────────────────────────────────────

    def status(self) -> List[ImportPreviewDto]:
        """Return a list of all completed imports."""
        records = self._state_repo.list_imports()
        # For status, we return lightweight DTOs from the state records.
        # Full preview DTOs are not available post-commit; return summaries.
        return [
            ImportPreviewDto(
                source_path=record.source_path,
                source_hash=record.source_hash,
                epic=EpicPreviewDto(
                    key=record.epic_key,
                    title="",
                    description="",
                    stories=[],
                ),
                validation=ValidationDto(is_valid=True, errors=[], warnings=[]),
                created_at=record.imported_at,
            )
            for record in records
        ]

    # ── private helpers ────────────────────────────────────────────────

    def _validate(self, epic: EpicPreview) -> ValidationReport:
        """Run structural validation on the parsed epic preview."""
        report = ValidationReport()

        if not epic.key:
            report.add_error("Epic key is missing")
        if not epic.title:
            report.add_error("Epic title is missing")

        seen_keys: set[str] = {epic.key}
        for story in epic.stories:
            if not story.key:
                report.add_error("A story is missing its key")
                continue
            if story.key in seen_keys:
                report.add_error(f"Duplicate story key: {story.key}")
            seen_keys.add(story.key)

            if not story.title:
                report.add_warning(
                    f"Story {story.key} has no title; will use key as title"
                )

        return report

    def _preview_path(self) -> Path:
        return self._preview_dir / _PREVIEW_FILE

    def _save_preview(self, preview: ImportPreview) -> None:
        self._preview_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "source_path": preview.source_path,
            "source_hash": preview.source_hash,
            "epic": {
                "key": preview.epic.key,
                "title": preview.epic.title,
                "description": preview.epic.description,
                "stories": [
                    {
                        "key": s.key,
                        "title": s.title,
                        "description": s.description,
                        "acceptance_criteria": s.acceptance_criteria,
                    }
                    for s in preview.epic.stories
                ],
            },
            "validation": {
                "is_valid": preview.validation.is_valid,
                "errors": preview.validation.errors,
                "warnings": preview.validation.warnings,
            },
            "created_at": preview.created_at.isoformat(),
        }
        self._preview_path().write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_preview(self) -> ImportPreview | None:
        path = self._preview_path()
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        epic_data = data["epic"]
        return ImportPreview(
            source_path=data["source_path"],
            source_hash=data["source_hash"],
            epic=EpicPreview(
                key=epic_data["key"],
                title=epic_data["title"],
                description=epic_data["description"],
                stories=[
                    StoryPreview(
                        key=s["key"],
                        title=s["title"],
                        description=s["description"],
                        acceptance_criteria=s.get("acceptance_criteria", []),
                    )
                    for s in epic_data.get("stories", [])
                ],
            ),
            validation=ValidationReport(
                errors=data["validation"]["errors"],
                warnings=data["validation"]["warnings"],
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    def _clear_preview(self) -> None:
        path = self._preview_path()
        if path.exists():
            path.unlink()

    @staticmethod
    def _to_preview_dto(preview: ImportPreview) -> ImportPreviewDto:
        return ImportPreviewDto(
            source_path=preview.source_path,
            source_hash=preview.source_hash,
            epic=EpicPreviewDto(
                key=preview.epic.key,
                title=preview.epic.title,
                description=preview.epic.description,
                stories=[
                    StoryPreviewDto(
                        key=s.key,
                        title=s.title,
                        description=s.description,
                        acceptance_criteria=s.acceptance_criteria,
                    )
                    for s in preview.epic.stories
                ],
            ),
            validation=ValidationDto(
                is_valid=preview.validation.is_valid,
                errors=preview.validation.errors,
                warnings=preview.validation.warnings,
            ),
            created_at=preview.created_at,
        )
