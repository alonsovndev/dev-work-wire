from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from devworkwire.composition.container import Composition
from devworkwire.core.domain.issue import IssueStatus
from devworkwire.features.epic.domain import Epic
from devworkwire.features.epic.presentation import commands
from devworkwire.features.story.domain import UserStory


def make_epic(key: str = "OPH-1") -> Epic:
    now = datetime(2026, 1, 1, 10, 0, 0)
    return Epic.create(
        key=key,
        numeric_id=1,
        summary="Foundational Setup",
        description="Setup description",
        status=IssueStatus.TODO,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_composition():
    """Build a Composition with a mock WorkItemProvider for command tests."""
    return Composition(
        work_item_provider=AsyncMock(),
        state_repository=AsyncMock(),
        import_service=AsyncMock(),
    )


class TestFetchEpic:
    def test_prints_epic_and_story_list(self, mock_composition, capsys):
        story = UserStory.create(
            key="OPH-2",
            numeric_id=2,
            summary="First story",
            description="Do things",
            status=IssueStatus.IN_PROGRESS,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 2),
            epic_key="OPH-1",
        )
        mock_composition.work_item_provider.get_epic.return_value = make_epic()
        mock_composition.work_item_provider.get_stories_in_epic.return_value = [story]

        commands.fetch_epic(mock_composition, "OPH-1")

        out = capsys.readouterr().out
        assert "OPH-1" in out
        assert "Foundational Setup" in out
        assert "Stories (1)" in out
        assert "OPH-2" in out

    def test_not_found_prints_friendly_message(self, mock_composition, capsys):
        mock_composition.work_item_provider.get_epic.return_value = None

        commands.fetch_epic(mock_composition, "OPH-404")

        assert "Epic not found: OPH-404" in capsys.readouterr().out

    def test_invalid_key_is_reported_without_repo_call(self, mock_composition, capsys):
        commands.fetch_epic(mock_composition, "not-a-jira-key")

        out = capsys.readouterr().out
        assert "Error fetching epic" in out
        mock_composition.work_item_provider.get_epic.assert_not_called()
        mock_composition.work_item_provider.get_stories_in_epic.assert_not_called()

    def test_unexpected_error_keeps_session_alive(self, mock_composition, capsys):
        mock_composition.work_item_provider.get_epic.side_effect = RuntimeError("boom")

        commands.fetch_epic(mock_composition, "OPH-1")

        assert "Unexpected error fetching epic" in capsys.readouterr().out


class TestCreateEpic:
    def test_creates_epic_from_markdown_file(self, mock_composition, tmp_path, capsys):
        epic_file = tmp_path / "epic.md"
        epic_file.write_text(
            "# Epic\n\n"
            "**Epic Title**: Foundational Setup\n"
            "**Epic Key**: EPIC-0\n"
            "**Epic Description:**\n"
            "Problem statement.\n",
            encoding="utf-8",
        )
        mock_composition.work_item_provider.create_epic.return_value = Epic.create(
            key="OPH-101",
            numeric_id=101,
            summary="EPIC-0 - Foundational Setup",
            description="Problem statement.",
            status=IssueStatus.TODO,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )

        commands.create_epic(mock_composition, str(epic_file))

        out = capsys.readouterr().out
        assert "Epic Successfully Created!" in out
        assert "OPH-101" in out
        mock_composition.work_item_provider.create_epic.assert_awaited_once_with(
            summary="EPIC-0 - Foundational Setup",
            description="Problem statement.",
        )

    def test_missing_file_reports_error(self, mock_composition, tmp_path, capsys):
        commands.create_epic(mock_composition, str(tmp_path / "does-not-exist.md"))

        assert "Cannot read file" in capsys.readouterr().out

    def test_markdown_missing_fields_reports_error(
        self, mock_composition, tmp_path, capsys
    ):
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("**Epic Key**: EPIC-0\n", encoding="utf-8")

        commands.create_epic(mock_composition, str(bad_file))

        out = capsys.readouterr().out
        assert "Invalid file or content" in out
        mock_composition.work_item_provider.create_epic.assert_not_called()
