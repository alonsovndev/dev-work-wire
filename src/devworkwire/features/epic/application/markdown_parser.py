import re

from devworkwire.core.domain.exceptions import BusinessRuleViolationException
from devworkwire.features.work_items.domain.import_preview import (
    EpicPreview,
    StoryPreview,
)


class EpicMarkdownParser:
    """Parses the project's Epic markdown format into Jira-ready fields.

    Supports two modes:

    * ``parse()`` — legacy flat format, returns ``(summary, description)``.
    * ``parse_structured()`` — full format with stories and acceptance
      criteria, returns an ``EpicPreview``.
    """

    _KEY_PREFIX = "**Epic Key**:"
    _TITLE_PREFIX = "**Epic Title**:"
    _DESCRIPTION_PREFIX = "**Epic Description:**"

    _STORY_HEADER_RE = re.compile(r"^## Story:\s*(.+)$")
    _STORY_TITLE_PREFIX = "**Story Title**:"
    _STORY_DESCRIPTION_PREFIX = "**Story Description:**"
    _AC_PREFIX = "**Acceptance Criteria**:"

    # ── legacy flat parse (backward-compatible) ────────────────────────

    @staticmethod
    def parse(markdown_content: str) -> tuple[str, str]:
        """
        Extracts ``(summary, description)`` from an Epic markdown document.

        Raises:
            BusinessRuleViolationException: If 'Epic Key' or 'Epic Title'
                is missing from the document.
        """
        lines = markdown_content.splitlines()

        epic_key = None
        epic_title = None
        description_lines: list[str] = []

        for idx, line in enumerate(lines):
            if line.startswith(EpicMarkdownParser._KEY_PREFIX):
                epic_key = line.split(":", 1)[1].strip()
            elif line.startswith(EpicMarkdownParser._TITLE_PREFIX):
                epic_title = line.split(":", 1)[1].strip()
            elif line.startswith(EpicMarkdownParser._DESCRIPTION_PREFIX):
                description_lines = lines[idx + 1 :]

        if not epic_key or not epic_title:
            raise BusinessRuleViolationException(
                "Epic markdown is missing required fields",
                details="'Epic Key' and 'Epic Title' are required",
            )

        summary = f"{epic_key} - {epic_title}"
        description = "\n".join(line.strip() for line in description_lines).strip()
        return summary, description

    # ── structured parse (stories + AC) ────────────────────────────────

    @classmethod
    def parse_structured(cls, markdown_content: str) -> EpicPreview:
        """Parse the full markdown format into an ``EpicPreview``.

        The structured format supports nested ``## Story: <key>`` sections
        with ``**Story Title**:`, ``**Story Description**:`, and
        ``**Acceptance Criteria**:` fields.

        Raises:
            BusinessRuleViolationException: If required epic fields are
                missing.
        """
        lines = markdown_content.splitlines()

        # ── Pass 1: split into epic header + story sections ────────────
        epic_lines: list[str] = []
        story_sections: list[tuple[str, list[str]]] = []

        current_story_key: str | None = None
        current_story_lines: list[str] = []

        for line in lines:
            story_match = cls._STORY_HEADER_RE.match(line)
            if story_match:
                # Flush previous story.
                if current_story_key is not None:
                    story_sections.append((current_story_key, current_story_lines))
                current_story_key = story_match.group(1).strip()
                current_story_lines = []
                continue

            if current_story_key is not None:
                current_story_lines.append(line)
            else:
                epic_lines.append(line)

        # Flush last story.
        if current_story_key is not None:
            story_sections.append((current_story_key, current_story_lines))

        # ── Pass 2: parse epic header ──────────────────────────────────
        epic_key = None
        epic_title = None
        epic_desc_lines: list[str] = []
        in_epic_desc = False

        for line in epic_lines:
            if line.startswith(cls._KEY_PREFIX):
                epic_key = line.split(":", 1)[1].strip()
                in_epic_desc = False
            elif line.startswith(cls._TITLE_PREFIX):
                epic_title = line.split(":", 1)[1].strip()
                in_epic_desc = False
            elif line.startswith(cls._DESCRIPTION_PREFIX):
                in_epic_desc = True
            elif in_epic_desc:
                epic_desc_lines.append(line)

        if not epic_key or not epic_title:
            raise BusinessRuleViolationException(
                "Epic markdown is missing required fields",
                details="'Epic Key' and 'Epic Title' are required",
            )

        epic_description = "\n".join(line.strip() for line in epic_desc_lines).strip()

        stories = [
            cls._parse_story_section(key, section_lines)
            for key, section_lines in story_sections
        ]

        return EpicPreview(
            key=epic_key,
            title=epic_title,
            description=epic_description,
            stories=stories,
        )

    # ── private helpers ────────────────────────────────────────────────

    @classmethod
    def _parse_story_section(cls, story_key: str, lines: list[str]) -> StoryPreview:
        """Parse a single ``## Story: <key>`` section."""
        story_title = None
        story_desc_lines: list[str] = []
        ac_lines: list[str] = []
        phase = "title"  # title → description → ac

        for line in lines:
            stripped = line.strip()

            # Acceptance Criteria block.
            if stripped.startswith(cls._AC_PREFIX):
                phase = "ac"
                continue

            if phase == "ac":
                if stripped.startswith("- "):
                    ac_lines.append(stripped[2:].strip())
                elif stripped:
                    # Non-bullet, non-empty line ends AC.
                    phase = "done"
                # Blank lines within AC are ignored.

            elif phase == "description":
                if stripped.startswith(cls._AC_PREFIX):
                    phase = "ac"
                elif stripped.startswith(cls._STORY_TITLE_PREFIX):
                    story_title = stripped.split(":", 1)[1].strip()
                    phase = "title"
                else:
                    story_desc_lines.append(line)

            elif phase == "title":
                if stripped.startswith(cls._STORY_TITLE_PREFIX):
                    story_title = stripped.split(":", 1)[1].strip()
                elif stripped.startswith(cls._STORY_DESCRIPTION_PREFIX):
                    phase = "description"
                elif stripped.startswith(cls._AC_PREFIX):
                    phase = "ac"

        story_title = story_title or story_key
        story_description = "\n".join(story_desc_lines).strip()

        return StoryPreview(
            key=story_key,
            title=story_title,
            description=story_description,
            acceptance_criteria=ac_lines,
        )
