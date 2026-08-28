import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.core.domain.issue import IssueStatus
from devworkwire.features.epic.application.use_cases import CreateEpicFromMarkdown
from devworkwire.features.epic.domain import Epic

VALID_MARKDOWN = """# Epic: Foundational Setup

**Epic Title**: Foundational Setup
**Epic Key**: EPIC-0
**Summary**: Establish foundations.

---

**Epic Description:**
Problem Statement: teams are blocked.

Objective: set up the baseline.
"""


@pytest.fixture
def mock_provider():
    """Fixture to create a mock WorkItemProvider."""
    return AsyncMock()


@pytest.mark.asyncio
class TestCreateEpicFromMarkdown:
    async def test_creates_epic_with_parsed_fields(self, mock_provider):
        # Arrange
        created_at = datetime(2026, 1, 1, 10, 0, 0)
        mock_provider.create_epic.return_value = Epic.create(
            key="OPH-101",
            numeric_id=101,
            summary="EPIC-0 - Foundational Setup",
            description="Problem Statement: teams are blocked.",
            status=IssueStatus.TODO,
            created_at=created_at,
            updated_at=created_at,
        )
        use_case = CreateEpicFromMarkdown(provider=mock_provider)

        # Act
        result = await use_case.execute(VALID_MARKDOWN)

        # Assert
        mock_provider.create_epic.assert_awaited_once_with(
            summary="EPIC-0 - Foundational Setup",
            description="Problem Statement: teams are blocked.\n\n"
            "Objective: set up the baseline.",
        )
        assert result.key == "OPH-101"
        assert result.summary == "EPIC-0 - Foundational Setup"

    async def test_missing_title_raises_and_skips_creation(self, mock_provider):
        # Arrange
        markdown = "**Epic Key**: EPIC-1\n**Epic Description:**\nBody"
        use_case = CreateEpicFromMarkdown(provider=mock_provider)

        # Act & Assert
        with pytest.raises(BusinessRuleViolationException):
            await use_case.execute(markdown)
        mock_provider.create_epic.assert_not_called()

    async def test_missing_key_raises_and_skips_creation(self, mock_provider):
        # Arrange
        markdown = "**Epic Title**: Only a title\n"
        use_case = CreateEpicFromMarkdown(provider=mock_provider)

        # Act & Assert
        with pytest.raises(BusinessRuleViolationException):
            await use_case.execute(markdown)
        mock_provider.create_epic.assert_not_called()

    async def test_description_defaults_to_empty_when_absent(self, mock_provider):
        # Arrange
        now = datetime.now()
        mock_provider.create_epic.return_value = Epic.create(
            key="OPH-102",
            numeric_id=102,
            summary="EPIC-2 - Bare",
            description="",
            status=IssueStatus.TODO,
            created_at=now,
            updated_at=now,
        )
        use_case = CreateEpicFromMarkdown(provider=mock_provider)

        # Act
        result = await use_case.execute("**Epic Title**: Bare\n**Epic Key**: EPIC-2")

        # Assert
        mock_provider.create_epic.assert_awaited_once_with(
            summary="EPIC-2 - Bare", description=""
        )
        assert result.key == "OPH-102"
