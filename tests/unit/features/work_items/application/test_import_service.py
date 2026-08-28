"""Tests for the ImportService application service."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from devworkwire.features.work_items.application.import_service import ImportService
from devworkwire.infrastructure.local.sqlite_state_store import SqliteStateStore


SAMPLE_MARKDOWN = """\
**Epic Key**: EPIC-0
**Epic Title**: Test Epic
**Epic Description:**
A test epic.

## Story: EPIC-0-1
**Story Title**: First story
**Story Description:**
Do something.

**Acceptance Criteria**:
- It works
- No bugs
"""


@pytest.fixture
def tmp_dir(tmp_path: Path):
    """Create a temp directory with a sample markdown file."""
    md_file = tmp_path / "epic.md"
    md_file.write_text(SAMPLE_MARKDOWN)
    return tmp_path


@pytest.fixture
def mock_provider():
    return AsyncMock()


@pytest.fixture
def state_store(tmp_dir: Path):
    return SqliteStateStore(tmp_dir / "test.db")


@pytest.fixture
def service(mock_provider, state_store, tmp_dir: Path):
    return ImportService(
        provider=mock_provider,
        state_repo=state_store,
        preview_dir=tmp_dir / ".devworkwire",
    )


class TestImportPreview:
    @pytest.mark.asyncio
    async def test_preview_returns_valid_result(self, service, tmp_dir):
        result = await service.preview(str(tmp_dir / "epic.md"))

        assert result.epic.key == "EPIC-0"
        assert result.epic.title == "Test Epic"
        assert len(result.epic.stories) == 1
        assert result.validation.is_valid

    @pytest.mark.asyncio
    async def test_preview_persists_file(self, service, tmp_dir):
        await service.preview(str(tmp_dir / "epic.md"))

        preview_file = tmp_dir / ".devworkwire" / "import-preview.json"
        assert preview_file.exists()
        data = json.loads(preview_file.read_text())
        assert data["epic"]["key"] == "EPIC-0"

    @pytest.mark.asyncio
    async def test_preview_rejects_missing_file(self, service):
        with pytest.raises(Exception, match="Source file not found"):
            await service.preview("/nonexistent/epic.md")

    @pytest.mark.asyncio
    async def test_preview_with_no_stories(self, service, tmp_dir):
        minimal = tmp_dir / "minimal.md"
        minimal.write_text("**Epic Key**: EPIC-1\n**Epic Title**: Minimal\n")
        result = await service.preview(str(minimal))
        assert result.epic.stories == []
        assert result.validation.is_valid


class TestValidation:
    @pytest.mark.asyncio
    async def test_duplicate_story_keys_flagged(self, service, tmp_dir):
        bad_md = tmp_dir / "bad.md"
        bad_md.write_text(
            "**Epic Key**: EPIC-0\n**Epic Title**: Test\n"
            "## Story: EPIC-0-1\n**Story Title**: A\n"
            "## Story: EPIC-0-1\n**Story Title**: B\n"
        )
        result = await service.preview(str(bad_md))
        assert not result.validation.is_valid
        assert any("Duplicate" in e for e in result.validation.errors)

    @pytest.mark.asyncio
    async def test_missing_story_key_flagged(self, service, tmp_dir):
        bad_md = tmp_dir / "bad2.md"
        bad_md.write_text(
            "**Epic Key**: EPIC-0\n**Epic Title**: Test\n"
            "## Story: \n**Story Title**: No key\n"
        )
        result = await service.preview(str(bad_md))
        assert not result.validation.is_valid


class TestImportCommit:
    @pytest.mark.asyncio
    async def test_commit_creates_epic_and_stories(self, service, tmp_dir):
        mock_epic = MagicMock()
        mock_epic.key = "OPH-42"
        mock_epic.numeric_id = 10042
        service._provider.create_epic = AsyncMock(return_value=mock_epic)

        mock_story = MagicMock()
        mock_story.key = "OPH-43"
        mock_story.numeric_id = 10043
        service._provider.create_user_story = AsyncMock(return_value=mock_story)

        await service.preview(str(tmp_dir / "epic.md"))
        result = await service.commit()

        assert result.epic_key == "EPIC-0"
        assert len(result.items) == 2  # 1 epic + 1 story
        assert all(i.action == "created" for i in result.items)
        service._provider.create_epic.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_skips_already_imported(self, service, tmp_dir, state_store):
        mock_epic = MagicMock()
        mock_epic.key = "OPH-42"
        mock_epic.numeric_id = 10042
        service._provider.create_epic = AsyncMock(return_value=mock_epic)

        mock_story = MagicMock()
        mock_story.key = "OPH-43"
        mock_story.numeric_id = 10043
        service._provider.create_user_story = AsyncMock(return_value=mock_story)

        await service.preview(str(tmp_dir / "epic.md"))
        await service.commit()

        # Re-preview then commit again — items already imported → skipped.
        await service.preview(str(tmp_dir / "epic.md"))
        result = await service.commit()
        assert all(i.action == "skipped" for i in result.items)

    @pytest.mark.asyncio
    async def test_commit_fails_without_preview(self, service):
        with pytest.raises(Exception, match="No import preview found"):
            await service.commit()

    @pytest.mark.asyncio
    async def test_commit_persists_state(self, service, tmp_dir, state_store):
        mock_epic = MagicMock()
        mock_epic.key = "OPH-42"
        mock_epic.numeric_id = 10042
        service._provider.create_epic = AsyncMock(return_value=mock_epic)

        mock_story = MagicMock()
        mock_story.key = "OPH-43"
        mock_story.numeric_id = 10043
        service._provider.create_user_story = AsyncMock(return_value=mock_story)

        await service.preview(str(tmp_dir / "epic.md"))
        await service.commit()

        records = state_store.list_imports()
        assert len(records) == 1
        assert records[0].epic_key == "EPIC-0"


class TestImportStatus:
    @pytest.mark.asyncio
    async def test_status_empty(self, service):
        assert service.status() == []

    @pytest.mark.asyncio
    async def test_status_after_import(self, service, tmp_dir):
        mock_epic = MagicMock()
        mock_epic.key = "OPH-42"
        mock_epic.numeric_id = 10042
        service._provider.create_epic = AsyncMock(return_value=mock_epic)

        mock_story = MagicMock()
        mock_story.key = "OPH-43"
        mock_story.numeric_id = 10043
        service._provider.create_user_story = AsyncMock(return_value=mock_story)

        await service.preview(str(tmp_dir / "epic.md"))
        await service.commit()

        records = service.status()
        assert len(records) == 1
        assert records[0].epic.key == "EPIC-0"
