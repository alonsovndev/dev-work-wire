"""Tests for the structured markdown parser (parse_structured)."""

import pytest

from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.features.epic.application.markdown_parser import EpicMarkdownParser


FULL_MARKDOWN = """\
**Epic Key**: EPIC-0
**Epic Title**: Foundational Setup
**Epic Description:**
Build the base infrastructure.

## Story: EPIC-0-1
**Story Title**: Repository setup
**Story Description:**
Initialize the monorepo.

**Acceptance Criteria**:
- Repo created with pyproject.toml
- CI pipeline green

## Story: EPIC-0-2
**Story Title**: Core domain layer

**Acceptance Criteria**:
- Domain entities defined
- Mappers implemented
"""

MINIMAL_MARKDOWN = """\
**Epic Key**: EPIC-1
**Epic Title**: Minimal Epic
"""


class TestParseStructured:
    def test_parses_full_format(self):
        result = EpicMarkdownParser.parse_structured(FULL_MARKDOWN)

        assert result.key == "EPIC-0"
        assert result.title == "Foundational Setup"
        assert "base infrastructure" in result.description
        assert len(result.stories) == 2

    def test_parses_stories(self):
        result = EpicMarkdownParser.parse_structured(FULL_MARKDOWN)

        story1 = result.stories[0]
        assert story1.key == "EPIC-0-1"
        assert story1.title == "Repository setup"
        assert "monorepo" in story1.description
        assert len(story1.acceptance_criteria) == 2
        assert "pyproject.toml" in story1.acceptance_criteria[0]

    def test_parses_acceptance_criteria(self):
        result = EpicMarkdownParser.parse_structured(FULL_MARKDOWN)

        story2 = result.stories[1]
        assert story2.key == "EPIC-0-2"
        assert story2.title == "Core domain layer"
        assert len(story2.acceptance_criteria) == 2

    def test_minimal_format_no_stories(self):
        result = EpicMarkdownParser.parse_structured(MINIMAL_MARKDOWN)

        assert result.key == "EPIC-1"
        assert result.title == "Minimal Epic"
        assert result.stories == []

    def test_missing_epic_key_raises(self):
        bad_md = "**Epic Title**: Oops\n"
        with pytest.raises(BusinessRuleViolationException):
            EpicMarkdownParser.parse_structured(bad_md)

    def test_missing_epic_title_raises(self):
        bad_md = "**Epic Key**: EPIC-X\n"
        with pytest.raises(BusinessRuleViolationException):
            EpicMarkdownParser.parse_structured(bad_md)


class TestParseBackwardCompat:
    """Ensure the legacy parse() method still works."""

    def test_legacy_parse(self):
        summary, description = EpicMarkdownParser.parse(FULL_MARKDOWN)
        assert summary == "EPIC-0 - Foundational Setup"
        assert "base infrastructure" in description
